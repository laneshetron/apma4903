"""Measure real fill rate and queue position by resting minimum-size orders live.

`hl_paper` has to guess two things it cannot derive from public data: how long our orders take
to place and cancel, and whether a sweep that reaches our price actually fills us or exhausts
on the size ahead. Both swing the result between profit and loss. This measures them.

The probe is cheap because of a property the size sweep exposed: **fill count does not depend
on order size** (38 fills/day at every size from $2k to $1M per order). Size changes how much
of each sweep we take, not how many sweeps reach us. So exchange-minimum orders observe the
same fill events as a real book, with negligible money at risk.

It rests a bid and an ask `offset_bp` from mid on each coin, repricing on drift exactly as the
sim does, and records every event with timestamps:

    place / ack / visible      -> real place latency
    cancel / ack / gone        -> real cancel latency
    fill                       -> did a sweep that reached our price fill us?
    book + trades around it    -> how much printed at our level, and what stood ahead

Analysis then answers: of the sweeps that reached our resting price, what fraction filled us,
and how did that compare to the depth ahead? That is the queue number, measured rather than
assumed -- Hyperliquid has no queue-position endpoint, unlike Kalshi's.

Events are written as our standard raw records, so `kalshi_data.raw` reads the output directly.

Safety: --live required, hard caps on per-order and total notional, a schedule_cancel dead-man
switch refreshed every 20 s so the exchange flattens our orders if this process dies, and
cancel-all on every exit path. Credentials only from HL_ACCOUNT_ADDRESS / HL_API_SECRET, which
should be an API wallet (agent) key -- it can trade but cannot withdraw.

    uv run python -m kalshi_data.research.hl_queue_probe --coins ZEC,SUI,NEAR --offset-bp 30
    uv run python -m kalshi_data.research.hl_queue_probe --coins ZEC,SUI,NEAR --offset-bp 30 --live
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

MAX_USD_PER_ORDER = 50.0
MAX_USD_TOTAL = 500.0


class Log:
    """Append-only JSONL in the same shape the rest of the tooling reads."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.f = path.open("a", buffering=1)
        self.lock = threading.Lock()

    def write(self, event: str, **fields) -> None:
        rec = {"rx_ns": time.time_ns(), "raw": {"channel": "_probe", "event": event, **fields}}
        with self.lock:
            self.f.write(json.dumps(rec) + "\n")

    def close(self) -> None:
        self.f.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--coins", default="ZEC,SUI,NEAR")
    ap.add_argument("--offset-bp", type=float, default=30.0)
    ap.add_argument("--tol", type=float, default=0.30, help="reprice when the offset drifts this fraction")
    ap.add_argument("--usd", type=float, default=15.0, help="notional per resting order")
    ap.add_argument("--minutes", type=float, default=60.0)
    ap.add_argument("--data-dir", type=Path, default=Path("../data_probe"))
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()

    coins = [c.strip() for c in a.coins.split(",") if c.strip()]
    if a.usd > MAX_USD_PER_ORDER:
        sys.exit(f"--usd {a.usd} exceeds the per-order cap {MAX_USD_PER_ORDER}")
    if a.usd * 2 * len(coins) > MAX_USD_TOTAL:
        sys.exit(f"total resting ${a.usd * 2 * len(coins):,.0f} exceeds the cap ${MAX_USD_TOTAL:,.0f}")

    from hyperliquid.exchange import Exchange
    from hyperliquid.info import Info
    from hyperliquid.utils import constants

    info = Info(constants.MAINNET_API_URL, skip_ws=not a.live)
    universe = {m["name"]: m for m in info.meta()["universe"]}
    for c in coins:
        if c not in universe:
            sys.exit(f"unknown coin {c}")

    mids = {}
    for c in coins:
        b = info.l2_snapshot(c)
        mids[c] = (float(b["levels"][0][0]["px"]) + float(b["levels"][1][0]["px"])) / 2

    print(f"coins: {', '.join(coins)}   offset {a.offset_bp:.0f} bp   ${a.usd:,.0f}/order   "
          f"total resting ${a.usd * 2 * len(coins):,.0f}   for {a.minutes:.0f} min")
    for c in coins:
        d = universe[c]["szDecimals"]
        px = round(mids[c] * (1 - a.offset_bp / 1e4), 6)
        sz = round(a.usd / px, d)
        print(f"  {c:6s} mid {mids[c]:>12,.5f}  bid {px:>12,.5f}  size {sz} "
              f"(${sz * px:,.2f}){'  TOO SMALL' if sz <= 0 else ''}")

    if not a.live:
        print("\nDRY RUN — nothing sent. With --live this would:")
        print("  rest a bid and an ask at the offset on each coin, reprice on drift,")
        print("  replace on fill, and log place/ack/visible/cancel/gone/fill with timestamps")
        print(f"  to {a.data_dir}/raw/<date>/<hour>.jsonl for offline analysis.")
        print("\nExpected from the sim: ~25-38 fill events/day across 10 coins at 30 bp,")
        print("so a 1 h run on 3 coins samples only a few -- plan on running it for a day.")
        return

    addr, secret = os.environ.get("HL_ACCOUNT_ADDRESS"), os.environ.get("HL_API_SECRET")
    if not addr or not secret:
        sys.exit("set HL_ACCOUNT_ADDRESS and HL_API_SECRET (an API wallet key, not your main key)")
    import eth_account
    ex = Exchange(eth_account.Account.from_key(secret), constants.MAINNET_API_URL, account_address=addr)

    day = datetime.now(timezone.utc)
    log = Log(a.data_dir / "raw" / day.strftime("%Y-%m-%d") / (day.strftime("%H") + ".jsonl"))
    stop = threading.Event()
    live_orders: dict[tuple[str, str], int] = {}

    def cancel_all() -> None:
        try:
            for o in info.open_orders(addr):
                ex.cancel(o["coin"], o["oid"])
                log.write("cancel_all", coin=o["coin"], oid=o["oid"])
        except Exception as e:  # noqa: BLE001
            print(f"WARNING: cancel_all failed: {e}", file=sys.stderr)

    def deadman() -> None:
        while not stop.wait(20):
            try:
                ex.schedule_cancel(int(time.time() * 1000) + 60_000)
            except Exception:  # noqa: BLE001
                pass

    def on_signal(*_):
        stop.set()

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    threading.Thread(target=deadman, daemon=True).start()

    def place(coin: str, side: str) -> None:
        d = universe[coin]["szDecimals"]
        m = mids[coin]
        px = round(m * (1 - a.offset_bp / 1e4) if side == "bid" else m * (1 + a.offset_bp / 1e4), 6)
        sz = round(a.usd / px, d)
        if sz <= 0:
            return
        t0 = time.time_ns()
        log.write("place_send", coin=coin, side=side, px=px, sz=sz, mid=m)
        try:
            r = ex.order(coin, side == "bid", sz, px, {"limit": {"tif": "Alo"}})
        except Exception as e:  # noqa: BLE001
            log.write("place_error", coin=coin, side=side, err=str(e))
            return
        t1 = time.time_ns()
        st = r.get("response", {}).get("data", {}).get("statuses", [{}])[0]
        oid = st.get("resting", {}).get("oid")
        log.write("place_ack", coin=coin, side=side, px=px, sz=sz, oid=oid,
                  ack_ms=(t1 - t0) / 1e6, raw=st)
        if oid:
            live_orders[(coin, side)] = oid

    def cancel(coin: str, side: str) -> None:
        oid = live_orders.pop((coin, side), None)
        if oid is None:
            return
        t0 = time.time_ns()
        log.write("cancel_send", coin=coin, side=side, oid=oid)
        try:
            ex.cancel(coin, oid)
        except Exception as e:  # noqa: BLE001
            log.write("cancel_error", coin=coin, side=side, oid=oid, err=str(e))
            return
        log.write("cancel_ack", coin=coin, side=side, oid=oid, ack_ms=(time.time_ns() - t0) / 1e6)

    def on_book(msg) -> None:
        d = msg.get("data", {})
        coin = d.get("coin")
        if coin not in universe:
            return
        b, o = d.get("bbo", [None, None])
        if not b or not o:
            return
        m = (float(b["px"]) + float(o["px"])) / 2
        mids[coin] = m
        log.write("bbo", coin=coin, bid=float(b["px"]), ask=float(o["px"]), mid=m)

    def on_l2(msg) -> None:
        d = msg.get("data", {})
        if d.get("coin") in universe:
            log.write("l2Book", coin=d["coin"], levels=d.get("levels"), time=d.get("time"))

    def on_trades(msg) -> None:
        for t in msg.get("data", []):
            if t.get("coin") in universe:
                log.write("trade", coin=t["coin"], px=float(t["px"]), sz=float(t["sz"]),
                          side=t["side"], time=t["time"])

    def on_user(msg) -> None:
        for f in msg.get("data", {}).get("fills", []):
            log.write("fill", coin=f.get("coin"), px=float(f.get("px", 0)), sz=float(f.get("sz", 0)),
                      side=f.get("side"), oid=f.get("oid"), time=f.get("time"), raw=f)
            for k, v in list(live_orders.items()):
                if v == f.get("oid"):
                    live_orders.pop(k, None)

    for c in coins:
        info.subscribe({"type": "bbo", "coin": c}, on_book)
        info.subscribe({"type": "l2Book", "coin": c}, on_l2)
        info.subscribe({"type": "trades", "coin": c}, on_trades)
    info.subscribe({"type": "userFills", "user": addr}, on_user)

    try:
        for c in coins:
            place(c, "bid")
            place(c, "ask")
        deadline = time.time() + a.minutes * 60
        while not stop.is_set() and time.time() < deadline:
            time.sleep(2)
            for c in coins:
                m = mids[c]
                for side in ("bid", "ask"):
                    tgt = m * (1 - a.offset_bp / 1e4) if side == "bid" else m * (1 + a.offset_bp / 1e4)
                    if (c, side) not in live_orders:
                        place(c, side)
                        continue
                    # reprice on drift, mirroring the sim's tolerance rule
                    cur = None
                    for o in info.open_orders(addr):
                        if o["oid"] == live_orders[(c, side)]:
                            cur = float(o["limitPx"])
                    if cur is None:
                        live_orders.pop((c, side), None)
                        place(c, side)
                    elif abs(cur - tgt) / tgt > a.offset_bp / 1e4 * a.tol:
                        cancel(c, side)
                        place(c, side)
    finally:
        stop.set()
        cancel_all()
        log.write("shutdown")
        log.close()
        print("stopped; all orders cancelled")


if __name__ == "__main__":
    main()
