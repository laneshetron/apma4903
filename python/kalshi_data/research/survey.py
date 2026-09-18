"""Which recorded markets are makeable by a REST participant?

Per series (and per market) on one day, from the collector tape alone:
  spread_c          time-weighted spread while two-sided, cents
  touch_life_ms     median lifetime of a touch level (from becoming the best to vacating)
  vac/h             touch vacates per hour of two-sided time
  refill<=2ms       share of vacates where a bid appears at the vacated price within 2 ms (the
                    vacator re-creating the level: the "rolling quoter" signature)
  refill<=16ms      ... within 16 ms (before a WS reader can react)
  refill<=2s        ... within 2 s at all
  taker/h           contracts traded per two-sided hour
  sweep%            share of traded contracts in trades that emptied the touch level
  mo10 / mo30       maker markout of every touch trade, cents/contract, volume-weighted
                    (+ = the maker earned; the market's toxicity independent of our queue)
  touch_size        median contracts at the touch (both sides)

    uv run python -m kalshi_data.research.survey 2026-09-17 --data-dir ../data_aws [--series KXBTC15M KXETH15M KXBTCD]
"""

from __future__ import annotations

import argparse
import bisect
import statistics as st
import sys
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

import numpy as np

from ..book import parse_price, parse_qty
from ..raw import iter_records
from .markouts import FastBook

ONE = 10_000
QTY = 100


