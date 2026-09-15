"""Market-impact event study: how does the book respond to a large order joining the touch?

    uv run python -m kalshi_data.research.impact 2026-09-14 [--end 2026-09-15]

Events: one orderbook_delta adding >= N contracts at the current best price on
its side. For each, over the next 1s and 5s at that level and the opposite touch:
  cancels    contracts removed by others (negative deltas minus trade volume; a
             single cancel equal to the event's own size is excluded as likely its own)
  joins      contracts added behind it
  traded     contracts taken from the level by sweeps
  swept      the level was emptied within the horizon
  dmid       mid move toward the event side (cents): price impact
  opp_moved  the opposite best price changed
Compared with small adds (1-20 contracts) as control.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from ..book import parse_price, parse_qty
from ..raw import iter_records
from .markouts import FastBook, close_time

ONE = 10_000
BUCKETS = [(1, 20, "1-20 (control)"), (20, 50, "20-50"), (50, 100, "50-100"), (100, 300, "100-300"), (300, 1000, "300-1000"), (1000, 10**9, ">=1000")]
H = (1.0, 5.0)


class Event:
    __slots__ = ("rx", "tk", "side", "price", "qty", "bucket", "mid0", "opp_best0", "opp_depth0", "level0",
                 "cancels", "joins", "traded", "swept", "done", "res", "improving")

    def __init__(self, rx, tk, side, price, qty, bucket, book: FastBook, improving: bool):
        self.rx, self.tk, self.side, self.price, self.qty, self.bucket, self.improving = rx, tk, side, price, qty, bucket, improving
        self.mid0 = book.mid()
        opp = "no" if side == "yes" else "yes"
        self.opp_best0 = book.best(opp)
        self.opp_depth0 = book.side(opp).get(self.opp_best0, 0)
        self.level0 = book.side(side).get(price, 0)   # includes the event's own qty
        self.cancels = {h: 0 for h in H}
        self.joins = {h: 0 for h in H}
        self.traded = {h: 0 for h in H}
        self.swept = {h: False for h in H}
        self.done = {h: False for h in H}
        self.res = {}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--end", type=date.fromisoformat, default=None)
    ap.add_argument("--data-dir", type=Path, default=Path("../data"))
    ap.add_argument("--series", default="KXBTC15M")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    books: dict[str, FastBook] = {}
    active: dict[tuple, list[Event]] = defaultdict(list)   # (tk, side, price) -> events
    by_tk: dict[str, list[Event]] = defaultdict(list)
    finished: list[Event] = []
    pending_neg: dict[tuple, list] = defaultdict(list)     # (tk, side, price) -> [(rx, ts_ms, qty)] awaiting trade attribution

    def resolve(ev: Event, h: float, book: FastBook, rx: int) -> None:
        ev.done[h] = True
        mid = book.mid()
        sign = 1 if ev.side == "yes" else -1   # a big bid pushes the mid up = impact toward the event side
        opp = "no" if ev.side == "yes" else "yes"
        ev.res[h] = {
            "dmid": None if (mid is None or ev.mid0 is None) else sign * (mid - ev.mid0),
            "opp_moved": book.best(opp) != ev.opp_best0,
            "opp_depth_chg": (book.side(opp).get(book.best(opp), 0) - ev.opp_depth0) / 100,
            "level_now": book.side(ev.side).get(ev.price, 0) / 100,
        }

    def flush_neg(key, rx, book):
        # unexplained negative deltas older than 200ms are cancels
        lst = pending_neg.get(key)
        if not lst:
            return
        keep = []
        for r0, ts, q in lst:
            if r0 < rx - 200_000_000:
                for ev in active.get(key, []):
                    for h in H:
                        if not ev.done[h] and r0 > ev.rx:
                            if q == ev.qty:
                                continue   # likely the event's own cancel
                            ev.cancels[h] += q
            else:
                keep.append((r0, ts, q))
        pending_neg[key] = keep

    n = 0
    for rec in iter_records(a.data_dir, a.day, a.end):
        n += 1
        if n % 10_000_000 == 0:
            print(f"  {n/1e6:.0f}M records, {len(finished):,} events", file=sys.stderr)
        raw = rec.raw
        t = raw.get("type")
        if t == "_local":
            if raw.get("event") in ("connect", "disconnect"):
                for b in books.values():
                    b.stale = True
            continue
        if t not in ("orderbook_snapshot", "orderbook_delta", "trade"):
            continue
        msg = raw["msg"]
        tk = msg["market_ticker"]
        if not tk.startswith(a.series + "-"):
            continue
        rx = rec.rx_ns
        b = books.get(tk)
        if b is None:
            b = books[tk] = FastBook()
        # resolve horizons for this market's events
        for ev in by_tk.get(tk, []):
            for h in H:
                if not ev.done[h] and rx >= ev.rx + int(h * 1e9):
                    resolve(ev, h, b, rx)
        by_tk[tk] = [ev for ev in by_tk[tk] if not all(ev.done.values())] if tk in by_tk else []
        for key in list(active):
            if key[0] == tk:
                active[key] = [ev for ev in active[key] if not all(ev.done.values())]
                if not active[key]:
                    del active[key]
        if t == "orderbook_snapshot":
            b.snapshot(msg)
            continue
        if t == "trade":
            side = "yes" if msg["taker_side"] == "no" else "no"
            price = parse_price(msg["yes_price_dollars"]) if side == "yes" else ONE - parse_price(msg["yes_price_dollars"])
            q = parse_qty(msg["count_fp"])
            key = (tk, side, price)
            # attribute pending negatives at this level with the same ts_ms to this trade
            left = q
            lst = pending_neg.get(key, [])
            keep = []
            for r0, ts, qq in lst:
                if ts == msg["ts_ms"] and left > 0:
                    take = min(qq, left)
                    left -= take
                    if qq - take > 0:
                        keep.append((r0, ts, qq - take))
                else:
                    keep.append((r0, ts, qq))
            pending_neg[key] = keep
            for ev in active.get(key, []):
                for h in H:
                    if not ev.done[h] and rx > ev.rx:
                        ev.traded[h] += q
                        if b.side(side).get(price, 0) == 0:
                            ev.swept[h] = True
            continue
        if b.stale:
            continue
        side, price, d = msg["side"], parse_price(msg["price_dollars"]), parse_qty(msg["delta_fp"])
        best_before = b.best(side)
        try:
            before = b.delta(side, price, d)
        except ValueError:
            b.stale = True
            continue
        key = (tk, side, price)
        flush_neg(key, rx, b)
        if d < 0:
            pending_neg[key].append((rx, msg.get("ts_ms", 0), -d))
        elif d > 0:
            for ev in active.get(key, []):
                for h in H:
                    if not ev.done[h] and rx > ev.rx:
                        ev.joins[h] += d
            # new event? an add at the best (join) or creating a new best (improving)
            if b.best(side) == price and b.best("no" if side == "yes" else "yes") >= 0:
                qc = d / 100
                for lo, hi, name in BUCKETS:
                    if lo <= qc < hi:
                        ev = Event(rx, tk, side, price, d, name, b, improving=price > best_before)
                        active[key].append(ev)
                        by_tk[tk].append(ev)
                        finished.append(ev)
                        break

    # ---- report ----
    L = [f"# Market impact event study, {a.series}, {a.day}" + (f" to {a.end}" if a.end else ""), "",
         "Response of the book to a single order joining the touch, by order size (contracts). Cancels/joins/traded in contracts at the event's level; "
         "swept = level emptied; dmid = mid move toward the event side in cents; opp moved = opposite best price changed.", ""]
    for improving in (False, True):
        L.append(f"## {'Improving orders (new best price)' if improving else 'Joins at the existing best'}")
        L.append("")
        L.append("| size | n | level before | 1s: cancels | joins | traded | swept | dmid | opp moved | 5s: cancels | joins | traded | swept | dmid | opp moved |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for lo, hi, name in BUCKETS:
            evs = [e for e in finished if e.bucket == name and e.improving == improving and all(e.done.values())]
            if len(evs) < 30:
                continue
            cells = [name, f"{len(evs):,}", f"{sum(e.level0 for e in evs)/len(evs)/100:,.0f}"]
            for h in H:
                dm = [e.res[h]["dmid"] for e in evs if e.res[h]["dmid"] is not None]
                cells += [f"{sum(e.cancels[h] for e in evs)/len(evs)/100:,.0f}", f"{sum(e.joins[h] for e in evs)/len(evs)/100:,.0f}",
                          f"{sum(e.traded[h] for e in evs)/len(evs)/100:,.0f}", f"{sum(e.swept[h] for e in evs)/len(evs)*100:.0f}%",
                          f"{sum(dm)/len(dm):+.2f}" if dm else "n/a", f"{sum(e.res[h]['opp_moved'] for e in evs)/len(evs)*100:.0f}%"]
            L.append("| " + " | ".join(cells) + " |")
        L.append("")
    text = "\n".join(L)
    print(text)
    if a.out:
        a.out.write_text(text)


if __name__ == "__main__":
    main()
