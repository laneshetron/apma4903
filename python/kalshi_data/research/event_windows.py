"""In-play markets: how is maker P&L distributed around information events (goals etc.)?

Events are detected from the tape: the mid of a market moving >= --jump cents within --jump-window
seconds (all strikes / outcomes of the same game jump together). Every touch trade is then bucketed by
its position relative to the nearest event:
    hit      the trade is within `pre` seconds BEFORE an event (the informed hit on the stale quote)
    post5    within 5 s after an event (repricing churn)
    post30   5-30 s after
    post120  30-120 s after
    quiet    everything else
and the maker markout at 30 s (+ = maker earned) is reported per bucket, volume-weighted, with the
share of volume. Optionally the same for our simulated fills (--fills parquet from `sim --fills-out`).

    uv run python -m kalshi_data.research.event_windows 2026-09-20 --data-dir ../data_epl --series KXEPLTOTAL
"""

from __future__ import annotations

import argparse
import bisect
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl

from ..book import parse_price, parse_qty
from ..raw import iter_records
from .markouts import FastBook

ONE = 10_000
QTY = 100


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--series", required=True)
    ap.add_argument("--jump", type=float, default=5.0, help="cents of mid move that defines an event")
    ap.add_argument("--jump-window", type=float, default=2.0, help="seconds over which the move is measured")
    ap.add_argument("--pre", type=float, default=5.0, help="seconds before an event counted as the informed hit")
    ap.add_argument("--fills", type=Path, default=None, help="sim fills parquet to bucket the same way")
    a = ap.parse_args()

    books: dict[str, FastBook] = {}
    mids: dict[str, tuple[list, list]] = defaultdict(lambda: ([], []))
    trades: list[tuple[str, int, int, float, float]] = []   # ticker, rx, sign, price_c, qty
    recent: dict[str, deque] = defaultdict(deque)
    for rec in iter_records(a.data_dir, a.day):
        raw = rec.raw
        t = raw.get("type")
        if t not in ("orderbook_snapshot", "orderbook_delta", "trade"):
            continue
        msg = raw["msg"]
        tk = msg["market_ticker"]
        if not tk.startswith(a.series + "-"):
            continue
        b = books.setdefault(tk, FastBook())
        rx = rec.rx_ns
        if t == "orderbook_snapshot":
            b.snapshot(msg)
        elif t == "orderbook_delta":
            if b.stale:
                continue
            try:
                b.delta(msg["side"], parse_price(msg["price_dollars"]), parse_qty(msg["delta_fp"]))
            except ValueError:
                b.stale = True
                continue
        else:
            yp = parse_price(msg["yes_price_dollars"])
            hit = "no" if msg["taker_side"] == "yes" else "yes"
            trades.append((tk, rx, 1 if hit == "yes" else -1, yp / 100, parse_qty(msg["count_fp"]) / QTY))
            continue
        m = b.mid()
        if m is None:
            continue
        mr, mv = mids[tk]
        if not mv or mv[-1] != m:
            mr.append(rx)
            mv.append(m)

    # events per ticker: first crossing of the jump within the window, then a refractory period of the window
    events: dict[str, list[int]] = {}
    w = int(a.jump_window * 1e9)
    for tk, (mr, mv) in mids.items():
        ev = []
        last = -1
        j = 0
        for i in range(len(mr)):
            if mr[i] - last < w:
                continue
            while mr[j] < mr[i] - w:
                j += 1
            if abs(mv[i] - mv[j]) >= a.jump:
                ev.append(mr[i])
                last = mr[i]
        events[tk] = ev
    n_ev = sum(len(v) for v in events.values())
    print(f"# {a.series} {a.day}: {len(mids)} markets, {n_ev} information events (mid moved >= {a.jump:.0f}c within {a.jump_window:.0f} s), {len(trades):,} trades\n")

    def bucket(tk: str, rx: int) -> str:
        ev = events.get(tk, [])
        i = bisect.bisect_left(ev, rx)
        nxt = (ev[i] - rx) / 1e9 if i < len(ev) else None
        prv = (rx - ev[i - 1]) / 1e9 if i > 0 else None
        if nxt is not None and nxt <= a.pre:
            return "hit (<= %gs before)" % a.pre
        if prv is not None and prv <= 5:
            return "post 0-5 s"
        if prv is not None and prv <= 30:
            return "post 5-30 s"
        if prv is not None and prv <= 120:
            return "post 30-120 s"
        return "quiet"

    order = ["hit (<= %gs before)" % a.pre, "post 0-5 s", "post 5-30 s", "post 30-120 s", "quiet"]

    def mo(tk: str, rx: int, sign: int, pc: float, h: int) -> float | None:
        mr, mv = mids[tk]
        i = bisect.bisect_right(mr, rx + h * 1_000_000_000) - 1
        return sign * (mv[i] - pc) if i >= 0 else None

    def report(title: str, rows: list[tuple[str, int, int, float, float]]) -> None:
        acc = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])   # qty, mo10*q, mo30*q, cap*q
        for tk, rx, sign, pc, q in rows:
            m10, m30, m0 = mo(tk, rx, sign, pc, 10), mo(tk, rx, sign, pc, 30), mo(tk, rx, sign, pc, 0)
            if m10 is None or m30 is None or m0 is None:
                continue
            k = bucket(tk, rx)
            acc[k][0] += q
            acc[k][1] += m10 * q
            acc[k][2] += m30 * q
            acc[k][3] += m0 * q
        tot = sum(v[0] for v in acc.values()) or 1
        print(f"{title}\n\n| bucket | contracts | share | half-spread at fill ¢ | mo10 ¢ | mo30 ¢ | $ at 30 s |\n|---|---|---|---|---|---|---|")
        for k in order:
            q, m10, m30, cap = acc.get(k, [0, 0, 0, 0])
            if q:
                print(f"| {k} | {q:,.0f} | {q / tot * 100:.0f}% | {cap / q:+.2f} | {m10 / q:+.2f} | {m30 / q:+.2f} | {m30 / 100:+.1f} |")
        print()

    report("Market-wide: maker side of every touch trade", trades)
    if a.fills and a.fills.exists():
        f = pl.read_parquet(a.fills)
        rows = [(r["ticker"], int(r["rx"]), 1 if r["side"] == "yes" else -1,
                 (r["price"] if r["side"] == "yes" else ONE - r["price"]) / 100, r["qty"] / QTY) for r in f.iter_rows(named=True)]
        report(f"Our simulated fills ({a.fills.name})", rows)


if __name__ == "__main__":
    main()
