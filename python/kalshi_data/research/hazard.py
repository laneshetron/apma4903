"""Measurement pass for the DP hold/cancel policy: fill hazards by book state,
adverse-episode durations, and queue advancement, from the book itself.

    uv run python -m kalshi_data.research.hazard 2026-09-14

States are defined from a RESTING order's side s:
  imb_s   = (depth at the other side's touch - depth at our touch) / (sum)   (>= 0.33: we are the thin side)
  micro_s = Coinbase microprice pressure against our order ($)               (>= 0.5: spot leaning against us)
Outputs research/hazard_<day>.json with
  time_in_state[state]            seconds (summed over markets and sides)
  sweeps[state][q]                count of sweeps hitting a side in that state with size > q
  episode_mean_s[state]           mean episode duration
  advance_per_s                   mean contracts/s by which the queue ahead of the touch shrinks
"""

from __future__ import annotations

import argparse
import heapq
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from ..book import parse_price, parse_qty
from ..raw import iter_records
from ..spot import SpotQuote, iter_spot
from .markouts import FastBook, close_time

Q_EDGES = [0, 50, 100, 200, 500, 1000, 2000, 5000]
ONE = 10_000


def imb_bucket(x: float) -> str:
    return "thin" if x >= 0.33 else ("thick" if x <= -0.33 else "balanced")


def micro_bucket(x: float | None) -> str:
    if x is None:
        return "flat"
    return "against" if x >= 0.5 else ("for" if x <= -0.5 else "flat")


def state_key(imb: float, micro: float | None) -> str:
    return f"{imb_bucket(imb)}|{micro_bucket(micro)}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, default=Path("../data"))
    ap.add_argument("--series", default="KXBTC15M")
    ap.add_argument("--out-dir", type=Path, default=Path("../research"))
    a = ap.parse_args()

    books: dict[str, FastBook] = {}
    closes: dict[str, float] = {}
    # per (ticker, side): current state, since when
    cur: dict[tuple, tuple[str, int]] = {}
    time_in: dict[str, float] = defaultdict(float)
    episodes: dict[str, list[float]] = defaultdict(list)
    sweeps: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    open_sweep: dict[tuple, list] = {}   # (ticker, side) -> [ts_ms, qty, state]
    # queue advancement: track touch depth decreases not due to our own orders
    adv_qty = 0.0
    cb_bid = cb_ask = cb_bs = cb_as = None

    def micro_for(side: str) -> float | None:
        if cb_bid is None or cb_bs is None or cb_bs + cb_as <= 0:
            return None
        mid = (cb_bid + cb_ask) / 2
        m = (cb_bid * cb_as + cb_ask * cb_bs) / (cb_bs + cb_as) - mid
        return -m if side == "yes" else m   # pressure against a YES bid is spot going down

    def update_state(tk: str, rx: int) -> None:
        b = books[tk]
        if b.stale or b.best_yes < 0 or b.best_no < 0:
            return
        dy, dn = b.yes.get(b.best_yes, 0), b.no.get(b.best_no, 0)
        if dy + dn == 0:
            return
        for side, ours, other in (("yes", dy, dn), ("no", dn, dy)):
            k = state_key((other - ours) / (other + ours), micro_for(side))
            prev = cur.get((tk, side))
            if prev is None:
                cur[(tk, side)] = (k, rx)
            elif prev[0] != k:
                dt = (rx - prev[1]) / 1e9
                time_in[prev[0]] += dt
                episodes[prev[0]].append(dt)
                cur[(tk, side)] = (k, rx)

    def close_sweep(key):
        sw = open_sweep.pop(key, None)
        if sw is None:
            return
        _, qty, st = sw
        for q in Q_EDGES:
            if qty > q * 100:
                sweeps[st][q] += 1

    def cb_events():
        for rec in iter_records(a.data_dir / "spot" / "coinbase", a.day):
            raw = rec.raw
            if raw.get("type") == "ticker" and raw.get("product_id") == "BTC-USD" and raw.get("best_bid_size"):
                yield ("cb", rec.rx_ns, float(raw["best_bid"]), float(raw["best_ask"]), float(raw["best_bid_size"]), float(raw["best_ask_size"]))

    n = 0
    for ev in heapq.merge(iter_records(a.data_dir, a.day), cb_events(), key=lambda e: e[1] if isinstance(e, tuple) else e.rx_ns):
        n += 1
        if n % 10_000_000 == 0:
            print(f"  {n/1e6:.0f}M", file=sys.stderr)
        if isinstance(ev, tuple):
            cb_bid, cb_ask, cb_bs, cb_as = ev[2], ev[3], ev[4], ev[5]
            continue
        raw = ev.raw
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
        rx = ev.rx_ns
        b = books.get(tk)
        if b is None:
            b = books[tk] = FastBook()
            closes[tk] = close_time(tk) or 0
        if t == "orderbook_snapshot":
            b.snapshot(msg)
            update_state(tk, rx)
            continue
        if t == "trade":
            side = "yes" if msg["taker_side"] == "no" else "no"
            key = (tk, side)
            sw = open_sweep.get(key)
            if sw is not None and sw[0] != msg["ts_ms"]:
                close_sweep(key)
                sw = None
            if sw is None:
                st = cur.get(key, ("balanced|flat", rx))[0]
                open_sweep[key] = [msg["ts_ms"], 0, st]
            open_sweep[key][1] += parse_qty(msg["count_fp"])
            continue
        if b.stale:
            continue
        side, price, d = msg["side"], parse_price(msg["price_dollars"]), parse_qty(msg["delta_fp"])
        # queue advancement at the touch: decreases of the best level's quantity
        best_before = b.best(side)
        try:
            before = b.delta(side, price, d)
        except ValueError:
            b.stale = True
            continue
        if price == best_before and d < 0:
            adv_qty += -d / 100   # contracts removed from the touch (trades and cancels)
        # sweeps whose deltas are followed by later deltas at other ts close out
        for key in list(open_sweep):
            if key[0] == tk and open_sweep[key][0] < msg.get("ts_ms", 0):
                close_sweep(key)
        update_state(tk, rx)

    for key in list(open_sweep):
        close_sweep(key)
    out = {
        "time_in_state_s": dict(time_in),
        "sweeps": {k: {str(q): v[q] for q in Q_EDGES} for k, v in sweeps.items()},
        "hazard_per_s": {k: {str(q): sweeps[k][q] / time_in[k] for q in Q_EDGES} for k in sweeps if time_in.get(k, 0) > 0},
        "episode_mean_s": {k: sum(v) / len(v) for k, v in episodes.items() if v},
        # per market-side: touch depletion over the time a side was observed (time_in sums both sides)
        "advance_per_s": adv_qty / sum(time_in.values()) if time_in else None,
    }
    p = a.out_dir / f"hazard_{a.day}.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"advance rate {out['advance_per_s']:.1f} contracts/s at the touch")
    print(f"{'state':18s} {'time %':>7s} {'ep mean s':>9s}  hazard/s for q> " + "  ".join(f"{q:>5d}" for q in Q_EDGES))
    tot = sum(time_in.values())
    for k in sorted(out["hazard_per_s"], key=lambda k: -time_in[k]):
        h = out["hazard_per_s"][k]
        print(f"{k:18s} {time_in[k]/tot*100:6.1f}% {out['episode_mean_s'].get(k, 0):9.2f}  " + "  ".join(f"{h[str(q)]:5.3f}" for q in Q_EDGES))


if __name__ == "__main__":
    main()
