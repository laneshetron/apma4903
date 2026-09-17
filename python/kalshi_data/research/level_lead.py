"""How long after a spot move does the Kalshi touch move, and can an order sent
on the spot trigger be first at the new level?

Events: a Coinbase mid move of >= --move dollars within --window ms (first
crossing after a quiet period). For each event, on the side the move favours
(spot up -> YES bids should step up; spot down -> NO bids step up), find the
next new best-bid level on that side within 2 s: the lag from the spot
receipt to the first order appearing at the new level (tape time). An order we
send on the trigger lands at tape time spot_rx + our_ms (default 16: 1
decision + 9 REST + 6 engine lag); we are first at the level when that beats
the observed formation time.

    uv run python -m kalshi_data.research.level_lead 2026-09-17 --data-dir ../data_aws
"""

from __future__ import annotations

import argparse
import bisect
import heapq
import statistics as st
from datetime import date
from pathlib import Path

from ..raw import iter_records
from ..replay import Replayer, BookUpdate
from ..spot import iter_spot, SpotQuote


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, default=Path("../data_aws"))
    ap.add_argument("--series", default="KXBTC15M")
    ap.add_argument("--move", type=float, default=2.0, help="$ Coinbase mid move")
    ap.add_argument("--window", type=float, default=1000, help="ms over which the move is measured")
    ap.add_argument("--our-ms", type=float, default=16.0, help="tape-time latency of an order sent on the spot trigger")
    a = ap.parse_args()

    rp = Replayer()
    # per ticker/side: list of (rx_ns, best_price) whenever the best bid moves
    best: dict[tuple, tuple[list, list]] = {}
    # per ticker/side/price: first rx at which the level had size > 0 (level birth), reset when it empties
    birth: dict[tuple, int] = {}
    births: list[tuple[int, str, str, int]] = []  # (rx, ticker, side, price) for levels that became the touch
    spot_rx: list[int] = []
    spot_mid: list[float] = []

    def kalshi_events():
        for rec in iter_records(a.data_dir, a.day):
            yield rec.rx_ns, "k", rec

    def spot_events():
        for q in iter_spot(a.data_dir, "coinbase", a.day):
            if isinstance(q, SpotQuote) and q.asset == "BTC":
                yield q.rx_ns, "s", q

    prev_best: dict[tuple, int] = {}
    for rx, kind, ev in heapq.merge(kalshi_events(), spot_events(), key=lambda e: e[0]):
        if kind == "s":
            spot_rx.append(rx)
            spot_mid.append((ev.bid + ev.ask) / 2)
            continue
        up = rp.feed(ev)
        if not isinstance(up, BookUpdate) or not up.ticker.startswith(a.series):
            continue
        b = rp.book(up.ticker)
        if up.side is not None:
            k = (up.ticker, up.side, up.price)
            q = b.side(up.side).get(up.price, 0)
            if q > 0 and k not in birth:
                birth[k] = rx
            elif q == 0 and k in birth:
                del birth[k]
        for side in ("yes", "no"):
            bb = b.best_bid(side)
            if bb is None:
                continue
            bp = bb[0]
            key = (up.ticker, side)
            if prev_best.get(key) != bp:
                prev_best[key] = bp
                lst = best.setdefault(key, ([], []))
                lst[0].append(rx)
                lst[1].append(bp)
                if bp is not None and (up.ticker, side, bp) in birth:
                    births.append((birth[(up.ticker, side, bp)], up.ticker, side, bp))

    # spot move events: first crossing of +-move over the trailing window, then a refractory period of one window
    import numpy as np
    srx = np.array(spot_rx); smid = np.array(spot_mid)
    events = []
    last_ev = -1
    w = int(a.window * 1e6)
    for i in range(len(srx)):
        if srx[i] - last_ev < w:
            continue
        j = bisect.bisect_left(srx, srx[i] - w)
        d = smid[i] - smid[j]
        if abs(d) >= a.move:
            events.append((int(srx[i]), "yes" if d > 0 else "no"))
            last_ev = srx[i]
    print(f"# {a.day}: {len(events)} Coinbase moves of >= ${a.move} within {a.window:.0f} ms; touch-level formation lag after the move (tape time)\n")

    # index level births per (ticker, side) sorted by rx
    by_side: dict[tuple, tuple[list, list]] = {}
    for brx, tk, side, price in births:
        lst = by_side.setdefault((tk, side), ([], []))
        lst[0].append(brx); lst[1].append(price)
    for lst in by_side.values():
        order = np.argsort(lst[0]); lst[0][:] = [lst[0][i] for i in order]; lst[1][:] = [lst[1][i] for i in order]

    tickers = sorted({tk for tk, _ in by_side})
    lags = []
    for erx, side in events:
        # the market open at erx: the one with the latest touch update before erx
        cand = None
        for tk in tickers:
            key = (tk, side)
            if key not in best:
                continue
            rxs = best[key][0]
            i = bisect.bisect_right(rxs, erx) - 1
            if i >= 0 and erx - rxs[i] < 60e9:
                cand = tk
        if cand is None:
            continue
        rxs, prices = by_side.get((cand, side), ([], []))
        # first level born after the move on that side that becomes the touch and is above the touch at the move
        pb = prev_price_at(best[(cand, side)], erx)
        i = bisect.bisect_right(rxs, erx)
        while i < len(rxs) and rxs[i] - erx < 2e9:
            if prices[i] > pb:
                lags.append((rxs[i] - erx) / 1e6)
                break
            i += 1
    lags.sort()
    if not lags:
        print("no level formations found")
        return
    pct = lambda p: lags[min(len(lags) - 1, int(p * len(lags)))]
    print(f"| events with a new touch within 2 s | p10 | p25 | p50 | p75 | p90 | share before our {a.our_ms:.0f} ms |\n|---|---|---|---|---|---|---|")
    print(f"| {len(lags)} of {len(events)} | {pct(.1):.0f} | {pct(.25):.0f} | {pct(.5):.0f} | {pct(.75):.0f} | {pct(.9):.0f} | {sum(1 for l in lags if l < a.our_ms) / len(lags) * 100:.0f}% |")
    for ms in (5, 10, 16, 20, 30, 50, 100, 200):
        print(f"formed within {ms:>3} ms: {sum(1 for l in lags if l < ms) / len(lags) * 100:5.1f}%")


def prev_price_at(series, rx):
    rxs, prices = series
    i = bisect.bisect_right(rxs, rx) - 1
    return prices[i] if i >= 0 else 0


if __name__ == "__main__":
    main()
