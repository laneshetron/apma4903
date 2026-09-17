"""Observed queue positions of the live quoter's orders vs the simulator's model.

For every live order on the quoter tape: queue ahead at placement (level size
on the collector tape when the order went live), whether it filled, time to
first fill, and queue ahead at the fill (contracts of the filling sweep that
traded before our share).

    uv run python -m kalshi_data.research.queue_obs 2026-09-17 --data-dir ../data_aws --from 04:13
"""

from __future__ import annotations

import argparse
import bisect
import collections
from datetime import date, datetime, timezone
from pathlib import Path

from ..raw import iter_records
from ..replay import Replayer, BookUpdate


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, default=Path("../data_aws"))
    ap.add_argument("--from", dest="from_", default="00:00")
    ap.add_argument("--place-latency-ms", type=float, default=9.0)
    a = ap.parse_args()
    start_ns = int(datetime.combine(a.day, datetime.strptime(a.from_, "%H:%M").time(), tzinfo=timezone.utc).timestamp() * 1e9)

    orders: dict[str, dict] = {}
    by_id: dict[str, dict] = {}
    for rec in iter_records(a.data_dir / "quoter" / "live", a.day):
        raw = rec.raw
        if raw.get("type") != "_local" or raw.get("event") != "quoter" or rec.rx_ns < start_ns:
            continue
        k = raw["kind"]
        if k == "place":
            orders[raw["client_id"]] = {"ticker": raw["ticker"], "side": raw["side"], "price": int(round(float(raw["price"]) * 10000)),
                                        "qty": float(raw["qty"]), "placed": rec.rx_ns, "fills": [], "done": None}
        elif k == "place_ack" and raw["client_id"] in orders:
            by_id[raw["order_id"]] = orders[raw["client_id"]]
            orders[raw["client_id"]]["acked"] = rec.rx_ns
        elif k == "fill" and raw.get("order_id") in by_id and not raw.get("taker"):
            by_id[raw["order_id"]]["fills"].append((rec.rx_ns, float(raw["qty"])))
        elif k == "done" and raw.get("order_id") in by_id:
            by_id[raw["order_id"]]["done"] = rec.rx_ns
    tickers = {o["ticker"] for o in orders.values()}

    rp = Replayer()
    levels: dict[tuple, tuple[list, list]] = collections.defaultdict(lambda: ([], []))
    trades: dict[tuple, list] = collections.defaultdict(list)
    for rec in iter_records(a.data_dir, a.day):
        raw = rec.raw
        if raw.get("type") == "trade" and raw["msg"]["market_ticker"] in tickers:
            m = raw["msg"]
            side = "yes" if m["taker_side"] == "no" else "no"
            yp = int(round(float(m["yes_price_dollars"]) * 10000))
            price = yp if side == "yes" else 10000 - yp
            trades[(m["market_ticker"], side, price)].append((rec.rx_ns, m["ts_ms"], float(m["count_fp"])))
            continue
        up = rp.feed(rec)
        if not isinstance(up, BookUpdate) or up.ticker not in tickers or up.side is None:
            continue
        b = rp.book(up.ticker)
        k = (up.ticker, up.side, up.price)
        levels[k][0].append(rec.rx_ns)
        levels[k][1].append(b.side(up.side).get(up.price, 0) / 100)

    acked = [o for o in orders.values() if "acked" in o]
    ahead_place, ahead_fill, ttf, share, lifetimes = [], [], [], [], []
    filled = 0
    for o in acked:
        k = (o["ticker"], o["side"], o["price"])
        rx, sizes = levels.get(k, ([], []))
        live_at = o["placed"] + int(a.place_latency_ms * 1e6)
        i = bisect.bisect_right(rx, live_at) - 1
        ap_ = sizes[i] if i >= 0 else 0.0
        ahead_place.append(ap_)
        end = o["done"] or (o["fills"][-1][0] if o["fills"] else None)
        if end:
            lifetimes.append((end - live_at) / 1e9)
        if o["fills"]:
            filled += 1
            t0, q0 = o["fills"][0]
            ttf.append((t0 - live_at) / 1e9)
            tr = trades.get(k, [])
            swept = sum(q for r, _, q in tr if t0 - 300_000_000 <= r <= t0 + 50_000_000)
            af = max(0.0, swept - q0)
            ahead_fill.append(af)
            if ap_ > 0:
                share.append(min(1.0, af / ap_))
    q = lambda xs, p: sorted(xs)[int(p * (len(xs) - 1))] if xs else float("nan")
    print(f"live orders acknowledged: {len(acked)}; filled at least partly: {filled} ({filled / max(len(acked), 1) * 100:.0f}%)")
    print(f"order lifetime before cancel/fill (s): p50 {q(lifetimes, .5):.2f}  p90 {q(lifetimes, .9):.2f}")
    print(f"ahead at placement (contracts): p25 {q(ahead_place, .25):.0f}  p50 {q(ahead_place, .5):.0f}  p75 {q(ahead_place, .75):.0f}")
    print(f"ahead at first fill (contracts of the sweep traded before our share): p25 {q(ahead_fill, .25):.0f}  p50 {q(ahead_fill, .5):.0f}  p75 {q(ahead_fill, .75):.0f}")
    print(f"time to first fill (s): p50 {q(ttf, .5):.2f}  p90 {q(ttf, .9):.2f}")
    print(f"consumed-before-us / level-at-placement: p25 {q(share, .25):.2f}  p50 {q(share, .5):.2f}  p75 {q(share, .75):.2f}  (1 = the whole level traded before us; 0 = we were first)")


if __name__ == "__main__":
    main()
