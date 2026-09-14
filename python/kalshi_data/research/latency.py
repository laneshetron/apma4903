"""Latency regime: how fast is the competition at the front of the queue?

    uv run python -m kalshi_data.research.latency 2026-09-14 --series KXBTC15M

Measures, from the raw logs:
  1. transport latency: our receive time minus the exchange/index timestamp
  2. reaction time: after a BRTI tick that moves the index, how long until the
     first order at a NEW best price on the market, and until the first sweep
  3. queue-formation: after a new best level appears, how long until the
     second order joins it (the window in which you could have been first)
All in milliseconds. Our clock is NTP-synced; exchange stamps are ms.
"""

from __future__ import annotations

import argparse
import bisect
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from ..book import parse_price, parse_qty
from ..raw import iter_records
from .markouts import FastBook


def pct(xs, ps=(10, 50, 90, 99)):
    if not xs:
        return "n/a"
    xs = sorted(xs)
    return "  ".join(f"p{p}={xs[min(len(xs)-1, int(p/100*len(xs)))]:.0f}" for p in ps) + f"  (n={len(xs):,})"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, default=Path("../data"))
    ap.add_argument("--series", default="KXBTC15M")
    ap.add_argument("--index", default="BRTI")
    ap.add_argument("--move", type=float, default=5.0, help="index move ($) that counts as a signal")
    a = ap.parse_args()

    lat_delta, lat_trade, lat_idx_time, lat_idx_kalshi = [], [], [], []
    books: dict[str, FastBook] = defaultdict(FastBook)
    stale_all = True
    # index ticks: (rx_ms, value)
    idx_rx: list[float] = []
    idx_val: list[float] = []
    sig_rx: list[float] = []  # rx_ms of ticks that moved >= a.move vs previous tick
    react_new_level, react_sweep = [], []
    reacted_level, reacted_sweep = -1, -1  # index of the last signal already answered
    # per (ticker, side, price): rx_ms when the level was created as a new best
    fresh: dict[tuple, float] = {}
    join_gap = []
    last_trade_ts = {}
    for rec in iter_records(a.data_dir, a.day):
        raw = rec.raw
        t = raw.get("type")
        rx_ms = rec.rx_ns / 1e6
        if t == "_local":
            if raw.get("event") in ("connect", "disconnect"):
                stale_all = True
                for b in books.values():
                    b.stale = True
            continue
        msg = raw.get("msg") or {}
        if t in ("cfbenchmarks_value_5hz", "cfbenchmarks_value"):
            if msg.get("index_id") != a.index:
                continue
            if t == "cfbenchmarks_value":
                continue  # only the 5hz stream for timing
            tick = json.loads(msg["data"])
            lat_idx_time.append(rx_ms - tick["time"])
            lat_idx_kalshi.append(rx_ms - msg["received_at"])
            v = float(tick["value"])
            if idx_val and abs(v - idx_val[-1]) >= a.move:
                sig_rx.append(rx_ms)
            idx_rx.append(rx_ms)
            idx_val.append(v)
            continue
        tk = msg.get("market_ticker", "")
        if not tk.startswith(a.series + "-"):
            continue
        b = books[tk]
        if t == "orderbook_snapshot":
            b.snapshot(msg)
            continue
        if t == "trade":
            lat_trade.append(rx_ms - msg["ts_ms"])
            if sig_rx and reacted_sweep < len(sig_rx) - 1:
                dt = rx_ms - sig_rx[-1]
                if dt < 5000:
                    react_sweep.append(dt)
                reacted_sweep = len(sig_rx) - 1
            continue
        if t != "orderbook_delta" or b.stale:
            continue
        lat_delta.append(rx_ms - msg["ts_ms"])
        side, price, d = msg["side"], parse_price(msg["price_dollars"]), parse_qty(msg["delta_fp"])
        best_before = b.best(side)
        try:
            before = b.delta(side, price, d)
        except ValueError:
            b.stale = True
            continue
        if d > 0 and before == 0 and price > best_before:
            # a new best level was created by this order
            fresh[(tk, side, price)] = rx_ms
            if sig_rx and reacted_level < len(sig_rx) - 1:
                dt = rx_ms - sig_rx[-1]
                if dt < 5000:
                    react_new_level.append(dt)
                reacted_level = len(sig_rx) - 1
        elif d > 0 and (tk, side, price) in fresh:
            join_gap.append(rx_ms - fresh.pop((tk, side, price)))
        elif d < 0 and (tk, side, price) in fresh and b.side(side).get(price, 0) == 0:
            fresh.pop((tk, side, price), None)  # level gone before anyone joined

    print(f"# Latency regime, {a.series}, {a.day}\n")
    print("## 1. Transport latency (ms): our receive time minus exchange timestamp")
    print(f"- orderbook_delta rx - ts_ms:   {pct(lat_delta)}")
    print(f"- trade rx - ts_ms:             {pct(lat_trade)}")
    print(f"- {a.index} 5hz rx - tick time:      {pct(lat_idx_time)}")
    print(f"- {a.index} 5hz rx - kalshi received_at: {pct(lat_idx_kalshi)}")
    print(f"\n## 2. Reaction to {a.index} moves >= ${a.move:g} between ticks ({len(sig_rx):,} signals)")
    print("time from the index tick reaching us to ...")
    print(f"- first order at a NEW best price:  {pct(react_new_level)}")
    print(f"- first taker sweep:                {pct(react_sweep)}")
    print("\n## 3. Queue formation: new best level -> second order joins it (ms)")
    print(f"- {pct(join_gap, (10, 25, 50, 75, 90))}")
    print(f"- levels that got a joiner: {len(join_gap):,}; within 10ms: {sum(g <= 10 for g in join_gap)/len(join_gap)*100:.0f}%, within 1ms: {sum(g <= 1 for g in join_gap)/len(join_gap)*100:.0f}%")


if __name__ == "__main__":
    main()
