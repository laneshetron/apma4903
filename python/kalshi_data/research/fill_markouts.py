"""Fill-by-fill markouts for the live and paper quoters against the collector's book.

For every quoter fill on the tape, mark the fill against the market's mid
(from the collector tape) at the fill time and h seconds later. A maker fill
on a YES bid at p earns (mid - p) at the fill and keeps or loses it as the
mid moves. Reports per horizon, split live vs paper, plus per-market totals.

    uv run python -m kalshi_data.research.fill_markouts 2026-09-17 --data-dir ../data_aws [--from 04:13]
"""

from __future__ import annotations

import argparse
import bisect
import collections
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

from ..raw import iter_records
from ..replay import Replayer, BookUpdate

HORIZONS = (1, 10, 30)


def mid_series(data_dir: Path, day: date, tickers: set[str]) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """ticker -> (rx_ns, mid_cents) at every top-of-book change."""
    rp = Replayer()
    out = {t: ([], []) for t in tickers}
    last = {}
    for rec in iter_records(data_dir, day):
        up = rp.feed(rec)
        if not isinstance(up, BookUpdate) or up.ticker not in tickers:
            continue
        m = rp.book(up.ticker).top().mid
        if m is None or m == last.get(up.ticker):
            continue
        last[up.ticker] = m
        out[up.ticker][0].append(rec.rx_ns)
        out[up.ticker][1].append(m / 100)  # price units 1/10000 -> cents
    return {t: (np.array(a), np.array(b)) for t, (a, b) in out.items()}


def quoter_fills(tape: Path, day: date, start_ns: int) -> list[dict]:
    fills = []
    for rec in iter_records(tape, day):
        raw = rec.raw
        if raw.get("type") == "_local" and raw.get("event") == "quoter" and raw.get("kind") == "fill" and rec.rx_ns >= start_ns:
            fills.append({"rx_ns": rec.rx_ns, "ticker": raw["ticker"], "side": raw["side"], "price": float(raw["price"]) * 100,
                          "qty": float(raw["qty"]), "taker": bool(raw.get("taker", False)), "fee": float(raw.get("fee", 0) or 0)})
    return fills


def mid_at(series, t_ns: int) -> float | None:
    rx, mids = series
    i = bisect.bisect_right(rx, t_ns) - 1
    return float(mids[i]) if i >= 0 else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, default=Path("../data_aws"))
    ap.add_argument("--from", dest="from_", default="00:00", help="HH:MM UTC, ignore fills before this")
    a = ap.parse_args()
    start_ns = int(datetime.combine(a.day, datetime.strptime(a.from_, "%H:%M").time(), tzinfo=timezone.utc).timestamp() * 1e9)
    modes = {}
    for mode in ("live", "paper"):
        tape = a.data_dir / "quoter" / mode
        if tape.is_dir():
            modes[mode] = quoter_fills(tape, a.day, start_ns)
    tickers = {f["ticker"] for fs in modes.values() for f in fs}
    series = mid_series(a.data_dir, a.day, tickers)

    print(f"# Fill markouts, {a.day} from {a.from_} UTC (maker fills only; cents/contract, volume-weighted; + = we earned)\n")
    print("| mode | fills | contracts | half-spread at fill | mo 1s | mo 10s | mo 30s | net/contract 30s | est. P&L $ |\n|---|---|---|---|---|---|---|---|---|")
    per_mkt = collections.defaultdict(lambda: collections.defaultdict(lambda: {"n": 0, "q": 0.0, "pnl30": 0.0, "cap": 0.0, "adv": 0.0}))
    for mode, fills in modes.items():
        rows = []
        for f in fills:
            if f["taker"]:
                continue
            s = series.get(f["ticker"])
            if s is None or len(s[0]) == 0:
                continue
            m0 = mid_at(s, f["rx_ns"])
            if m0 is None:
                continue
            sign = 1 if f["side"] == "yes" else -1          # long YES after a YES fill; short after a NO fill
            px = f["price"] if f["side"] == "yes" else 100 - f["price"]  # YES price we transacted at
            cap = sign * (m0 - px)                           # half-spread captured at the fill (cents)
            mo = {}
            for h in HORIZONS:
                mh = mid_at(s, f["rx_ns"] + h * 1_000_000_000)
                mo[h] = sign * (mh - px) if mh is not None else np.nan   # P&L per contract if unwound at mid h seconds later
            rows.append((f["qty"], cap, mo))
            f["mo30"] = mo[30]
            pm = per_mkt[f["ticker"]][mode]
            pm["n"] += 1
            pm["q"] += f["qty"]
            pm["cap"] += cap * f["qty"]
            if not np.isnan(mo[30]):
                pm["pnl30"] += mo[30] * f["qty"]
                pm["adv"] += (mo[30] - cap) * f["qty"]
        if not rows:
            continue
        w = np.array([r[0] for r in rows])
        cap = np.array([r[1] for r in rows])
        wm = lambda x: float(np.nansum(x * w) / w[~np.isnan(x)].sum())
        mos = {h: np.array([r[2][h] for r in rows]) for h in HORIZONS}
        print(f"| {mode} | {len(rows)} | {w.sum():,.0f} | {wm(cap):+.2f} | {wm(mos[1]):+.2f} | {wm(mos[10]):+.2f} | {wm(mos[30]):+.2f} | {wm(mos[30]):+.2f} | {wm(mos[30]) * w.sum() / 100:+.2f} |")

    print("\nPer market (30s markout; adverse = markout - half-spread captured):\n")
    print("| market | mode | fills | contracts | half-spread $ | adverse $ | P&L @30s $ |\n|---|---|---|---|---|---|---|")
    for tk in sorted(per_mkt):
        for mode in ("live", "paper"):
            pm = per_mkt[tk].get(mode)
            if not pm or pm["n"] == 0:
                continue
            print(f"| {tk[-7:]} | {mode} | {pm['n']} | {pm['q']:,.0f} | {pm['cap'] / 100:+.2f} | {pm['adv'] / 100:+.2f} | {pm['pnl30'] / 100:+.2f} |")
    sweep_context(a.data_dir, a.day, modes)



