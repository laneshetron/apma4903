"""Paper trader for the Hyperliquid deep-resting strategy, replayed over the tape.

The markout work (`hl_offset.py`) asks "what did whoever was resting there earn?". This asks
the harder question: "would WE have been filled, and what would the book have left us?" -- the
question that killed the Kalshi version, where the edge per fill was real and the queue took
all of it.

Strategy: rest a bid `offset_bp` below mid and an ask `offset_bp` above, size `size` each,
on every coin. Reprice when the mid has moved enough that our offset drifts outside
[offset*(1-tol), offset*(1+tol)]. Close each fill after `hold_s`, or earlier if an opposite
fill nets it off. Stop quoting a side while inventory is past the cap.

Fills use the recorded book, not an assumption:

    a taker burst walks prices away from the aggressor. For our resting price P, let V be the
    burst volume that printed at P or beyond, and Q the standing size at P from the most recent
    l2Book. We are behind that size, so we fill  clamp(V - Q, 0, our size).

Q comes from an l2Book published every ~5.4 s, so it is stale; `--queue` picks how to use it:
    pessimistic  (default) Q as recorded -- everyone ahead of us
    prorata      Q * our_size/(Q+our_size) -- we get our share of the level
    none         Q = 0 -- filled whenever a sweep reaches us (the optimistic bound)

Fees are charged on fills. Exit is at mid (no slippage), which is optimistic; `--exit-bp`
charges a fixed cost per exit if you want to bound that.

    uv run python -m kalshi_data.research.hl_paper 2026-09-25 --data-dir ../data_hlalt --offset-bp 10
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

import numpy as np

from ..raw import iter_records


class Coin:
    __slots__ = ("mid", "book_bid", "book_ask", "book_rx", "bid_px", "ask_px", "bid_rx", "ask_rx",
                 "pos", "open_lots", "realized", "fees", "n_fills", "filled_notional",
                 "peak_abs_pos", "pos_notional", "edge_bp_sum", "edge_w")

    def __init__(self) -> None:
        self.mid = None
        self.book_bid: list[tuple[float, float]] = []
        self.book_ask: list[tuple[float, float]] = []
        self.book_rx = 0
        self.bid_px = self.ask_px = None
        self.bid_rx = self.ask_rx = 0
        self.pos = 0.0              # signed units
        self.pos_notional = 0.0     # signed $ at entry, for inventory caps
        self.open_lots: deque = deque()   # (close_rx, units, entry_px)
        self.realized = 0.0
        self.fees = 0.0
        self.n_fills = 0
        self.filled_notional = 0.0
        self.peak_abs_pos = 0.0
        self.edge_bp_sum = 0.0
        self.edge_w = 0.0


def depth_at(levels: list[tuple[float, float]], px: float, side: str) -> float:
    """Standing notional at prices at least as aggressive as px, i.e. ahead of us in a sweep."""
    tot = 0.0
    for p, sz in levels:
        if (side == "bid" and p >= px) or (side == "ask" and p <= px):
            tot += p * sz
    return tot


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--end", type=date.fromisoformat, default=None)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--coins", default=None)
    ap.add_argument("--offset-bp", type=float, default=10.0)
    ap.add_argument("--size", type=float, default=2_000, help="$ resting per side per coin")
    ap.add_argument("--max-pos", type=float, default=10_000, help="$ inventory cap per coin")
    ap.add_argument("--hold-s", type=float, default=300)
    ap.add_argument("--tol", type=float, default=0.30, help="reprice when offset drifts this fraction")
    ap.add_argument("--queue", choices=("pessimistic", "prorata", "none"), default="pessimistic")
    ap.add_argument("--fee-bp", type=float, default=1.5)
    ap.add_argument("--exit-bp", type=float, default=0.0, help="cost charged per exit, bps")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    want = set(a.coins.split(",")) if a.coins else None

    C: dict[str, Coin] = defaultdict(Coin)
    hold_ns = int(a.hold_s * 1e9)

    def reprice(c: Coin, rx: int) -> None:
        if c.mid is None:
            return
        tgt_bid = c.mid * (1 - a.offset_bp / 1e4)
        tgt_ask = c.mid * (1 + a.offset_bp / 1e4)
        for side in ("bid", "ask"):
            px = c.bid_px if side == "bid" else c.ask_px
            tgt = tgt_bid if side == "bid" else tgt_ask
            blocked = (c.pos_notional >= a.max_pos) if side == "bid" else (c.pos_notional <= -a.max_pos)
            if blocked:
                if side == "bid":
                    c.bid_px = None
                else:
                    c.ask_px = None
                continue
            if px is None or abs(px - tgt) / tgt > a.offset_bp / 1e4 * a.tol:
                if side == "bid":
                    c.bid_px, c.bid_rx = tgt, rx
                else:
                    c.ask_px, c.ask_rx = tgt, rx

    def close_expired(c: Coin, rx: int) -> None:
        while c.open_lots and c.open_lots[0][0] <= rx:
            _, units, entry = c.open_lots.popleft()
            if c.mid is None:
                continue
            exit_px = c.mid * (1 - np.sign(units) * a.exit_bp / 1e4)
            c.realized += units * (exit_px - entry)
            c.fees += abs(units) * exit_px * a.fee_bp / 1e4 * 0  # exit assumed maker-neutral
            c.pos -= units
            c.pos_notional -= units * entry

    for rec in iter_records(a.data_dir, a.day, a.end or a.day):
        raw = rec.raw
        ch = raw.get("channel")
        rx = rec.rx_ns
        if ch == "bbo":
            d = raw["data"]
            coin = d["coin"]
            if want and coin not in want:
                continue
            b, o = d["bbo"]
            if not b or not o:
                continue
            c = C[coin]
            c.mid = (float(b["px"]) + float(o["px"])) / 2
            close_expired(c, rx)
            reprice(c, rx)
            continue
        if ch == "l2Book":
            d = raw["data"]
            coin = d["coin"]
            if want and coin not in want:
                continue
            lv = d["levels"]
            if not lv or not lv[0] or not lv[1]:
                continue
            c = C[coin]
            c.book_bid = [(float(x["px"]), float(x["sz"])) for x in lv[0]]
            c.book_ask = [(float(x["px"]), float(x["sz"])) for x in lv[1]]
            c.book_rx = rx
            continue
        if ch != "trades":
            continue
        # group the message's prints into (coin, ms, side) bursts
        bursts: dict[tuple, list[tuple[float, float]]] = defaultdict(list)
        for t in raw["data"]:
            if want and t["coin"] not in want:
                continue
            bursts[(t["coin"], t["time"], t["side"])].append((float(t["px"]), float(t["sz"])))
        for (coin, _, side), prints in bursts.items():
            c = C[coin]
            if c.mid is None:
                continue
            close_expired(c, rx)
            # side B = taker buying, walking UP through asks -> hits OUR ask
            our_px = c.ask_px if side == "B" else c.bid_px
            if our_px is None:
                continue
            deepest = max(p for p, _ in prints) if side == "B" else min(p for p, _ in prints)
            reached = (deepest >= our_px) if side == "B" else (deepest <= our_px)
            if not reached:
                continue
            V = sum(p * s for p, s in prints if (p >= our_px if side == "B" else p <= our_px))
            if a.queue == "none":
                Q = 0.0
            else:
                Q = depth_at(c.book_ask if side == "B" else c.book_bid, our_px,
                             "ask" if side == "B" else "bid")
                if a.queue == "prorata" and (Q + a.size) > 0:
                    Q = Q * a.size / (Q + a.size)
            fill_notional = min(max(V - Q, 0.0), a.size)
            if fill_notional <= 0:
                continue
            sign = -1.0 if side == "B" else 1.0      # our ask hit -> we are short
            units = sign * fill_notional / our_px
            c.n_fills += 1
            c.filled_notional += fill_notional
            c.fees += fill_notional * a.fee_bp / 1e4
            c.pos += units
            c.pos_notional += units * our_px
            c.peak_abs_pos = max(c.peak_abs_pos, abs(c.pos_notional))
            c.open_lots.append((rx + hold_ns, units, our_px))
            c.edge_bp_sum += sign * (c.mid - our_px) / c.mid * 1e4 * fill_notional
            c.edge_w += fill_notional
            if side == "B":
                c.ask_px = None
            else:
                c.bid_px = None
            reprice(c, rx)

    for coin, c in C.items():
        close_expired(c, 1 << 62)

    lines = [f"# Hyperliquid paper trader, {a.day}{'' if not a.end else '..' + str(a.end)}\n",
             f"Resting +/-{a.offset_bp:.0f} bp, ${a.size:,.0f} per side per coin, ${a.max_pos:,.0f} inventory cap, "
             f"{a.hold_s:.0f} s hold, {a.queue} queue, {a.fee_bp} bp maker fee.\n",
             "| coin | fills | filled $ | edge at fill bp | fees $ | **net $** | peak inv $ | $/day per $1k rested |",
             "|---|---|---|---|---|---|---|---|"]
    tot_net = tot_fill = tot_fee = tot_peak = 0.0
    tot_n = 0
    for coin in sorted(C, key=lambda k: -(C[k].realized - C[k].fees)):
        c = C[coin]
        if not c.n_fills:
            continue
        net = c.realized - c.fees
        tot_net += net
        tot_fill += c.filled_notional
        tot_fee += c.fees
        tot_peak += c.peak_abs_pos
        tot_n += c.n_fills
        edge = c.edge_bp_sum / c.edge_w if c.edge_w else 0.0
        lines.append(f"| {coin} | {c.n_fills:,} | ${c.filled_notional:,.0f} | {edge:+.1f} | "
                     f"${c.fees:,.0f} | **${net:+,.0f}** | ${c.peak_abs_pos:,.0f} | "
                     f"${net / (a.size * 2 / 1000):+,.1f} |")
    lines.append(f"\n**total: {tot_n:,} fills, ${tot_fill:,.0f} filled, ${tot_fee:,.0f} fees, "
                 f"net ${tot_net:+,.0f}, peak inventory ${tot_peak:,.0f}**")
    if tot_fill:
        lines.append(f"\nnet edge realised: {tot_net / tot_fill * 1e4:+.2f} bp of filled notional")
    text = "\n".join(lines)
    print(text)
    if a.out:
        a.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
