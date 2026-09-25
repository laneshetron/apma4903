"""Test B: on a continuous perp book, do fills away from the touch revert?

The Kalshi version is `offset_markouts.py`. This is the same question on Hyperliquid, where
the answer is supposed to differ: a sweep that overshoots a few bps on a perp should snap back,
and that reversion is what pays a maker resting outside the touch.

**Why this does not use the book.** Hyperliquid publishes `l2Book` every ~5.4 s, and its `bbo`
(~125 ms) is worse than useless for the pre-trade touch: 98.7% of trades carry the *same*
exchange millisecond as the bbo we hold, because that bbo is the update the trade caused. Any
"offset beyond the touch" computed against it measures the print against the book *after* it.

So the offset comes from the trades feed alone. A taker order that walks the book prints several
times under one `(coin, exchange ms, side)` key, monotonically 98.9% of the time (`hash` is
worse -- it is an L1 transaction and mixes unrelated fills, one group held 72,746 prints).
Within such a burst the **first print executed at the touch by construction**, so

    offset_bp(print i) = (px_i - px_first) / mid * 1e4     side B (taker buying, walking up)
                       = (px_first - px_i) / mid * 1e4     side A (taker selling, walking down)

needs no book at all. Only the markout uses bbo mids, where a 125 ms publish lag is irrelevant
against 1-300 s horizons.

Sign convention is the maker's; + means the resting maker earned. Verified on the data: side B
bursts walk up 98.9% of the time and side A bursts walk down, so B = aggressor buying (the maker
sold) and A = aggressor selling (the maker bought).

    uv run python -m kalshi_data.research.hl_offset 2026-09-16 --end 2026-09-25 --data-dir ../data_hl
"""

from __future__ import annotations

import argparse
import bisect
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

from ..raw import iter_records

HORIZONS = (1, 10, 60, 300)
OFF_BUCKETS = ((0.0, "at touch"), (1.0, "0-1 bp"), (3.0, "1-3 bp"), (10.0, "3-10 bp"), (float("inf"), "10 bp+"))
PRUNE_EVERY = 4096


def bucket(v: float, table) -> str:
    for hi, name in table:
        if v <= hi:
            return name
    return table[-1][1]


