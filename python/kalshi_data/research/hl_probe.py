"""Measure real place/cancel latency and queue position against live Hyperliquid.

The paper sim swings from +$121 to -$150 on a single day depending on the place/cancel latency
we assume, and we have no measurement of it. This probes the live exchange for that number.

Two modes:

  latency   Place a post-only order far from mid (it cannot fill, cannot cross), time the ack
            and the moment it shows up in our own l2Book feed, cancel, time that too. Repeat.
            Risk is structurally nil: the order is --far percent away and ALO, so it can never
            trade, and size is the exchange minimum.

  queue     Rest a minimum-size order at the real strategy offset and record, for every sweep
            that reaches our price, the book depth at our level beforehand and whether we
            filled. That brackets our queue position: filled => we were inside the volume that
            printed at our level; not filled => we were behind it. This one takes real (tiny)
            risk, because the order is at a price that can actually trade.

Safety, because this sends live orders:
  * --live is required; without it everything runs and prints but nothing is sent.
  * order size is capped at --max-usd (default $15) and the venue minimum is used.
  * latency mode refuses to quote closer than --far percent from mid.
  * a dead-man switch (schedule_cancel) is armed and refreshed, so if this process dies the
    exchange cancels our orders without us.
  * every exit path, including exceptions and SIGINT, cancels all open orders.

Credentials come from the environment, never arguments:
    HL_ACCOUNT_ADDRESS   the main account (0x...)
    HL_API_SECRET        an API WALLET (agent) private key -- create one in the HL UI under
                         More > API. An agent can trade but cannot withdraw, which is the only
                         key that should ever be on a research box.

    uv run python -m kalshi_data.research.hl_probe latency --coin ZEC --n 50
    uv run python -m kalshi_data.research.hl_probe latency --coin ZEC --n 50 --live
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import statistics
import sys
import threading
import time
from pathlib import Path

MAX_USD_HARD = 100.0          # refuse to build an order bigger than this under any flag
MIN_FAR_PCT = 5.0             # latency mode: never rest closer than this to mid


def env_creds() -> tuple[str, str]:
    addr, secret = os.environ.get("HL_ACCOUNT_ADDRESS"), os.environ.get("HL_API_SECRET")
    if not addr or not secret:
        sys.exit("set HL_ACCOUNT_ADDRESS and HL_API_SECRET (an API wallet key, not your main key)")
    return addr, secret


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("latency", "queue"))
    ap.add_argument("--coin", default="ZEC")
    ap.add_argument("--n", type=int, default=30, help="round trips to time")
    ap.add_argument("--far", type=float, default=20.0, help="latency mode: percent below mid to rest")
    ap.add_argument("--offset-bp", type=float, default=30.0, help="queue mode: offset from mid")
    ap.add_argument("--max-usd", type=float, default=15.0)
    ap.add_argument("--gap-s", type=float, default=2.0, help="pause between round trips")
    ap.add_argument("--live", action="store_true", help="actually send orders (otherwise dry run)")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    if a.max_usd > MAX_USD_HARD:
        sys.exit(f"--max-usd {a.max_usd} exceeds the hard cap {MAX_USD_HARD}")
    if a.mode == "latency" and a.far < MIN_FAR_PCT:
        sys.exit(f"--far {a.far}% is too close to mid for a no-fill probe (min {MIN_FAR_PCT}%)")

    from hyperliquid.exchange import Exchange
    from hyperliquid.info import Info
    from hyperliquid.utils import constants

    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    meta = info.meta()
    universe = {m["name"]: m for m in meta["universe"]}
    if a.coin not in universe:
        sys.exit(f"unknown coin {a.coin}")
    sz_decimals = universe[a.coin]["szDecimals"]

    book = info.l2_snapshot(a.coin)
    bid = float(book["levels"][0][0]["px"])
    ask = float(book["levels"][1][0]["px"])
    mid = (bid + ask) / 2

    if a.mode == "latency":
        px = round(mid * (1 - a.far / 100), 6)
    else:
        px = round(mid * (1 - a.offset_bp / 1e4), 6)
    sz = round(a.max_usd / px, sz_decimals)
    if sz <= 0:
        sys.exit(f"${a.max_usd} is below one tick of size for {a.coin} (szDecimals={sz_decimals})")
    notional = sz * px

    print(f"{a.coin}: mid {mid:,.6f}  probe bid {px:,.6f} ({(mid-px)/mid*100:.2f}% below mid)  "
          f"size {sz} = ${notional:,.2f}")
    if not a.live:
        print("\nDRY RUN — nothing will be sent. Re-run with --live once credentials are set.")
        print("Would, per round trip: place ALO bid, poll openOrders until it appears, cancel, "
              "poll until it is gone; recording wall-clock for each leg.")
        return

    addr, secret = env_creds()
    import eth_account
    wallet = eth_account.Account.from_key(secret)
    ex = Exchange(wallet, constants.MAINNET_API_URL, account_address=addr)

    stop = threading.Event()

    def cancel_all() -> None:
        try:
            for o in info.open_orders(addr):
                ex.cancel(o["coin"], o["oid"])
            print("cancelled all open orders")
        except Exception as e:  # noqa: BLE001
            print(f"WARNING: cancel_all failed: {e}", file=sys.stderr)

    def deadman() -> None:
        # exchange-side cancel-all if we stop refreshing; survives a crash of this process
        while not stop.wait(20):
            try:
                ex.schedule_cancel(int(time.time() * 1000) + 60_000)
            except Exception:  # noqa: BLE001
                pass

    def on_signal(*_):
        stop.set()
        cancel_all()
        sys.exit(1)

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    threading.Thread(target=deadman, daemon=True).start()

    place_ack, place_seen, cancel_ack, cancel_seen = [], [], [], []
    try:
        for i in range(a.n):
            t0 = time.perf_counter()
            r = ex.order(a.coin, True, sz, px, {"limit": {"tif": "Alo"}})
            t1 = time.perf_counter()
            place_ack.append((t1 - t0) * 1000)
            st = r.get("response", {}).get("data", {}).get("statuses", [{}])[0]
            oid = st.get("resting", {}).get("oid")
            if oid is None:
                print(f"  [{i}] no resting oid: {json.dumps(r)[:200]}")
                continue
            while True:                                   # when does it become visible to us?
                if any(o["oid"] == oid for o in info.open_orders(addr)):
                    break
                if time.perf_counter() - t0 > 10:
                    break
            place_seen.append((time.perf_counter() - t0) * 1000)

            t2 = time.perf_counter()
            ex.cancel(a.coin, oid)
            t3 = time.perf_counter()
            cancel_ack.append((t3 - t2) * 1000)
            while True:
                if not any(o["oid"] == oid for o in info.open_orders(addr)):
                    break
                if time.perf_counter() - t2 > 10:
                    break
            cancel_seen.append((time.perf_counter() - t2) * 1000)
            print(f"  [{i}] place ack {place_ack[-1]:6.1f} ms  visible {place_seen[-1]:6.1f} ms  "
                  f"cancel ack {cancel_ack[-1]:6.1f} ms  gone {cancel_seen[-1]:6.1f} ms")
            time.sleep(a.gap_s)
    finally:
        stop.set()
        cancel_all()

    def summarize(name, v):
        if not v:
            return f"| {name} | — | — | — | — |"
        return (f"| {name} | {statistics.median(v):.1f} | {min(v):.1f} | "
                f"{statistics.quantiles(v, n=20)[-1] if len(v) > 3 else max(v):.1f} | {len(v)} |")

    lines = [f"# Hyperliquid live latency, {a.coin}, {a.n} round trips\n",
             "| leg | median ms | min ms | p95 ms | n |", "|---|---|---|---|---|",
             summarize("place -> ack", place_ack),
             summarize("place -> visible to us", place_seen),
             summarize("cancel -> ack", cancel_ack),
             summarize("cancel -> gone", cancel_seen)]
    text = "\n".join(lines)
    print("\n" + text)
    if a.out:
        a.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