class MStat:
    __slots__ = ("book", "series", "two_sided_since", "two_sided_ns", "spread_ns", "touch_since", "lives", "vac", "refill", "pend",
                 "traded", "swept", "mo10", "mo30", "mo_qty", "mids", "pending_mo", "sizes", "last_rx", "vol_by_hour", "mid_med")

    def __init__(self, series: str):
        self.book = FastBook()
        self.series = series
        self.two_sided_since = None
        self.two_sided_ns = 0
        self.spread_ns = 0.0          # integral of spread (price units) over two-sided time
        self.touch_since = {"yes": None, "no": None}
        self.lives: list[float] = []
        self.vac = 0
        self.refill = [0, 0, 0]       # <=2ms, <=16ms, <=2s
        self.pend: deque = deque()    # (rx, side, price) vacates awaiting a refill
        self.traded = 0.0
        self.swept = 0.0
        self.mo10 = self.mo30 = self.mo_qty = 0.0
        self.mids: tuple[deque, deque] = (deque(), deque())   # last ~40 s of mid changes (bounded)
        self.pending_mo: deque = deque()   # (rx, sign, price_c, qty)
        self.sizes: list[float] = []
        self.mid_med: list[float] = []
        self.last_rx = 0

    def mid(self) -> float | None:
        b = self.book
        if b.best_yes < 0 or b.best_no < 0:
            return None
        return (b.best_yes + ONE - b.best_no) / 2 / 100


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, default=Path("../data_aws"))
    ap.add_argument("--series", nargs="*", default=["KXBTC15M", "KXETH15M", "KXBTCD"])
    ap.add_argument("--per-market", action="store_true")
    a = ap.parse_args()
    ms: dict[str, MStat] = {}
    n = 0
    for rec in iter_records(a.data_dir, a.day):
        raw = rec.raw
        t = raw.get("type")
        if t not in ("orderbook_snapshot", "orderbook_delta", "trade"):
            continue
        tk = raw["msg"]["market_ticker"]
        ser = tk.split("-")[0]
        if ser not in a.series:
            continue
        n += 1
        if n % 5_000_000 == 0:
            print(f"  {n/1e6:.0f}M msgs", file=sys.stderr)
        m = ms.get(tk)
        if m is None:
            m = ms[tk] = MStat(ser)
        rx = rec.rx_ns
        b = m.book
        was_two = b.best_yes >= 0 and b.best_no >= 0
        prev_best = {"yes": b.best_yes, "no": b.best_no}
        if was_two:
            spread = ONE - b.best_no - b.best_yes
            m.spread_ns += spread * (rx - m.last_rx)
            m.two_sided_ns += rx - m.last_rx
        m.last_rx = rx
        # resolve markouts due
        mid_now = m.mid()
        if mid_now is not None:
            mids_rx, mids_v = m.mids
            if not mids_v or mids_v[-1] != mid_now:
                mids_rx.append(rx)
                mids_v.append(mid_now)
                while mids_rx and rx - mids_rx[0] > 40_000_000_000 and len(mids_rx) > 1:
                    mids_rx.popleft()
                    mids_v.popleft()
            m.mid_med.append(mid_now) if n % 200 == 0 else None
        while m.pending_mo and rx - m.pending_mo[0][0] > 30_000_000_000:
            trx, sign, pc, q = m.pending_mo.popleft()
            m10 = _mid_at(m.mids, trx + 10_000_000_000)
            m30 = _mid_at(m.mids, trx + 30_000_000_000)
            if m10 is not None and m30 is not None:
                m.mo10 += sign * (m10 - pc) * q
                m.mo30 += sign * (m30 - pc) * q
                m.mo_qty += q
        if t == "orderbook_snapshot":
            b.snapshot(raw["msg"])
        elif t == "orderbook_delta":
            msg = raw["msg"]
            side, price, d = msg["side"], parse_price(msg["price_dollars"]), parse_qty(msg["delta_fp"])
            try:
                b.delta(side, price, d)
            except ValueError:
                continue
        else:
            msg = raw["msg"]
            q = parse_qty(msg["count_fp"]) / QTY
            yes_price = parse_price(msg["yes_price_dollars"])
            hit = "no" if msg["taker_side"] == "yes" else "yes"
            m.traded += q
            # maker at the hit side transacted at yes_price (yes bid) or sold YES at yes_price (no bid): sign for maker
            sign = 1 if hit == "yes" else -1
            m.pending_mo.append((rx, sign, yes_price / 100, q))
            # sweep: the trade price is worse for the taker than the touch, or the level is gone right after
            lvl_price = yes_price if hit == "yes" else ONE - yes_price
            if b.side(hit).get(lvl_price, 0) == 0 or (hit == "yes" and yes_price < prev_best["yes"]) or (hit == "no" and ONE - yes_price < prev_best["no"]):
                m.swept += q
            continue
        # touch changes
        for s in ("yes", "no"):
            bp = b.best(s)
            if bp != prev_best[s]:
                if m.touch_since[s] is not None and prev_best[s] >= 0:
                    m.lives.append((rx - m.touch_since[s]) / 1e6)
                m.touch_since[s] = rx
                if prev_best[s] >= 0 and bp < prev_best[s]:
                    m.vac += 1
                    other = "no" if s == "yes" else "yes"
                    m.pend.append((rx, other, ONE - prev_best[s]))
        # refills: a level born on the other side at the vacated price
        if t == "orderbook_delta" and d > 0 and b.side(side).get(price, 0) == d:
            for i in range(len(m.pend) - 1, -1, -1):
                vrx, vs, vp = m.pend[i]
                if rx - vrx > 2_000_000_000:
                    break
                if vs == side and vp == price:
                    lag = (rx - vrx) / 1e6
                    m.refill[2] += 1
                    if lag <= 16:
                        m.refill[1] += 1
                    if lag <= 2:
                        m.refill[0] += 1
                    del m.pend[i]
                    break
        while m.pend and rx - m.pend[0][0] > 2_000_000_000:
            m.pend.popleft()
        if was_two and n % 50 == 0:
            m.sizes.append((b.side("yes").get(b.best_yes, 0) + b.side("no").get(b.best_no, 0)) / 2 / QTY)

    rows = []
    for tk, m in ms.items():
        if m.two_sided_ns < 60e9:
            continue
        rows.append((m.series, tk, m))
    print(f"# Market survey, {a.day}: {len(rows)} markets with >= 1 min two-sided\n")
    hdr = "| group | markets | two-sided h | spread_c | touch_size | touch_life_ms | vac/h | refill<=2ms | refill<=16ms | refill<=2s | taker/h | sweep% | mo10_c | mo30_c |"
    print(hdr + "\n" + "|" + "---|" * 14)

    def agg(name, group):
        two_h = sum(m.two_sided_ns for _, _, m in group) / 3.6e12
        spread = sum(m.spread_ns for _, _, m in group) / max(1, sum(m.two_sided_ns for _, _, m in group)) / 100
        lives = [x for _, _, m in group for x in m.lives]
        sizes = [x for _, _, m in group for x in m.sizes]
        vac = sum(m.vac for _, _, m in group)
        rf = [sum(m.refill[i] for _, _, m in group) for i in range(3)]
        traded = sum(m.traded for _, _, m in group)
        swept = sum(m.swept for _, _, m in group)
        moq = sum(m.mo_qty for _, _, m in group)
        mo10 = sum(m.mo10 for _, _, m in group) / moq if moq else float("nan")
        mo30 = sum(m.mo30 for _, _, m in group) / moq if moq else float("nan")
        print(f"| {name} | {len(group)} | {two_h:.1f} | {spread:.2f} | {st.median(sizes) if sizes else 0:.0f} | {st.median(lives) if lives else 0:.0f} | {vac / max(two_h, 1e-9):.0f} | "
              f"{rf[0] / max(vac, 1) * 100:.0f}% | {rf[1] / max(vac, 1) * 100:.0f}% | {rf[2] / max(vac, 1) * 100:.0f}% | {traded / max(two_h, 1e-9):,.0f} | {swept / max(traded, 1) * 100:.0f}% | {mo10:+.2f} | {mo30:+.2f} |")

    for ser in a.series:
        g = [r for r in rows if r[0] == ser]
        if g:
            agg(ser, g)
    # KXBTCD by moneyness bucket (price level): near-the-money vs tails
    for ser in a.series:
        g = [r for r in rows if r[0] == ser]
        if len(g) < 6:
            continue
        buckets = defaultdict(list)
        for r in g:
            m = r[2]
            mid = st.median(m.mid_med) if m.mid_med else None
            if mid is None:
                continue
            buckets["tails (<10c or >90c)" if mid < 10 or mid > 90 else "mid (10-90c)"].append(r)
        for k, gg in buckets.items():
            agg(f"{ser} {k}", gg)
    if a.per_market:
        for ser in a.series:
            print(f"\n{ser}, top 20 markets by volume:\n")
            print(hdr + "\n" + "|" + "---|" * 14)
            for s_, tk, m in sorted([r for r in rows if r[0] == ser], key=lambda r: -r[2].traded)[:20]:
                agg(tk, [(s_, tk, m)])


def _mid_at(series, t_ns):
    rx, v = series
    i = bisect.bisect_right(list(rx), t_ns) - 1
    return v[i] if i >= 0 else None


if __name__ == "__main__":
    main()