def sweep_context(data_dir: Path, day: date, fills: dict[str, list[dict]]) -> None:
    """For each fill: was our level emptied within 300ms of the fill (a full sweep) or not (a partial)?"""
    rp = Replayer()
    tickers = {f["ticker"] for fs in fills.values() for f in fs}
    # per ticker/side/price: list of (rx_ns, qty_after) level sizes
    levels: dict[tuple, tuple[list, list]] = collections.defaultdict(lambda: ([], []))
    for rec in iter_records(data_dir, day):
        up = rp.feed(rec)
        if not isinstance(up, BookUpdate) or up.ticker not in tickers or up.side is None:
            continue
        b = rp.book(up.ticker)
        k = (up.ticker, up.side, up.price)
        levels[k][0].append(rec.rx_ns)
        levels[k][1].append(b.side(up.side).get(up.price, 0))
    out = {}
    for mode, fs in fills.items():
        stats = {"full": [0, 0.0, 0.0], "partial": [0, 0.0, 0.0]}  # n, qty, mo30*qty
        for f in fs:
            if f["taker"] or "mo30" not in f:
                continue
            k = (f["ticker"], f["side"], int(round(f["price"] * 100)))
            rx, sizes = levels.get(k, ([], []))
            if not rx:
                continue
            i = bisect.bisect_right(rx, f["rx_ns"] + 300_000_000) - 1
            emptied = i >= 0 and sizes[i] == 0
            s = stats["full" if emptied else "partial"]
            s[0] += 1
            s[1] += f["qty"]
            s[2] += f["mo30"] * f["qty"]
        out[mode] = stats
    print("\nFills by whether our level was emptied within 300ms (full sweep) or survived (partial):\n")
    print("| mode | class | fills | contracts | share | mo 30s |\n|---|---|---|---|---|---|")
    for mode, stats in out.items():
        tot = sum(s[1] for s in stats.values()) or 1
        for cls, s in stats.items():
            if s[1]:
                print(f"| {mode} | {cls} | {s[0]} | {s[1]:,.0f} | {s[1] / tot * 100:.0f}% | {s[2] / s[1]:+.2f} |")


if __name__ == "__main__":
    main()