class Acc:
    __slots__ = ("n", "notional", "mo", "win")

    def __init__(self) -> None:
        self.n = 0
        self.notional = 0.0
        self.mo = [0.0] * len(HORIZONS)
        self.win = 0.0

    def add(self, notional: float, mo_bp: list[float]) -> None:
        self.n += 1
        self.notional += notional
        if mo_bp[-1] > 0:
            self.win += notional
        for i, m in enumerate(mo_bp):
            self.mo[i] += m * notional


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--end", type=date.fromisoformat, default=None)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--coins", default=None)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    coins = set(a.coins.split(",")) if a.coins else None

    keep_ns = (max(HORIZONS) + 5) * 1_000_000_000
    mid_rx: dict[str, list[int]] = defaultdict(list)
    mid_v: dict[str, list[float]] = defaultdict(list)
    cur: dict[str, list] = {}           # coin -> [exch_ms, side, rx, [(px, sz), ...]]
    pending: deque = deque()
    by_off: dict[tuple[str, str], Acc] = defaultdict(Acc)
    n_prints = n_scored = n_nomid = n_nonmono = 0
    burst_sizes: dict[int, int] = defaultdict(int)

    def mid_at(coin: str, at: int) -> float | None:
        r = mid_rx[coin]
        i = bisect.bisect_right(r, at) - 1
        return mid_v[coin][i] if i >= 0 else None

    def resolve(now_rx: int, flush: bool = False) -> None:
        nonlocal n_scored, n_nomid
        while pending and (flush or pending[0][0] <= now_rx):
            _, coin, rx, sign, px, notional, offb = pending.popleft()
            ref = mid_at(coin, rx)
            mo = []
            for h in HORIZONS:
                m = mid_at(coin, rx + h * 1_000_000_000)
                mo.append(sign * (m - px) / ref * 1e4 if (m is not None and ref) else None)
            if any(m is None for m in mo):
                n_nomid += 1
                continue
            n_scored += 1
            by_off[(coin, offb)].add(notional, mo)

    def flush_burst(coin: str) -> None:
        nonlocal n_nonmono
        got = cur.pop(coin, None)
        if not got:
            return
        _, side, rx, prints = got
        burst_sizes[min(len(prints), 10)] += 1
        ref = mid_at(coin, rx)
        if ref is None:
            return
        walk = [p for p, _ in prints]
        # a burst that does not walk away from the aggressor is not one order walking the book
        if len(walk) > 1 and not (all(b >= a for a, b in zip(walk, walk[1:])) if side == "B"
                                  else all(b <= a for a, b in zip(walk, walk[1:]))):
            n_nonmono += 1
            return
        px0 = walk[0]
        sign = -1 if side == "B" else 1          # B: taker bought, so the resting maker sold
        for px, sz in prints:
            off_bp = ((px - px0) if side == "B" else (px0 - px)) / ref * 1e4
            pending.append((rx + max(HORIZONS) * 1_000_000_000, coin, rx, sign, px, px * sz,
                            bucket(max(off_bp, 0.0), OFF_BUCKETS)))

    end = a.end or a.day
    for rec in iter_records(a.data_dir, a.day, end):
        raw = rec.raw
        ch = raw.get("channel")
        rx = rec.rx_ns
        if ch == "bbo":
            d = raw["data"]
            coin = d["coin"]
            if coins and coin not in coins:
                continue
            b, o = d["bbo"]
            if not b or not o:
                continue
            m = (float(b["px"]) + float(o["px"])) / 2
            r, v = mid_rx[coin], mid_v[coin]
            if not v or v[-1] != m:
                r.append(rx)
                v.append(m)
                if len(r) % PRUNE_EVERY == 0:
                    cut = bisect.bisect_left(r, rx - keep_ns) - 1
                    if cut > 0:
                        del r[:cut]
                        del v[:cut]
            resolve(rx)
            continue
        if ch != "trades":
            continue
        for t in raw["data"]:
            coin = t["coin"]
            if coins and coin not in coins:
                continue
            n_prints += 1
            got = cur.get(coin)
            if got is not None and (got[0] != t["time"] or got[1] != t["side"]):
                flush_burst(coin)
                got = None
            if got is None:
                cur[coin] = [t["time"], t["side"], rx, []]
            cur[coin][3].append((float(t["px"]), float(t["sz"])))
    for c in list(cur):
        flush_burst(c)
    resolve(0, flush=True)

    lines: list[str] = []
    w = lines.append
    span = f"{a.day}" if end == a.day else f"{a.day}..{end}"
    w(f"# Hyperliquid burst-relative offset markouts, {span}\n")
    w(f"{n_prints:,} prints, {n_scored:,} scored, {n_nomid:,} without a mid, "
      f"{n_nonmono:,} non-monotonic bursts dropped.\n")
    w("Offset is measured **within a taker's sweep**, against the burst's first print (which "
      "executed at the touch); no order book is involved. Markout in **bps of mid**, "
      "notional-weighted, + = the resting maker earned.\n")
    hdr = " | ".join(f"mo{h}s" for h in HORIZONS)
    w(f"| coin | offset into the sweep | prints | notional $ | {hdr} | win% |")
    w("|---|---|---|---|" + "---|" * len(HORIZONS) + "---|")
    for coin in sorted({c for c, _ in by_off}):
        for _, name in OFF_BUCKETS:
            acc = by_off.get((coin, name))
            if not acc or not acc.notional:
                continue
            mo = " | ".join(f"{m / acc.notional:+.3f}" for m in acc.mo)
            w(f"| {coin} | {name} | {acc.n:,} | {acc.notional:,.0f} | {mo} | {acc.win / acc.notional * 100:.0f}% |")
    w("")
    w("Burst size distribution (prints per taker order; 10+ bucketed):\n")
    w("| prints | bursts |")
    w("|---|---|")
    for k in sorted(burst_sizes):
        w(f"| {k}{'+' if k == 10 else ''} | {burst_sizes[k]:,} |")
    text = "\n".join(lines)
    print(text)
    if a.out:
        a.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
