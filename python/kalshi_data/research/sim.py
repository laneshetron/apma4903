"""Phase B step 4: queue-position-aware simulation of a touch quoter.

    uv run python -m kalshi_data.research.sim 2026-09-14 [--series KXBTC15M] [--venue coinbase]

Replays the day's books, trades and a spot mid (for the cancel-on-signal
rule) and runs several quoter configurations in one pass. See the class
docstrings for the model; the summary at the end is the deliverable.

Model limits: no market impact (our orders do not change anyone else's
behaviour), fills are attributed from recorded trades against a queue model,
and inventory is marked at the mid when quoting stops rather than carried to
settlement.
"""

from __future__ import annotations

import argparse
import bisect
import heapq
import json
import statistics as st
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import math

import numpy as np
import polars as pl

from ..book import parse_price, parse_qty
from ..raw import iter_records
from ..spot import SpotQuote, SpotTrade, iter_spot
from .alpha import VENUES, SpotState, fetch_strikes
from .fair import SpotSeries, fair_value
from .markouts import FastBook, close_time

ONE = 10_000
TICK = 100          # 1c (used where a fixed reference is needed)


_AGE = ((0, 5), (5, 16), (16, 50), (50, 200), (200, 1000), (1000, float("inf")))


def _age_bucket(ms: float) -> str:
    for lo, hi in _AGE:
        if lo <= ms < hi:
            return f"{lo}-{'' if hi == float('inf') else int(hi)}ms"
    return "?"


TICK_GRID = "tapered_deci_cent"   # set per series by run(): tapered_deci_cent (15-minute crypto) | linear_cent (KXBTCD)


def tick_at(price: int) -> int:
    """Price grid: tapered_deci_cent = 0.1c steps below 10c and above 90c, 1c between; linear_cent = 1c everywhere."""
    if TICK_GRID == "linear_cent":
        return 100
    return 10 if price < 1_000 or price >= 9_000 else 100
QTY = 100           # 1 contract
TAKER_FEE = 0.07    # per contract: 0.07 * p * (1-p) dollars


@dataclass(slots=True)
class Params:
    name: str
    size: int = 100                 # contracts per side
    max_pos: int = 500              # contracts
    latency_ms: float = 2.0
    # optional split of latency_ms by action, in tape time (see MEASURED for the AWS calibration)
    place_latency_ms: float | None = None    # book event seen -> our order live at the engine
    cancel_latency_ms: float | None = None   # book event seen -> our cancel effective
    signal_latency_ms: float | None = None   # spot tick seen -> our cancel effective
    capital: float | None = None             # $ available per market: resting bids reserve price x qty, fills lock the collateral paid
    reduce_only_exempt: bool = False         # greeks cap / join gate apply only to orders that would increase |position|
    skew_at: float | None = None             # fraction of max_pos beyond which the reducing side improves a tick and the increasing side shrinks
    flatten_at_stop: bool = False            # at the endgame stop, cross the spread to close the position (taker fee) instead of carrying it to settlement
    flatten_above: int | None = None         # contracts: whenever |position| exceeds this, take the touch to bring it back to this (taker fee)
    size_skew: bool = False                  # A-S by size: increasing side quotes size*(1-|q|/max), reducing side size*(1+|q|/max)
    price_priority: bool = False             # a trade at a worse price for the taker fills our better-priced resting order first (multi-level sweeps)
    engine_lag_ms: float = 0.0               # tape time - engine time (AWS tape: ~6 ms); added to place/cancel latencies so they are in tape time
    min_level_age_ms: float | None = None    # don't JOIN a touch level younger than this (time since the level appeared)
    min_rest_ms: float | None = None         # don't reprice an order younger than this (cancels for disallow/signal still apply)
    reprice_ticks: int = 1                   # reprice only when the wanted price is at least this many ticks from the order's price
    offset_ticks: int = 0                    # rest this many ticks behind the touch (pre-positioning); disables improving
    signal_venues: tuple = ("coinbase",)     # venues whose 1s mid move can trigger cancel-on-signal
    stale_feed_ms: float | None = None       # pull quotes while the latest Coinbase message arrived this late (rx - exchange ts)
    stop_before_s: float = 120.0
    signal_move: float | None = None  # $ over 1s on the spot mid; None disables
    max_ttx_h: float | None = None          # only quote markets closing within this many hours (multi-market series)
    global_capital: bool = False            # capital is shared across all markets of the series (multi-market)
    wide_spread_ticks: float | None = None   # spread wider than this many ticks = information state: no improve (join only) ...
    wide_spread_pull: bool = False           # ... or no quoting at all while the spread is that wide
    post_jump_pause_s: float | None = None   # after the mid moves >= post_jump_c within 2 s, no quoting for this long
    post_jump_c: float = 5.0
    min_touch_age_ms: float | None = None   # only quote when our side's touch PRICE has been the best this long
    improve_only: bool = False        # quote only when the spread allows an improve (never join a touch)
    no_improve: bool = False          # never improve; join only
    veto_file: str | None = None      # parquet of (ticker, side, start_rx, end_rx): presence veto on side while rx in [start, end)
    signal_improve: bool = False      # on a spot move, post-only at the old ask on the side the move favours (first at the level it vacates)
    signal_hold_ms: float = 2000.0    # how long a signal improve is exempt from the off-market cancel
    signal_place_latency_ms: float | None = None  # spot tick seen -> our post-only live (tape time); default signal + (place - cancel)
    cooldown_ms: float = 1000.0
    queue: str = "prorata"          # prorata | pessimistic
    # adverse-selection filters
    alpha_thr: float | None = None    # $: don't rest a side when predicted 5s spot move is >= thr against it
    greeks_cap: float | None = None   # don't quote when a 1-sigma 10s spot move is worth >= cap (fraction of $1)
    min_depth: int | None = None      # contracts: don't JOIN a touch on our side thinner than this
    imb_thr: float | None = None      # don't rest when (other - ours)/(other + ours) at the touch >= thr
    cluster_ms: float | None = None   # after a level is emptied by trades, stay off that side this long
    keep_if_ahead_lt: int | None = None  # contracts: ignore filter vetoes for a live order this close to the front
    # value-function hold/cancel policy (needs an EdgeModel): cancel a live order when its
    # expected edge from (queue position, state) is below -edge_theta for at least edge_debounce_ms
    edge_theta: float | None = None
    edge_debounce_ms: float = 0.0
    join_theta: float | None = None   # only JOIN/PLACE when expected edge at the placement queue position >= -join_theta
    # fair value gap rules (cents): gap = fair - mid. Bid is overpriced when gap < -thr, ask when gap > +thr.
    fair_gap_thr: float | None = None       # presence rule: cancel/avoid the overpriced side
    fair_gap_join: float | None = None      # join-only rule: don't place on the overpriced side, hold existing orders
    vol_mult: float = 1.0                   # scale realized vol in the fair value model
    # delta-scaled repricing: cancel a side when fair value has moved against it by >= this many cents
    # since the order was placed (replaces the flat "$X spot move" cancel-on-signal rule)
    dfair_cancel_c: float | None = None
    fair_spot: str = "coinbase"             # spot series driving fair for the repricing rule: coinbase | brti
    dfair_window_s: float | None = None     # if set, compare fair now vs fair this many seconds ago instead of since placement
    kernel: str = "normal"                  # normal | mixture (fat-tailed)


@dataclass(slots=True)
class Order:
    side: str          # book side we rest on: "yes" (our YES bid) or "no" (our YES ask)
    price: int         # price on that side
    remaining: int     # qty units
    ahead: int | None  # queue ahead of us; None until activation
    active_from: int   # rx_ns when the order is live
    cancel_at: int | None = None  # rx_ns when a cancel lands
    improved: bool = False        # placed one tick inside the touch
    sig_until: int = 0            # signal improve: exempt from the off-market cancel until this rx_ns
    last_seen: int = 0            # rx_ns of the last probe update
    fair_at_place: float | None = None  # fair (cents) when placed, for delta-scaled repricing
    filled_any: bool = False
    unexplained: deque = field(default_factory=deque)  # (rx_ns, ts_ms, qty) negative deltas awaiting a trade


@dataclass(slots=True)
class MarketPnL:
    ticker: str
    fills: int = 0
    sweep_fills: int = 0   # fills received by price priority (a trade went through our level)
    bought: int = 0    # qty units
    sold: int = 0
    cash: float = 0.0  # dollars
    pos: int = 0       # qty units, + long YES
    max_abs_pos: int = 0
    mark_pnl: float | None = None     # dollars, inventory at mid
    flatten_cost: float = 0.0         # dollars, pessimistic unwind
    market_volume: int = 0
    buy_cost: float = 0.0   # dollars paid for buys
    sell_proceeds: float = 0.0
    no_paid: float = 0.0    # dollars paid for NO fills (a NO bid at p locks p per contract)
    flattened: float = 0.0  # contracts closed at the stop by taking the touch
    settle: float | None = None   # 1.0 / 0.0 once the market resolves (BRTI 60s average vs strike), None if unknown
    mid_at_stop: float | None = None

    def locked(self) -> float:
        """Collateral held against the NET position: Kalshi returns the collateral of offsetting pairs."""
        if self.pos > 0 and self.bought:
            return self.pos / QTY * (self.buy_cost / (self.bought / QTY))
        if self.pos < 0 and self.sold:
            return -self.pos / QTY * (self.no_paid / (self.sold / QTY))
        return 0.0
    spread_capture: float = 0.0   # dollars: sum over fills of (mid - price) * qty, signed
    inventory_pnl: float = 0.0    # dollars: sum over time of pos * d(mid)
    last_mid: float | None = None # cents
    pre_mid: float | None = None  # mid before the first delta of the current ts_ms (pre-sweep)
    last_ts: int = -1
    improved_fills: int = 0  # fills on a quote that improved the touch (alone at the front)
    stop_rx: int = 0         # rx_ns when quoting stopped (for train/test split)


class Quoter:
    """One strategy configuration, run against every market of the series."""

    def __init__(self, p: Params):
        self.p = p
        self.lat = int(((p.cancel_latency_ms if p.cancel_latency_ms is not None else p.latency_ms) + p.engine_lag_ms) * 1e6)
        self.lat_place = int(((p.place_latency_ms if p.place_latency_ms is not None else p.latency_ms) + p.engine_lag_ms) * 1e6)
        self.lat_signal = int((p.signal_latency_ms if p.signal_latency_ms is not None else p.latency_ms) * 1e6)
        sig_place = p.signal_place_latency_ms
        if sig_place is None:
            sig_place = (p.signal_latency_ms if p.signal_latency_ms is not None else p.latency_ms) + \
                        ((p.place_latency_ms or p.latency_ms) - (p.cancel_latency_ms or p.latency_ms))
        self.lat_sig_place = int(sig_place * 1e6)
        self.orders: dict[str, dict[str, Order]] = defaultdict(dict)   # ticker -> side -> Order
        self.pnl: dict[str, MarketPnL] = {}
        self.blocked: dict[str, dict[str, int]] = defaultdict(lambda: {"yes": 0, "no": 0})  # side -> rx_ns until which quoting is off
        self.stopped: set[str] = set()
        self.swept_until: dict[str, dict[str, int]] = defaultdict(lambda: {"yes": 0, "no": 0})
        self.vetoes: dict[str, int] = defaultdict(int)  # reason -> count of (side, requote) decisions blocked
        self.feed_lag_ms = 0.0   # delivery lag of the latest Coinbase message
        self.adverse_since: dict[str, dict[str, int]] = defaultdict(lambda: {"yes": -1, "no": -1})
        self.level_born: dict[str, dict[tuple, int]] = defaultdict(dict)   # ticker -> (side, price) -> rx_ns the level appeared
        self.veto: dict[tuple, tuple[list, list]] = {}   # (ticker, side) -> (starts, ends) sorted
        self._locked_cache: tuple = (None, 0.0)
        if p.veto_file:
            import polars as _pl
            for (tk, sd), g in _pl.read_parquet(p.veto_file).sort("start_rx").group_by(["ticker", "side"], maintain_order=True):
                self.veto[(tk, sd)] = (g["start_rx"].to_list(), g["end_rx"].to_list())

        self.probe_adv_qty = 0.0     # contracts by which live orders advanced
        self.probe_live_s = 0.0      # live-order seconds
        self.probe_ttf: list[float] = []      # seconds from activation to (first) fill
        self.probe_ahead_at_fill: list[float] = []
        self.probe_ahead_at_place: list[float] = []
        self.edge_blocked: dict[str, dict[str, bool]] = defaultdict(lambda: {"yes": False, "no": False})
        self.fair_hist: dict[str, deque] = defaultdict(deque)   # ticker -> (rx_ns, fair_c) for the window variant
        self.fill_mo: deque = deque()   # (deadline_ns, ticker, sign, price_cents, qty, horizon) for markouts of our fills
        self.fill_markouts: dict[int, list[tuple[float, int]]] = {10: [], 30: []}  # horizon -> (markout cents, qty)
        self.mid_hist: dict[str, deque] = defaultdict(deque)   # ticker -> (rx, mid) last 2 s, for post-jump pauses
        self.jump_until: dict[str, int] = defaultdict(int)
        self.fill_log: list | None = None   # (ticker, rx, side, price, qty, improved, sweep) when --fills-out is set
        self.fill_by: dict[tuple, list[float]] = {}   # (improve|join, sweep|partial, age-of-touch bucket, age-of-level bucket) -> [mo30*qty, qty]
        self.best_since: dict[str, dict[str, int]] = defaultdict(dict)   # ticker -> side -> rx the current best price became best
        self._last_best: dict[str, dict[str, int]] = defaultdict(dict)
        self.adverse_10s: float = 0.0   # dollars: mid move in the 10s after our fills, signed (negative = adverse)

    # ---- helpers -----------------------------------------------------------
    def _locked_all(self, exclude_tk: str, rx: int = 0) -> float:
        """Collateral held in every other market: net positions plus resting orders (recomputed at most once per 200 ms)."""
        key = (exclude_tk, rx // 200_000_000)
        if self._locked_cache[0] == key:
            return self._locked_cache[1]
        tot = 0.0
        for t, r in self.pnl.items():
            if t != exclude_tk and r.pos != 0:
                tot += r.locked()
        for t, od in self.orders.items():
            if t != exclude_tk:
                tot += sum(x.price / ONE * x.remaining / QTY for x in od.values() if x.cancel_at is None)
        self._locked_cache = (key, tot)
        return tot

    def _vetoed(self, tk: str, s: str, rx: int) -> bool:
        iv = self.veto.get((tk, s))
        if iv is None:
            return False
        starts, ends = iv
        i = bisect.bisect_right(starts, rx) - 1
        # intervals may overlap: check back a few
        j = i
        while j >= 0 and i - j < 8:
            if rx < ends[j]:
                return True
            j -= 1
        return False

    def m(self, tk: str) -> MarketPnL:
        r = self.pnl.get(tk)
        if r is None:
            r = self.pnl[tk] = MarketPnL(tk)
        return r

    def _fill(self, tk: str, o: Order, qty: int, rx: int, sweep: bool = False) -> None:
        r = self.m(tk)
        born = self.level_born[tk].get((o.side, o.price))
        bs = self.best_since[tk].get(o.side)
        age_born = (rx - born) / 1e6 if born is not None else float("nan")
        age_best = (rx - bs) / 1e6 if bs is not None else float("nan")
        fkey = ("improve" if o.improved else "join", "sweep" if sweep else "partial", _age_bucket(age_best), _age_bucket(age_born))
        if self.fill_log is not None:
            self.fill_log.append((tk, rx, o.side, o.price, min(qty, o.remaining), o.improved, sweep))
        qty = min(qty, o.remaining)
        if qty <= 0:
            return
        o.remaining -= qty
        r.fills += 1
        if o.improved:
            r.improved_fills += 1
        mid = r.pre_mid if r.pre_mid is not None else r.last_mid  # cents, pre-sweep
        if o.side == "yes":       # our YES bid was hit: we buy YES at price
            cost = o.price / ONE * qty / QTY
            r.cash -= cost
            r.buy_cost += cost
            r.pos += qty
            r.bought += qty
            px, sign = o.price / 100, -1
        else:                     # our NO bid was hit: we sell YES at ONE - price
            proceeds = (ONE - o.price) / ONE * qty / QTY
            r.cash += proceeds
            r.sell_proceeds += proceeds
            r.no_paid += o.price / ONE * qty / QTY
            r.pos -= qty
            r.sold += qty
            px, sign = (ONE - o.price) / 100, 1
        if mid is not None:
            # spread capture is measured against the pre-sweep mid; inventory P&L then
            # starts from that same mid so the two parts sum to the total
            r.spread_capture += sign * (px - mid) / 100 * qty / QTY
            if r.last_mid is not None and r.last_mid != mid:
                # the sweep's own delta moved the mid before the trade message arrived and
                # inventory P&L was booked on the pre-fill position; re-book that move on
                # the filled quantity so spread + inventory == total
                r.inventory_pnl += (-sign * qty / QTY) * (r.last_mid - mid) / 100
        for h in (10, 30):
            self.fill_mo.append((rx + h * 1_000_000_000, tk, sign, px, qty, h, mid, fkey))
        r.max_abs_pos = max(r.max_abs_pos, abs(r.pos))
        if o.remaining == 0:
            self.orders[tk].pop(o.side, None)

    def _live(self, o: Order, rx: int) -> bool:
        return rx >= o.active_from and (o.cancel_at is None or rx < o.cancel_at)

    def _flush_unexplained(self, o: Order, rx: int, book: FastBook) -> None:
        """Negative deltas at our level not matched by a trade within 200ms are cancels."""
        while o.unexplained and o.unexplained[0][0] < rx - 200_000_000:
            _, _, q = o.unexplained.popleft()
            if o.ahead is None:
                continue
            if self.p.queue == "prorata":
                level = book.side(o.side).get(o.price, 0) + q  # level size before the cancel
                if level > 0:
                    o.ahead = int(o.ahead * max(0, level - q) / level)
            # pessimistic: cancels come from behind us; ahead unchanged

    # ---- events --------------------------------------------------------------
    def on_snapshot(self, tk: str, book: FastBook) -> None:
        self.orders[tk].clear()   # book was rebuilt; treat our orders as cancelled
        r = self.m(tk)
        m = book.mid()
        if m is not None:         # an empty snapshot (market closed / emptied) keeps the last known mid
            r.last_mid = m        # no inventory P&L is booked across a stale gap
        r.pre_mid = r.last_mid

    def resolve_markouts(self, tk: str, rx: int, book: FastBook) -> None:
        while self.fill_mo and self.fill_mo[0][0] <= rx:
            _, t, sign, px, q, h, mid0, fkey = self.fill_mo.popleft()
            r = self.pnl.get(t)
            mid = book.mid() if t == tk else (r.last_mid if r else None)
            if mid is not None:
                self.fill_markouts[h].append((sign * (px - mid), q))
                if h == 30:
                    acc = self.fill_by.setdefault(fkey, [0.0, 0.0])
                    acc[0] += sign * (px - mid) * q / QTY
                    acc[1] += q / QTY
                if h == 10 and mid0 is not None:
                    # mid move in the 10s after the fill, on the filled quantity: the
                    # adverse-selection slice of inventory P&L (negative = moved against us)
                    self.adverse_10s += sign * (mid0 - mid) / 100 * q / QTY

    def on_delta(self, tk: str, rx: int, ts_ms: int, side: str, price: int, before: int, after: int, book: FastBook, close_ns: int, ctx: "Context | None" = None) -> None:
        r = self.m(tk)
        for sd in ("yes", "no"):
            bp = book.best(sd)
            if self._last_best[tk].get(sd) != bp:
                self._last_best[tk][sd] = bp
                self.best_since[tk][sd] = rx
        mid = book.mid()
        if ts_ms != r.last_ts:
            r.pre_mid, r.last_ts = r.last_mid, ts_ms
        if mid is not None and r.last_mid is not None and tk not in self.stopped:
            r.inventory_pnl += (r.pos / QTY) * (mid - r.last_mid) / 100
        if mid is not None:
            r.last_mid = mid
            if self.p.post_jump_pause_s is not None:
                h = self.mid_hist[tk]
                h.append((rx, mid))
                while h and h[0][0] < rx - 2_000_000_000:
                    h.popleft()
                if abs(mid - h[0][1]) >= self.p.post_jump_c:
                    self.jump_until[tk] = rx + int(self.p.post_jump_pause_s * 1e9)
        self.resolve_markouts(tk, rx, book)
        if before == 0 and after > 0:
            self.level_born[tk][(side, price)] = rx
        elif after == 0:
            self.level_born[tk].pop((side, price), None)
        if self.p.max_ttx_h is not None and close_ns - rx > self.p.max_ttx_h * 3.6e12 and not self.orders[tk] and r.pos == 0:
            return   # far from close, nothing resting, nothing held: the decision would be vetoed anyway
        o = self.orders[tk].get(side)
        if o is not None and o.price == price:
            if o.ahead is None and rx >= o.active_from:
                o.ahead = before  # activate: everything resting is ahead of us
                o.last_seen = rx
                self.probe_ahead_at_place.append(before / QTY)
            elif o.ahead is not None and after < before:
                o.unexplained.append((rx, ts_ms, before - after))
            elif o.ahead is None and after > before:
                pass  # arrivals before activation are ahead of us anyway
        for oo in list(self.orders[tk].values()):
            prev_ahead = oo.ahead
            self._flush_unexplained(oo, rx, book)
            if oo.ahead is None and rx >= oo.active_from and oo.sig_until and oo.price + book.best("no" if oo.side == "yes" else "yes") >= ONE:
                # post-only at a price the other side still occupies: rejected by the exchange
                del self.orders[tk][oo.side]
                self.vetoes["post_only_cross"] += 1
                continue
            if oo.ahead is None and rx >= oo.active_from:
                oo.ahead = book.side(oo.side).get(oo.price, 0)
                oo.last_seen = rx
                self.probe_ahead_at_place.append(oo.ahead / QTY)
            elif oo.ahead is not None and prev_ahead is not None:
                self.probe_adv_qty += max(0, prev_ahead - oo.ahead) / QTY
                self.probe_live_s += (rx - oo.last_seen) / 1e9
                oo.last_seen = rx
        self._requote(tk, rx, book, close_ns, ctx)

    def on_trade(self, tk: str, rx: int, ts_ms: int, taker_side: str, yes_price: int, qty: int, book: FastBook) -> None:
        self.m(tk).market_volume += qty
        side = "yes" if taker_side == "no" else "no"        # resting side consumed
        price = yes_price if side == "yes" else ONE - yes_price
        if self.p.cluster_ms is not None and book.side(side).get(price, 0) == 0:
            self.swept_until[tk][side] = rx + int(self.p.cluster_ms * 1e6)  # level emptied by this sweep
        o = self.orders[tk].get(side)
        if self.p.price_priority and o is not None and o.ahead is not None and self._live(o, rx) and o.price > price and o.remaining > 0:
            # the taker traded through our level: by price priority our order fills before anything at the worse price
            self.vetoes["priority_fills"] += 1
            self.m(tk).sweep_fills += 1
            o.ahead = 0
            self._fill(tk, o, qty, rx, sweep=True)
            return
        if o is None or o.price != price or o.ahead is None or not self._live(o, rx):
            return
        # this trade explains the matching negative delta(s)
        left = qty
        while o.unexplained and left > 0 and o.unexplained[0][1] == ts_ms:
            r0, t0, q = o.unexplained[0]
            take = min(q, left)
            left -= take
            if take == q:
                o.unexplained.popleft()
            else:
                o.unexplained[0] = (r0, t0, q - take)
        if qty <= o.ahead:
            self.probe_adv_qty += qty / QTY
            o.ahead -= qty
        else:
            spill = qty - o.ahead
            self.probe_adv_qty += o.ahead / QTY
            if not o.filled_any:
                o.filled_any = True
                self.probe_ttf.append((rx - o.active_from) / 1e9)
                self.probe_ahead_at_fill.append(o.ahead / QTY)
            o.ahead = 0
            self._fill(tk, o, spill, rx)

    def on_tick(self, tk_list: list[str], rx: int, mid: float, mid_1s_ago: float | None, ctx: "Context | None" = None,
                books: "dict[str, FastBook] | None" = None) -> None:
        if self.p.dfair_cancel_c is not None and ctx is not None:
            for tk in tk_list:
                close_ns = ctx.closes.get(tk)
                if close_ns is None:
                    continue
                f = ctx.fair_c(tk, rx, close_ns, self.p.fair_spot, self.p.vol_mult, self.p.kernel)
                if f is None:
                    continue
                ref = None
                if self.p.dfair_window_s is not None:
                    h = self.fair_hist[tk]
                    h.append((rx, f))
                    lo = rx - int(self.p.dfair_window_s * 1e9)
                    while len(h) > 1 and h[1][0] <= lo:
                        h.popleft()
                    ref = h[0][1] if h[0][0] <= lo else None
                for s, o in list(self.orders[tk].items()):
                    if o.cancel_at is not None:
                        continue
                    if self.p.dfair_window_s is None:
                        if o.fair_at_place is None:
                            o.fair_at_place = f
                            continue
                        d = f - o.fair_at_place
                    else:
                        if ref is None:
                            break
                        d = f - ref
                    # fair up -> our ask (NO bid) is stale; fair down -> our bid is stale
                    if (s == "no" and d >= self.p.dfair_cancel_c) or (s == "yes" and -d >= self.p.dfair_cancel_c):
                        o.cancel_at = rx + self.lat
                        self.vetoes["dfair"] += 1
        if self.p.signal_move is None or mid_1s_ago is None:
            return
        d = mid - mid_1s_ago
        if abs(d) < self.p.signal_move:
            return
        stale = "no" if d > 0 else "yes"   # spot up -> our YES ask (NO bid) is stale; down -> our bid
        until = rx + int(self.p.cooldown_ms * 1e6)
        for tk in tk_list:
            self.blocked[tk][stale] = until
            o = self.orders[tk].get(stale)
            if o is not None and o.cancel_at is None:
                o.cancel_at = rx + self.lat_signal
        if self.p.signal_improve and books is not None:
            self._signal_improve(tk_list, rx, "yes" if d > 0 else "no", books)

    def _signal_improve(self, tk_list: list[str], rx: int, fresh: str, books: "dict[str, FastBook]") -> None:
        """Spot moved in favour of side `fresh`: the other side's touch is about to be pulled or taken.
        Post-only at that price now; if the level is still occupied when we arrive the exchange
        rejects it (post-only cross), otherwise we are the first bid at the vacated level."""
        p = self.p
        other = "no" if fresh == "yes" else "yes"
        for tk in tk_list:
            if tk in self.stopped:
                continue
            book = books[tk]
            if book.best_yes < 0 or book.best_no < 0:
                continue
            spread = ONE - book.best_no - book.best_yes
            tick = tick_at(book.best(fresh))
            price = book.best(fresh) + tick if spread > tick else ONE - book.best(other)  # inside the spread, else the old ask
            if price <= tick or price >= ONE - tick:
                continue
            r = self.m(tk)
            lim = p.max_pos * QTY - p.size * QTY
            if (fresh == "yes" and r.pos > lim) or (fresh == "no" and r.pos < -lim):
                continue
            if rx < self.blocked[tk][fresh]:
                continue
            cur = self.orders[tk].get(fresh)
            if cur is not None and cur.cancel_at is None and cur.price >= price:
                continue  # already there or better
            size = p.size * QTY
            if p.capital is not None:
                reserved = sum(x.price / ONE * x.remaining / QTY for x in self.orders[tk].values() if x.cancel_at is None and x is not cur)
                free = p.capital - r.locked() - reserved
                afford = int(free / (price / ONE))
                size = min(p.size, max(0, afford)) * QTY
                if size < QTY:
                    self.vetoes["capital"] += 1
                    continue
            # replace the resting join on this side (its fills during the cancel window are the benign direction; ignored)
            o = Order(fresh, price, size, None, rx + self.lat_sig_place, improved=True)
            o.sig_until = rx + int(p.signal_hold_ms * 1e6)
            self.orders[tk][fresh] = o
            self.vetoes["signal_improve"] += 1

    def _requote(self, tk: str, rx: int, book: FastBook, close_ns: int, ctx: "Context | None" = None) -> None:
        orders = self.orders[tk]
        # drop cancelled orders whose cancel has landed
        for s in list(orders):
            o = orders[s]
            if o.cancel_at is not None and rx >= o.cancel_at:
                del orders[s]
        r = self.m(tk)
        stop = rx >= close_ns - int(self.p.stop_before_s * 1e9)
        if stop:
            if tk not in self.stopped:
                self.stopped.add(tk)
                r.stop_rx = rx
                mid = book.mid()
                if mid is None:
                    mid = r.last_mid   # one-sided book at the stop (outcome known): mark at the last two-sided mid
                if mid is not None:
                    p = mid / 100
                    r.flatten_cost = abs(r.pos) / QTY * (0.005 + TAKER_FEE * p * (1 - p))
                    if self.p.flatten_at_stop and r.pos != 0 and book.best_yes >= 0 and book.best_no >= 0:
                        # take the touch: sell YES into the best YES bid, or buy YES at the best YES ask (= 1 - best NO bid)
                        n = abs(r.pos) / QTY
                        if r.pos > 0:
                            px = book.best_yes / ONE
                            r.cash += n * (px - TAKER_FEE * px * (1 - px))
                        else:
                            px = (ONE - book.best_no) / ONE
                            r.cash -= n * (px + TAKER_FEE * px * (1 - px))
                        r.flattened = n
                        r.pos = 0
                    r.mid_at_stop = mid
                    r.mark_pnl = r.cash + r.pos / QTY * mid / 100   # provisional; replaced by settlement in resolve()
            for o in orders.values():
                if o.cancel_at is None:
                    o.cancel_at = rx + self.lat
            return
        if book.stale or book.best_yes < 0 or book.best_no < 0:
            return
        if self.p.flatten_above is not None and abs(r.pos) > self.p.flatten_above * QTY:
            # take the touch for the excess: sell YES into the best YES bid, or buy YES at the best YES ask
            excess = (abs(r.pos) - self.p.flatten_above * QTY) / QTY
            if r.pos > 0:
                px = book.best_yes / ONE
                r.cash += excess * (px - TAKER_FEE * px * (1 - px))
                r.pos -= int(excess * QTY)
            else:
                px = (ONE - book.best_no) / ONE
                r.cash -= excess * (px + TAKER_FEE * px * (1 - px))
                r.pos += int(excess * QTY)
            r.flattened += excess
            self.vetoes["taken"] += 1
        spread = (ONE - book.best_no) - book.best_yes
        tick = {"yes": tick_at(book.best_yes), "no": tick_at(book.best_no)}
        improve = {s: (self.p.offset_ticks == 0 and spread > tick[s] and not self.p.no_improve) for s in ("yes", "no")}
        want = {
            "yes": book.best_yes + (tick["yes"] if improve["yes"] else 0) - self.p.offset_ticks * tick["yes"],
            "no": book.best_no + (tick["no"] if improve["no"] else 0) - self.p.offset_ticks * tick["no"],
        }
        pos = r.pos
        lim = self.p.max_pos * QTY - self.p.size * QTY
        allow = {"yes": pos <= lim, "no": pos >= -lim}
        p = self.p
        reducing = {"yes": pos < 0, "no": pos > 0}   # a fill on this side moves the position toward zero
        if p.greeks_cap is not None and ctx is not None:
            g = ctx.delta_sigma10(tk, close_ns)
            if g is not None and g >= p.greeks_cap:
                for s in ("yes", "no"):
                    if not (p.reduce_only_exempt and reducing[s]):
                        allow[s] = False
                        self.vetoes["greeks"] += 1
        skewed = {"yes": False, "no": False}
        if p.skew_at is not None and abs(pos) >= p.skew_at * p.max_pos * QTY:
            for s in ("yes", "no"):
                if reducing[s] and spread <= tick[s] and want[s] + tick[s] < ONE - tick[s]:
                    want[s] += tick[s]    # lean: improve the reducing side by a tick
                    skewed[s] = True
        if p.stale_feed_ms is not None and self.feed_lag_ms > p.stale_feed_ms:
            allow = {"yes": False, "no": False}
            self.vetoes["stale_feed"] += 2
        if p.min_touch_age_ms is not None:
            for s in ("yes", "no"):
                bs = self.best_since[tk].get(s)
                if allow[s] and not improve[s] and (bs is None or rx - bs < p.min_touch_age_ms * 1e6):
                    allow[s] = False
                    self.vetoes["young_touch"] += 1
        if p.wide_spread_ticks is not None:
            for s in ("yes", "no"):
                if spread > p.wide_spread_ticks * tick[s]:
                    if p.wide_spread_pull:
                        allow[s] = False
                        self.vetoes["wide_spread"] += 1
                    elif improve[s]:
                        improve[s] = False
                        want[s] -= tick[s]   # join the touch instead of improving into an information-state spread
                        self.vetoes["wide_no_improve"] += 1
        if p.post_jump_pause_s is not None and rx < self.jump_until[tk]:
            allow = {"yes": False, "no": False}
            self.vetoes["post_jump"] += 2
        if p.improve_only:
            for s in ("yes", "no"):
                if allow[s] and not improve[s]:
                    allow[s] = False
                    self.vetoes["join_disallowed"] += 1
        if self.veto:
            for s in ("yes", "no"):
                if allow[s] and self._vetoed(tk, s, rx):
                    allow[s] = False
                    self.vetoes["ext_veto"] += 1
        if p.alpha_thr is not None and ctx is not None and ctx.alpha is not None:
            if ctx.alpha <= -p.alpha_thr and allow["yes"]:   # spot predicted down: our bid is stale
                allow["yes"] = False
                self.vetoes["alpha"] += 1
            if ctx.alpha >= p.alpha_thr and allow["no"]:     # spot predicted up: our ask is stale
                allow["no"] = False
                self.vetoes["alpha"] += 1
        depth = {"yes": book.yes.get(book.best_yes, 0), "no": book.no.get(book.best_no, 0)}
        for s in ("yes", "no"):
            other = "no" if s == "yes" else "yes"
            if p.min_depth is not None and spread <= tick[s] and depth[s] < p.min_depth * QTY and allow[s]:
                allow[s] = False
                self.vetoes["thin"] += 1
            if p.imb_thr is not None and allow[s] and depth[s] + depth[other] > 0 and \
                    (depth[other] - depth[s]) / (depth[other] + depth[s]) >= p.imb_thr:
                allow[s] = False
                self.vetoes["imbalance"] += 1
            if p.cluster_ms is not None and allow[s] and rx < self.swept_until[tk][s]:
                allow[s] = False
                self.vetoes["cluster"] += 1
        gap = None
        if (p.fair_gap_thr is not None or p.fair_gap_join is not None) and ctx is not None:
            gap = ctx.fair_gap_c(tk, book, rx, close_ns, p.vol_mult)
        if p.fair_gap_thr is not None and gap is not None:
            if gap < -p.fair_gap_thr and allow["yes"]:
                allow["yes"] = False
                self.vetoes["fair_bid"] += 1
            if gap > p.fair_gap_thr and allow["no"]:
                allow["no"] = False
                self.vetoes["fair_ask"] += 1
        if p.edge_theta is not None and ctx is not None and ctx.edge_model is not None:
            micro = ctx.micro_unsigned()
            ttx_min = (close_ns - rx) / 6e10
            for s in ("yes", "no"):
                other = "no" if s == "yes" else "yes"
                imb = (depth[other] - depth[s]) / (depth[other] + depth[s]) if depth[other] + depth[s] > 0 else 0.0
                o = orders.get(s)
                q = o.ahead / QTY if (o is not None and o.ahead is not None) else depth[s] / QTY
                e = ctx.edge_model.edge(s, imb, micro, ttx_min, q)
                if e is None:
                    continue
                if e < -p.edge_theta:
                    if self.adverse_since[tk][s] < 0:
                        self.adverse_since[tk][s] = rx
                    if rx - self.adverse_since[tk][s] >= p.edge_debounce_ms * 1e6:
                        self.edge_blocked[tk][s] = True
                else:
                    self.adverse_since[tk][s] = -1
                    if e >= 0:
                        self.edge_blocked[tk][s] = False
                if self.edge_blocked[tk][s] and allow[s]:
                    allow[s] = False
                    self.vetoes["edge"] += 1
        for s in ("yes", "no"):
            o = orders.get(s)
            ok = allow[s] and rx >= self.blocked[tk][s]
            if not ok and p.keep_if_ahead_lt is not None and o is not None and o.cancel_at is None \
                    and o.ahead is not None and o.ahead < p.keep_if_ahead_lt * QTY and o.price == want[s] \
                    and (s == "yes" and pos <= lim or s == "no" and pos >= -lim):
                ok = True   # near the front: fills here are the benign partials; keep the position
                self.vetoes["kept_front"] += 1
            if o is not None and o.cancel_at is None:
                off = abs(o.price - want[s]) >= p.reprice_ticks * tick[s] if o.price != want[s] else False
                if off and o.sig_until and rx < o.sig_until and o.price > want[s]:
                    off = False   # a signal improve ahead of the touch is held for its window
                    self.vetoes["sig_held"] += 1
                young = p.min_rest_ms is not None and rx - o.active_from < p.min_rest_ms * 1e6
                if not ok or (off and not young):
                    o.cancel_at = rx + self.lat
                elif off and young:
                    self.vetoes["held_young"] += 1
            if ok and (o is None or o.cancel_at is not None) and not any(
                x.side == s and x.cancel_at is None for x in orders.values()
            ):
                if p.fair_gap_join is not None and gap is not None and (
                        (s == "yes" and gap < -p.fair_gap_join) or (s == "no" and gap > p.fair_gap_join)):
                    self.vetoes["fair_join"] += 1
                    continue
                if p.min_level_age_ms is not None and not improve[s]:
                    born = self.level_born[tk].get((s, want[s]))
                    if born is not None and rx - born < p.min_level_age_ms * 1e6:
                        self.vetoes["young_level"] += 1
                        continue
                if p.join_theta is not None and ctx is not None and ctx.edge_model is not None and not (p.reduce_only_exempt and reducing[s]):
                    other = "no" if s == "yes" else "yes"
                    imb = (depth[other] - depth[s]) / (depth[other] + depth[s]) if depth[other] + depth[s] > 0 else 0.0
                    q_join = 0.0 if improve[s] else depth[s] / QTY
                    e = ctx.edge_model.edge(s, imb, ctx.micro_unsigned(), (close_ns - rx) / 6e10, q_join)
                    if e is not None and e < -p.join_theta:
                        self.vetoes["join"] += 1
                        continue
                # place: becomes live after latency; replaces a cancelled order once it lands
                if o is None or rx >= o.cancel_at:
                    size = self.p.size * QTY
                    if p.size_skew and pos != 0:
                        frac = min(1.0, abs(pos) / (p.max_pos * QTY))
                        mult = (1 + frac) if reducing[s] else (1 - frac)
                        size = max(0, int(round(self.p.size * mult))) * QTY
                        if size < QTY:
                            self.vetoes["size_skew"] += 1
                            continue
                    if p.skew_at is not None and not reducing[s] and abs(pos) >= p.skew_at * p.max_pos * QTY:
                        frac = max(0.0, 1 - (abs(pos) / QTY - p.skew_at * p.max_pos) / ((1 - p.skew_at) * p.max_pos))
                        size = max(QTY, int(self.p.size * frac) * QTY)   # increasing side shrinks toward 1 lot at the cap
                    if p.capital is not None:
                        reserved = sum(x.price / ONE * x.remaining / QTY for x in orders.values() if x.cancel_at is None)
                        free = p.capital - r.locked() - reserved - (self._locked_all(tk, rx) if p.global_capital else 0.0)
                        other_needs = 1 if (allow[("no" if s == "yes" else "yes")] and ("no" if s == "yes" else "yes") not in orders) else 0
                        budget = free / (1 + other_needs)
                        afford = int(budget / (want[s] / ONE)) if want[s] > 0 else 0
                        size = min(size // QTY, max(0, afford)) * QTY   # capital caps the (possibly skewed) size
                        if size < QTY:
                            self.vetoes["capital"] += 1
                            continue
                    orders[s] = Order(s, want[s], size, None, rx + self.lat_place, improved=improve[s] or skewed[s])
                    if p.dfair_cancel_c is not None and ctx is not None:
                        orders[s].fair_at_place = ctx.fair_c(tk, rx, close_ns, p.fair_spot, p.vol_mult, p.kernel)

    def mark_unfinished(self, books: dict) -> None:
        """Markets still open when the tape ends: mark at the last mid (flatten cost not charged; reported as unrealized)."""
        for tk, r in self.pnl.items():
            if r.mark_pnl is not None or not r.fills:
                continue
            b = books.get(tk)
            mid = b.mid() if b is not None else None
            if mid is None:
                mid = r.last_mid
            if mid is None:
                continue
            r.mark_pnl = r.cash + r.pos / QTY * mid / 100
            r.mid_at_stop = mid
            if r.stop_rx is None:
                r.stop_rx = 0

    def settle_now(self, tk: str, v: float) -> None:
        """The market settled at v (0/1) while the run continues: realise any position and free its collateral."""
        r = self.pnl.get(tk)
        if r is None:
            return
        if r.pos != 0:
            r.cash += r.pos / QTY * v
            r.pos = 0
            r.settle = v
        if r.mark_pnl is not None or r.fills:
            r.mark_pnl = r.cash
            if r.stop_rx is None:
                r.stop_rx = 0
        self.stopped.add(tk)
        for o in self.orders.pop(tk, {}).values():
            pass   # resting orders die with the market

    def resolve(self, settles: dict[str, float]) -> None:
        """Mark positions carried past the stop at the settlement value instead of the stop-time mid."""
        for tk, r in self.pnl.items():
            v = settles.get(tk)
            if v is None or r.mark_pnl is None or r.pos == 0:
                continue
            r.settle = v
            r.mark_pnl = r.cash + r.pos / QTY * v

    # ---- summary ---------------------------------------------------------------
    def summary(self, test_from_ns: int = 0) -> dict:
        ms = [r for r in self.pnl.values() if r.mark_pnl is not None]
        test = [r for r in ms if r.stop_rx >= test_from_ns]
        if not ms:
            return {"name": self.p.name, "markets": 0}
        pnl = [r.mark_pnl for r in ms]
        traded = sum(r.bought + r.sold for r in ms) / QTY
        vol = sum(r.market_volume for r in ms) / QTY
        # realized: matched buys/sells at average prices; unrealized: the rest of the mark
        realized = 0.0
        for r in ms:
            if r.bought and r.sold:
                matched = min(r.bought, r.sold)
                realized += matched / QTY * (r.sell_proceeds / (r.sold / QTY) - r.buy_cost / (r.bought / QTY))
        sd = st.pstdev(pnl) if len(pnl) > 1 else 0.0
        fm = self.fill_markouts[30]
        ttf = sorted(self.probe_ttf)
        pct = lambda xs, p: xs[min(len(xs) - 1, int(p * len(xs)))] if xs else float("nan")
        return {
            "name": self.p.name,
            "markets": len(ms),
            "probe_advance_per_s": self.probe_adv_qty / self.probe_live_s if self.probe_live_s else float("nan"),
            "probe_ttf_p50": pct(ttf, 0.5), "probe_ttf_p90": pct(ttf, 0.9),
            "probe_ahead_at_place_p50": pct(sorted(self.probe_ahead_at_place), 0.5),
            "probe_ahead_at_fill_p50": pct(sorted(self.probe_ahead_at_fill), 0.5),
            "probe_fill_rate": len(ttf) / max(1, len(self.probe_ahead_at_place)),
            "pnl_$": sum(pnl),
            "test_pnl_$": sum(r.mark_pnl for r in test),
            "test_spread_$": sum(r.spread_capture for r in test),
            "test_inventory_$": sum(r.inventory_pnl for r in test),
            "test_markets": len(test),
            "vetoes": dict(self.vetoes),
            "spread_$": sum(r.spread_capture for r in ms),
            "inventory_$": sum(r.inventory_pnl for r in ms),
            "adverse_10s_$": self.adverse_10s,
            "realized_$": realized,
            "unrealized_$": sum(pnl) - realized,
            "pnl_per_market_$": st.mean(pnl),
            "pnl_sd_$": sd,
            "t_stat": st.mean(pnl) / (sd / len(pnl) ** 0.5) if sd else float("nan"),
            "fill_markout_30s_c": (sum(m * q for m, q in fm) / sum(q for _, q in fm)) if fm else float("nan"),
            "improved_fill_%": sum(r.improved_fills for r in ms) / max(1, sum(r.fills for r in ms)) * 100,
            "worst_$": min(pnl),
            "best_$": max(pnl),
            "contracts": traded,
            "pnl_c_per_contract": sum(pnl) / traded * 100 if traded else float("nan"),
            "per_market": ms,
            "fill_by": self.fill_by,
            "fill_share_%": traded / vol * 100 if vol else float("nan"),
            "fills": sum(r.fills for r in ms),
            "avg_max_pos": st.mean(r.max_abs_pos for r in ms) / QTY,
            "end_pos_abs": st.mean(abs(r.pos) for r in ms) / QTY,
            "flatten_cost_$": sum(r.flatten_cost for r in ms),
        }


# ------------------------------------------------------------------ context ---

ALPHA_FEATS = ["cb_imb", "cb_micro", "coinbase_flow_1s", "coinbase_flow_5s", "kraken_flow_1s", "kraken_flow_5s",
               "gemini_btc_flow_5s", "bitstamp_flow_5s", "ret_1s", "ret_5s", "ret_30s", "kr_minus_cb"]


def fit_alpha(parquet: Path, train_frac: float = 0.6) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """Ridge for unsigned Δspot5s from unsigned spot features, on the first train_frac of sweeps.
    Returns (w, mu, sd, cutoff_rx_ns). Missing flows are treated as zero."""
    df = pl.read_parquet(parquet).sort("rx_ns")
    sign = pl.when(pl.col("taker_side") == "yes").then(1.0).otherwise(-1.0)
    df = df.with_columns([(pl.col(c).fill_null(0.0) * sign).alias(c) for c in ALPHA_FEATS] + [(pl.col("dspot5") * sign).alias("y")])
    df = df.filter(pl.col("y").is_not_null())
    n = df.height
    cut = int(n * train_frac)
    X = df.select(ALPHA_FEATS).to_numpy().astype(float)
    y = df["y"].to_numpy().astype(float)
    mu, sd = X[:cut].mean(0), X[:cut].std(0) + 1e-12
    Xs = (X[:cut] - mu) / sd
    w = np.linalg.solve(Xs.T @ Xs + 10.0 * np.eye(Xs.shape[1]), Xs.T @ y[:cut])
    pred = ((X[cut:] - mu) / sd) @ w
    r = np.corrcoef(pred, y[cut:])[0, 1]
    print(f"alpha fit: train {cut:,} test {n-cut:,}, out-of-sample corr {r:.3f}", file=sys.stderr)
    return w, mu, sd, int(df["rx_ns"][cut])


Q_EDGES = [0, 50, 100, 200, 500, 1000, 2000, 5000, 1e12]
IMB_EDGES = [-1e9, -0.33, 0.33, 1e9]
MICRO_EDGES = [-1e9, -0.5, 0.5, 1e9]
TTX_EDGES = [0, 2, 5, 10, 1e9]


def _bucket(x: float, edges: list[float]) -> int:
    for i in range(len(edges) - 1):
        if edges[i] <= x < edges[i + 1]:
            return i
    return len(edges) - 2


class EdgeModel:
    """E[half-spread + 30s markout | fill from q ahead, state], estimated from the sweep
    dataset (first train_frac of the day). States are expressed from the RESTING order's
    side: imbalance = (other side depth - our side depth)/(sum) at the touch, micro = spot
    microprice pressure against our order ($), ttx in minutes. Marginal tables by
    (state, q) are combined additively around the all-state curve."""

    def __init__(self, parquet: Path, train_frac: float = 0.6, order: int = 100):
        df = pl.read_parquet(parquet).filter(pl.col("klass") != "unknown").sort("rx_ns")
        self.cutoff_rx = int(df["rx_ns"][min(df.height - 1, int(df.height * train_frac))])
        df = df[: int(df.height * train_frac)]
        df = df.filter(pl.col("mo0").is_not_null() & pl.col("mo30").is_not_null())
        # features in the parquet are signed into the taker's direction == adverse-for-the-resting-order direction
        self.all = self._curve(df, order)
        self.imb = {i: self._curve(df.filter((pl.col("touch_imb") >= lo) & (pl.col("touch_imb") < hi)), order)
                    for i, (lo, hi) in enumerate(zip(IMB_EDGES[:-1], IMB_EDGES[1:]))}
        self.micro = {i: self._curve(df.filter((pl.col("cb_micro") >= lo) & (pl.col("cb_micro") < hi)), order)
                      for i, (lo, hi) in enumerate(zip(MICRO_EDGES[:-1], MICRO_EDGES[1:]))}
        self.ttx = {i: self._curve(df.filter((pl.col("ttx_min") >= lo) & (pl.col("ttx_min") < hi)), order)
                    for i, (lo, hi) in enumerate(zip(TTX_EDGES[:-1], TTX_EDGES[1:]))}
        print("edge model (all states, by q ahead): " + " ".join(f"{q}:{e:+.2f}" for q, e in zip(Q_EDGES[:-1], self.all)), file=sys.stderr)

    @staticmethod
    def _curve(d: pl.DataFrame, order: int) -> list[float | None]:
        out = []
        for q in Q_EDGES[:-1]:
            f = d.filter(pl.col("qty") > q).with_columns(pl.min_horizontal(pl.lit(order), pl.col("qty") - q).alias("fill"))
            if f.height < 50:
                out.append(None)
                continue
            w = f["fill"]
            out.append(float(((f["mo0"] + f["mo30"]) * w).sum() / w.sum()))
        return out

    def edge(self, side: str, imb: float, micro_unsigned: float | None, ttx_min: float, q: float) -> float | None:
        qi = _bucket(q, Q_EDGES)
        base = self.all[qi]
        if base is None:
            return None
        e = base
        c = self.imb[_bucket(imb, IMB_EDGES)][qi]
        if c is not None:
            e += c - base
        if micro_unsigned is not None:
            # pressure against a YES bid is spot going DOWN (micro < 0); against a NO bid (our ask) it is UP
            m = -micro_unsigned if side == "yes" else micro_unsigned
            c = self.micro[_bucket(m, MICRO_EDGES)][qi]
            if c is not None:
                e += c - base
        c = self.ttx[_bucket(ttx_min, TTX_EDGES)][qi]
        if c is not None:
            e += c - base
        return e


class Context:
    """Per-time market context shared by all quoters: predicted spot drift and option Greeks."""

    def __init__(self, spot: SpotState, strikes: dict[str, float], alpha_model, edge_model: EdgeModel | None = None):
        self.closes: dict[str, int] = {}
        self.spot = spot
        self.strikes = strikes
        self.alpha_model = alpha_model
        self.edge_model = edge_model
        self.alpha: float | None = None

    brti_series: SpotSeries | None = None
    cb_series: SpotSeries | None = None

    def fair_c(self, tk: str, t_ns: int, close_ns: int, spot: str, vol_mult: float = 1.0, kernel: str = "normal") -> float | None:
        K = self.strikes.get(tk)
        ser = self.cb_series if spot == "coinbase" else self.brti_series
        if not K or ser is None:
            return None
        vol = ser.vol()
        if vol is None:
            return None
        f = fair_value(ser, K, t_ns / 1e9, close_ns / 1e9, sigma=vol * vol_mult, kernel=kernel)
        return None if f is None else f * 100

    def fair_gap_c(self, tk: str, book: FastBook, rx: int, close_ns: int, vol_mult: float) -> float | None:
        """fair - mid in cents, from the BRTI-based settlement-aware model."""
        K = self.strikes.get(tk)
        if not K or self.brti_series is None:
            return None
        vol = self.brti_series.vol()
        if vol is None:
            return None
        f = fair_value(self.brti_series, K, rx / 1e9, close_ns / 1e9, sigma=vol * vol_mult)
        mid = book.mid()
        if f is None or mid is None:
            return None
        return f * 100 - mid

    def micro_unsigned(self) -> float | None:
        sp = self.spot
        if sp.cb_bs is None or sp.cb_as is None or sp.cb_bs + sp.cb_as <= 0 or sp.cb_bid is None:
            return None
        mid = (sp.cb_bid + sp.cb_ask) / 2
        return (sp.cb_bid * sp.cb_as + sp.cb_ask * sp.cb_bs) / (sp.cb_bs + sp.cb_as) - mid

    def refresh_alpha(self, rx: int) -> None:
        if self.alpha_model is None:
            return
        f = self.spot.features(rx, 1)
        if "cb_imb" not in f:
            return
        w, mu, sd, _ = self.alpha_model
        x = np.array([f.get(c, 0.0) for c in ALPHA_FEATS])
        self.alpha = float(((x - mu) / sd) @ w)

    def delta_sigma10(self, tk: str, close_ns: int) -> float | None:
        """Price change (fraction of $1) for a 1-sigma spot move over 10s: phi(d) * sqrt(10 / tau)."""
        K = self.strikes.get(tk)
        S = self.spot.brti_last
        vol = self.spot.realized_vol()
        if not K or not S or not vol:
            return None
        tau = max(1.0, (close_ns - self.spot.brti[-1][0]) / 1e9)
        d = math.log(S / K) / (vol * math.sqrt(tau))
        return math.exp(-d * d / 2) / math.sqrt(2 * math.pi) * math.sqrt(10 / tau)


# ------------------------------------------------------------------- driver ---

def run(data_dir: Path, day: date, series: str, venue: str, configs: list[Params],
        alpha_parquet: Path | None = None, train_frac: float = 0.6, checkpoint=None, no_spot: bool = False,
        warm_days: int = 0) -> tuple[list[dict], int]:
    """checkpoint(results) is called every 10M records with the summaries so far (markets completed to that point)."""
    quoters = [Quoter(p) for p in configs]
    books: dict[str, FastBook] = {}
    closes: dict[str, int] = {}
    ticks: deque = deque()   # (rx_ns, mid)
    need_fair = any(p.fair_gap_thr is not None or p.fair_gap_join is not None or p.dfair_cancel_c is not None for p in configs)
    need_ctx = need_fair or any(p.alpha_thr is not None or p.greeks_cap is not None or p.edge_theta is not None or p.join_theta is not None for p in configs)
    alpha_model = fit_alpha(alpha_parquet) if (alpha_parquet and any(p.alpha_thr is not None for p in configs)) else None
    test_from = alpha_model[3] if alpha_model else 0
    strikes: dict[str, float] = {}
    tickers = sorted({r.raw["msg"]["market_ticker"] for r in iter_records(data_dir, day)
                      if r.raw.get("type") == "orderbook_snapshot" and r.raw["msg"]["market_ticker"].startswith(series + "-")})
    strikes = fetch_strikes(tickers) if series.startswith(("KXBTC", "KXETH", "KXSOL", "KXXRP")) else {}   # settlement / greeks need a strike; non-crypto series have none
    global TICK_GRID
    TICK_GRID = "tapered_deci_cent" if series.endswith("15M") else "linear_cent"   # only the 15-minute crypto series use the tapered grid
    print(f"tick grid {TICK_GRID}", file=sys.stderr)
    avg60: list[tuple[int, float]] = []   # (window_end_ms, BRTI 60s average) from the 1/s channel
    spot = SpotState()
    edge_model = EdgeModel(alpha_parquet, train_frac=train_frac) if (alpha_parquet and any(p.edge_theta is not None or p.join_theta is not None for p in configs)) else None
    if edge_model is not None and not test_from:
        test_from = edge_model.cutoff_rx
    ctx = Context(spot, strikes, alpha_model, edge_model)
    if need_fair:
        ctx.brti_series = SpotSeries()
        ctx.cb_series = SpotSeries()
    ctx.closes = closes
    closing: dict[int, list[str]] = defaultdict(list)   # close ms -> tickers, for settle-on-close
    asset = "ETH" if "ETH" in series else "BTC"
    index_id = "ETHUSD_RTI" if asset == "ETH" else "BRTI"   # cfbenchmarks settlement index for the series

    signal_venues = set()
    for p in configs:
        signal_venues |= set(p.signal_venues)
    extra = [v for v in ("okx", "bybit") if v in signal_venues and (data_dir / "spot" / v).is_dir()]
    vticks: dict[str, deque] = {v: deque() for v in signal_venues}

    def spot_events():
        its = [iter_spot(data_dir, v, day) for v in (*VENUES, *extra)]
        yield from heapq.merge(*its, key=lambda e: e.rx_ns)

    def cb_sizes():
        for rec in iter_records(data_dir / "spot" / "coinbase", day):
            raw = rec.raw
            if raw.get("type") == "ticker" and raw.get("product_id") == f"{asset}-USD" and raw.get("best_bid_size"):
                yield ("cbsz", rec.rx_ns, float(raw["best_bid_size"]), float(raw["best_ask_size"]))

    n = 0
    # warm start: rebuild the books from earlier days' snapshots and deltas (no quoting), for markets
    # whose subscription snapshot predates the day under study
    from datetime import timedelta as _td
    for back in range(warm_days, 0, -1):
        wd = day - _td(days=back)
        nwarm = 0
        for rec in iter_records(data_dir, wd):
            raw = rec.raw
            t = raw.get("type")
            if t not in ("orderbook_snapshot", "orderbook_delta"):
                continue
            msg = raw["msg"]
            tk = msg["market_ticker"]
            if not tk.startswith(series + "-"):
                continue
            b = books.get(tk)
            if b is None:
                ct = close_time(tk)
                if ct is None:
                    continue
                b = books[tk] = FastBook()
                closes[tk] = int(ct * 1e9)
                closing[closes[tk] // 1_000_000].append(tk)
            if t == "orderbook_snapshot":
                b.snapshot(msg)
                nwarm += 1
            elif not b.stale:
                try:
                    b.delta(msg["side"], parse_price(msg["price_dollars"]), parse_qty(msg["delta_fp"]))
                except ValueError:
                    b.stale = True
        print(f"warm start from {wd}: {nwarm} snapshots, {sum(1 for b in books.values() if not b.stale)} live books", file=sys.stderr)
    stream = iter_records(data_dir, day) if no_spot else heapq.merge(iter_records(data_dir, day), spot_events(), cb_sizes(),
                         key=lambda e: e[1] if isinstance(e, tuple) else e.rx_ns)
    for rec in stream:
        n += 1
        if n % 5_000_000 == 0:
            print(f"  {n/1e6:.0f}M records", file=sys.stderr)
            if checkpoint is not None and n % 10_000_000 == 0:
                try:
                    checkpoint([q.summary(test_from) for q in quoters])
                except Exception as e:  # noqa: BLE001
                    print(f"  checkpoint failed: {e}", file=sys.stderr)
        if isinstance(rec, tuple):
            spot.on_quote_sizes(rec[2], rec[3])
            continue
        rx = rec.rx_ns
        if isinstance(rec, SpotTrade):
            if rec.asset == asset and rec.venue in VENUES:
                spot.on_trade(rec)
            continue
        if isinstance(rec, SpotQuote):
            if rec.asset != asset:
                continue
            if rec.venue in VENUES:
                spot.on_quote(rec)
            if rec.venue == venue and rec.ts_ms is not None:
                lag = rx / 1e6 - rec.ts_ms
                for q in quoters:
                    q.feed_lag_ms = lag
            if rec.venue not in signal_venues:
                continue
            mid = (rec.bid + rec.ask) / 2
            if rec.venue == venue and ctx.cb_series is not None:
                ctx.cb_series.add(rx / 1e9, mid)
            vt = vticks[rec.venue]
            while vt and vt[0][0] < rx - 1_000_000_000:
                vt.popleft()
            ago = vt[0][1] if vt else None
            vt.append((rx, mid))
            if need_ctx and rec.venue == venue:
                ctx.refresh_alpha(rx)
            live = [tk for tk, b in books.items() if not b.stale]
            for q in quoters:
                if rec.venue in q.p.signal_venues:
                    q.on_tick(live, rx, mid, ago, ctx, books)
            continue
        raw = rec.raw
        if raw.get("type") == "cfbenchmarks_value" and raw["msg"].get("index_id") == index_id:
            a = raw["msg"].get("avg_60s_data")
            if a:
                end_ms = int(a["window_end_ts_exclusive"])
                avg60.append((end_ms, float(a["value"])))
                for tk_c in closing.pop(end_ms, ()):
                    K = strikes.get(tk_c)
                    if K is None:
                        continue
                    v = 1.0 if float(a["value"]) > K else 0.0
                    for q in quoters:
                        q.settle_now(tk_c, v)
            continue
        if raw.get("type") == "cfbenchmarks_value_5hz" and raw["msg"].get("index_id") == index_id:
            v = float(json.loads(raw["msg"]["data"])["value"])
            spot.on_brti(rx, v)
            if ctx.brti_series is not None:
                ctx.brti_series.add(rx / 1e9, v)
            continue
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
        if not tk.startswith(series + "-"):
            continue
        b = books.get(tk)
        if b is None:
            ct = close_time(tk)
            if ct is None:
                continue
            b = books[tk] = FastBook()
            closes[tk] = int(ct * 1e9)
            closing[closes[tk] // 1_000_000].append(tk)
        if t == "orderbook_snapshot":
            b.snapshot(msg)
            for q in quoters:
                q.on_snapshot(tk, b)
            continue
        if t == "trade":
            for q in quoters:
                q.on_trade(tk, rx, msg["ts_ms"], msg["taker_side"], parse_price(msg["yes_price_dollars"]), parse_qty(msg["count_fp"]), b)
            continue
        if b.stale:
            continue
        side, price, d = msg["side"], parse_price(msg["price_dollars"]), parse_qty(msg["delta_fp"])
        try:
            before = b.delta(side, price, d)
        except ValueError:
            b.stale = True
            continue
        for q in quoters:
            q.on_delta(tk, rx, msg.get("ts_ms", 0), side, price, before, before + d, b, closes[tk], ctx)
    # settlement: YES iff the 60s average ending at the close is above the strike
    settles: dict[str, float] = {}
    ends = [e for e, _ in avg60]
    import bisect as _bisect
    for tk, close_ns in closes.items():
        K = strikes.get(tk)
        if not K or not avg60:
            continue
        close_ms = close_ns // 1_000_000
        i = _bisect.bisect_right(ends, close_ms) - 1
        if i >= 0 and close_ms - ends[i] <= 2_000:
            settles[tk] = 1.0 if avg60[i][1] > K else 0.0
    for q in quoters:
        q.resolve(settles)
    print(f"settled {len(settles)} of {len(closes)} markets from the recorded BRTI 60s average", file=sys.stderr)
    for q in quoters:
        q.mark_unfinished(books)
    return [q.summary(test_from) for q in quoters], test_from


_F = dict(latency_ms=2, signal_move=2.0, stop_before_s=300, max_pos=200)
_G = dict(latency_ms=2, signal_move=2.0, max_pos=200)
JOIN = [
    Params("base, stop 5min", **_G, stop_before_s=300),
    Params("join gate: edge(depth) >= 0, stop 5min", **_G, stop_before_s=300, join_theta=0.0),
    Params("join gate: edge(depth) >= -0.25c, stop 5min", **_G, stop_before_s=300, join_theta=0.25),
    Params("join gate 0 + hold policy (edge<0, 300ms), stop 5min", **_G, stop_before_s=300, join_theta=0.0, edge_theta=0.0, edge_debounce_ms=300),
    Params("join gate 0 + greeks cap 5c, stop 2min", **_G, stop_before_s=120, join_theta=0.0, greeks_cap=0.05),
    Params("base, stop 2min", **_G, stop_before_s=120),
]

FAIR = [
    Params("base (2ms, cancel $2/1s, stop 5min, max pos 200)", **_G, stop_before_s=300),
    Params("fair gap presence rule, thr 3c", **_G, stop_before_s=300, fair_gap_thr=3.0),
    Params("fair gap presence rule, thr 5c", **_G, stop_before_s=300, fair_gap_thr=5.0),
    Params("fair gap join-only rule, thr 2c", **_G, stop_before_s=300, fair_gap_join=2.0),
    Params("fair gap join-only rule, thr 3c", **_G, stop_before_s=300, fair_gap_join=3.0),
    Params("fair gap join-only 3c + edge join gate 0", **_G, stop_before_s=300, fair_gap_join=3.0, join_theta=0.0),
    Params("fair gap join-only 3c, vol x1.25", **_G, stop_before_s=300, fair_gap_join=3.0, vol_mult=1.25),
]

_H = dict(latency_ms=2, stop_before_s=300, max_pos=200)
DFAIR2 = [
    Params("flat rule: spot move $2/1s", **_H, signal_move=2.0),
    Params("delta-scaled, 1s window, >= 0.25c", **_H, dfair_cancel_c=0.25, dfair_window_s=1.0),
    Params("delta-scaled, 1s window, >= 0.5c", **_H, dfair_cancel_c=0.5, dfair_window_s=1.0),
    Params("delta-scaled, 1s window, >= 0.25c, fat-tailed kernel", **_H, dfair_cancel_c=0.25, dfair_window_s=1.0, kernel="mixture"),
    Params("delta-scaled, 1s window, >= 0.5c, fat-tailed kernel", **_H, dfair_cancel_c=0.5, dfair_window_s=1.0, kernel="mixture"),
    Params("delta-scaled 1s 0.25c fat-tailed + flat $2", **_H, dfair_cancel_c=0.25, dfair_window_s=1.0, kernel="mixture", signal_move=2.0),
]

DFAIR = [
    Params("no cancel-on-signal", **_H),
    Params("flat rule: spot move $2/1s (previous base)", **_H, signal_move=2.0),
    Params("delta-scaled: cancel when fair moved >= 0.25c against quote", **_H, dfair_cancel_c=0.25),
    Params("delta-scaled: >= 0.5c", **_H, dfair_cancel_c=0.5),
    Params("delta-scaled: >= 1c", **_H, dfair_cancel_c=1.0),
    Params("delta-scaled 0.5c + flat $2/1s", **_H, dfair_cancel_c=0.5, signal_move=2.0),
    Params("delta-scaled 0.5c, BRTI spot", **_H, dfair_cancel_c=0.5, fair_spot="brti"),
]

WALK = [
    Params("base (2ms, cancel $2/1s, stop 5min, max pos 200)", **_G, stop_before_s=300),
    Params("+ join gate (edge >= 0)", **_G, stop_before_s=300, join_theta=0.0),
    Params("+ join gate + greeks cap 5c", **_G, stop_before_s=300, join_theta=0.0, greeks_cap=0.05),
    Params("base, max pos 100", latency_ms=2, signal_move=2.0, stop_before_s=300, max_pos=100),
    Params("home 40ms, no rules, stop 2min", latency_ms=40, stop_before_s=120, max_pos=200),
]

# Measured on the AWS host (2026-09-16): order -> engine 11 ms, cancel -> engine 7 ms, Kalshi engine -> us 6 ms,
# Coinbase -> us 11 ms. Laptop tape timestamps run ~15 ms fast and lag Kalshi by ~19 ms / Coinbase by ~15 ms (true),
# so in laptop-tape time: place = 6+11 = 17, cancel = 6+7 = 13, spot-triggered cancel = 11+7+(19-15) = 22.
_M = dict(signal_move=2.0, stop_before_s=300, max_pos=200, place_latency_ms=17, cancel_latency_ms=13, signal_latency_ms=22)
MEASURED = [
    Params("as simulated before (2ms all)", **_G, stop_before_s=300),
    Params("measured REST path (place 17 / cancel 13 / signal 22)", **_M),
    Params("measured + join gate", **_M, join_theta=0.0),
    Params("measured + join gate + greeks cap 5c", **_M, join_theta=0.0, greeks_cap=0.05),
    Params("measured, max pos 100", **{**_M, "max_pos": 100}),
    Params("measured +5ms everywhere", **{**_M, "place_latency_ms": 22, "cancel_latency_ms": 18, "signal_latency_ms": 27}),
    Params("FIX-like (place 8 / cancel 6 / signal 15)", **{**_M, "place_latency_ms": 8, "cancel_latency_ms": 6, "signal_latency_ms": 15}),
]

# On the AWS tape no clock-skew conversion is needed: Kalshi engine -> us 6 ms, Coinbase -> us 11 ms.
# Explicit-shard REST: place 9, cancel 5; spot-triggered cancel lands at engine C+11+5 -> tape C+22 = coinbase_rx + 11.
_A = dict(signal_move=2.0, stop_before_s=300, max_pos=200)
AWSTAPE = [
    Params("2ms all (reference)", **_A, latency_ms=2),
    Params("REST explicit shard (place 9 / cancel 5 / signal 11)", **_A, place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11),
    Params("REST explicit + join gate + greeks cap", **_A, place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11, join_theta=0.0, greeks_cap=0.05),
    Params("REST explicit, max pos 100", **{**_A, "max_pos": 100}, place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11),
    Params("FIX-like (place 5 / cancel 3 / signal 9)", **_A, place_latency_ms=5, cancel_latency_ms=3, signal_latency_ms=9),
    Params("place 3 / cancel 3 / signal 9", **_A, place_latency_ms=3, cancel_latency_ms=3, signal_latency_ms=9),
]

_R = dict(signal_move=2.0, stop_before_s=300, max_pos=200, place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11, join_theta=0.0, greeks_cap=0.05)
FEEDS = [
    Params("REST explicit + join gate + greeks cap (standing)", **_R),
    Params("+ pull quotes when Coinbase feed lag > 100ms", **_R, stale_feed_ms=100),
    Params("+ pull quotes when Coinbase feed lag > 300ms", **_R, stale_feed_ms=300),
    Params("+ pull quotes when Coinbase feed lag > 30ms", **_R, stale_feed_ms=30),
    Params("+ composite signal (coinbase|okx|bybit)", **_R, signal_venues=("coinbase", "okx", "bybit")),
    Params("+ composite signal + stale 100ms", **_R, signal_venues=("coinbase", "okx", "bybit"), stale_feed_ms=100),
    Params("+ okx-only signal", **_R, signal_venues=("okx",)),
]
FEEDS2 = [
    Params("REST explicit + join gate + greeks cap (standing)", **_R),
    Params("gemini-only signal", **_R, signal_venues=("gemini_btc",)),
    Params("coinbase|gemini signal", **_R, signal_venues=("coinbase", "gemini_btc")),
    Params("coinbase|kraken signal", **_R, signal_venues=("coinbase", "kraken")),
]

_C = dict(signal_move=2.0, stop_before_s=300, place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11, join_theta=0.0, greeks_cap=0.05)
CAPITAL = [
    Params("size 100 / max 200, unlimited capital (standing)", **_C, size=100, max_pos=200),
    Params("size 5 / max 10, $5 (what we ran)", **_C, size=5, max_pos=10, capital=5),
    Params("size 10 / max 50, $100", **_C, size=10, max_pos=50, capital=100),
    Params("size 20 / max 100, $100", **_C, size=20, max_pos=100, capital=100),
    Params("size 10 / max 50, unlimited", **_C, size=10, max_pos=50),
    Params("size 20 / max 60, $150", **_C, size=20, max_pos=60, capital=150),
    Params("size 50 / max 100, $300", **_C, size=50, max_pos=100, capital=300),
]

_I = dict(signal_move=2.0, stop_before_s=300, place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11, join_theta=0.0, greeks_cap=0.05)
INVENTORY2 = [
    Params("size 20 / max 100, $100 (live config)", **_I, size=20, max_pos=100, capital=100),
    Params("+ reduce-only exempt from greeks cap and join gate", **_I, size=20, max_pos=100, capital=100, reduce_only_exempt=True),
    Params("+ skew above 50% of cap", **_I, size=20, max_pos=100, capital=100, skew_at=0.5),
    Params("+ skew above 25% of cap", **_I, size=20, max_pos=100, capital=100, skew_at=0.25),
    Params("+ reduce-only exempt + skew 50%", **_I, size=20, max_pos=100, capital=100, reduce_only_exempt=True, skew_at=0.5),
    Params("size 100 / max 200 (standing)", **_I, size=100, max_pos=200),
    Params("size 100 / max 200 + reduce-only exempt + skew 50%", **_I, size=100, max_pos=200, reduce_only_exempt=True, skew_at=0.5),
]
FLAT = [
    Params("live config (20 / 100, $100), carry", **_I, size=20, max_pos=100, capital=100),
    Params("lean always (skew 0) + reduce-only exempt + flatten at stop, max 100", **_I, size=20, max_pos=100, capital=100, reduce_only_exempt=True, skew_at=0.0, flatten_at_stop=True),
    Params("same, max 40", **_I, size=20, max_pos=40, capital=100, reduce_only_exempt=True, skew_at=0.0, flatten_at_stop=True),
    Params("same, max 40 + take above 20", **_I, size=20, max_pos=40, capital=100, reduce_only_exempt=True, skew_at=0.0, flatten_at_stop=True, flatten_above=20),
    Params("same, max 40 + take above 40", **_I, size=20, max_pos=40, capital=100, reduce_only_exempt=True, skew_at=0.0, flatten_at_stop=True, flatten_above=40),
    Params("max 20 + take above 20 (never hold more than one quote)", **_I, size=20, max_pos=20, capital=100, reduce_only_exempt=True, skew_at=0.0, flatten_at_stop=True, flatten_above=20),
    Params("standing (100 / 200), carry", **_I, size=100, max_pos=200),
    Params("standing + lean + reduce-only + flatten at stop + take above 100", **_I, size=100, max_pos=200, reduce_only_exempt=True, skew_at=0.0, flatten_at_stop=True, flatten_above=100),
]

CAPS = [
    Params("size 20 / max 100, $100, flatten at stop", **_I, size=20, max_pos=100, capital=100, flatten_at_stop=True),
    Params("size 20 / max 60, flatten", **_I, size=20, max_pos=60, capital=100, flatten_at_stop=True),
    Params("size 20 / max 40, flatten", **_I, size=20, max_pos=40, capital=100, flatten_at_stop=True),
    Params("size 20 / max 20, flatten", **_I, size=20, max_pos=20, capital=100, flatten_at_stop=True),
    Params("size 10 / max 20, flatten", **_I, size=10, max_pos=20, capital=100, flatten_at_stop=True),
    Params("size 10 / max 40, flatten", **_I, size=10, max_pos=40, capital=100, flatten_at_stop=True),
    Params("size 20 / max 40, flatten + take above 80 (rare backstop)", **_I, size=20, max_pos=40, capital=100, flatten_at_stop=True, flatten_above=80),
    Params("size 100 / max 200, flatten", **_I, size=100, max_pos=200, flatten_at_stop=True),
    Params("size 100 / max 100, flatten", **_I, size=100, max_pos=100, flatten_at_stop=True),
]

SIZESKEW = [
    Params("size 20 / max 20, flatten (live)", **_I, size=20, max_pos=20, capital=100, flatten_at_stop=True),
    Params("size 20 / max 40, flatten", **_I, size=20, max_pos=40, capital=100, flatten_at_stop=True),
    Params("size 20 / max 40, flatten + size skew", **_I, size=20, max_pos=40, capital=100, flatten_at_stop=True, size_skew=True),
    Params("size 20 / max 60, flatten + size skew", **_I, size=20, max_pos=60, capital=100, flatten_at_stop=True, size_skew=True),
    Params("size 20 / max 100, flatten + size skew", **_I, size=20, max_pos=100, capital=100, flatten_at_stop=True, size_skew=True),
    Params("size 10 / max 40, flatten + size skew", **_I, size=10, max_pos=40, capital=100, flatten_at_stop=True, size_skew=True),
    Params("size 100 / max 200, flatten + size skew", **_I, size=100, max_pos=200, flatten_at_stop=True, size_skew=True),
]

_Q = dict(signal_move=2.0, stop_before_s=300, join_theta=0.0, greeks_cap=0.05, size=20, max_pos=20, capital=100, flatten_at_stop=True)
# Corrected model: price-priority fills, engine lag in tape time, tapered ticks, settlement. Explicit-shard REST latencies.
_M2 = dict(signal_move=2.0, stop_before_s=300, join_theta=0.0, greeks_cap=0.05, price_priority=True, engine_lag_ms=6.0,
           place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11)
EVAL = [
    Params("live 20/20 $100 flatten (baseline)", **_M2, size=20, max_pos=20, capital=100, flatten_at_stop=True),
    Params("live 20/20, carry to settlement", **_M2, size=20, max_pos=20, capital=100),
    Params("A1 persistence: min rest 1s, reprice >= 2 ticks", **_M2, size=20, max_pos=20, capital=100, flatten_at_stop=True, min_rest_ms=1000, reprice_ticks=2),
    Params("A2 join gate: level age >= 1s", **_M2, size=20, max_pos=20, capital=100, flatten_at_stop=True, min_level_age_ms=1000),
    Params("A3 join gate: level age >= 1s + min depth 300", **_M2, size=20, max_pos=20, capital=100, flatten_at_stop=True, min_level_age_ms=1000, min_depth=300),
    Params("A4 persistence + level age 1s + depth 300", **_M2, size=20, max_pos=20, capital=100, flatten_at_stop=True, min_rest_ms=1000, reprice_ticks=2, min_level_age_ms=1000, min_depth=300),
    Params("C  pre-position 1 tick behind the touch", **_M2, size=20, max_pos=20, capital=100, flatten_at_stop=True, offset_ticks=1),
    Params("C2 pre-position 1 tick + persistence", **_M2, size=20, max_pos=20, capital=100, flatten_at_stop=True, offset_ticks=1, min_rest_ms=1000, reprice_ticks=2),
    Params("D  cap 40 + size skew + flatten", **_M2, size=20, max_pos=40, capital=100, flatten_at_stop=True, size_skew=True),
    Params("D2 cap 40 + size skew + A4", **_M2, size=20, max_pos=40, capital=100, flatten_at_stop=True, size_skew=True, min_rest_ms=1000, reprice_ticks=2, min_level_age_ms=1000, min_depth=300),
    Params("standing 100/200 flatten", **_M2, size=100, max_pos=200, flatten_at_stop=True),
    Params("standing 100/200 + A4", **_M2, size=100, max_pos=200, flatten_at_stop=True, min_rest_ms=1000, reprice_ticks=2, min_level_age_ms=1000, min_depth=300),
    Params("standing, no gates, flatten (raw touch quoter)", **{**_M2, "join_theta": None, "greeks_cap": None}, size=100, max_pos=200, flatten_at_stop=True),
]

# neighbourhood of A3 (the only EVAL config positive on both days): is it a knife-edge?
_A3 = dict(**_M2, size=20, max_pos=20, capital=100, flatten_at_stop=True)
EVAL2 = [
    Params("A3 level age 1s + depth 300 (reference)", **_A3, min_level_age_ms=1000, min_depth=300),
    Params("depth 300 only", **_A3, min_depth=300),
    Params("depth 200 only", **_A3, min_depth=200),
    Params("depth 500 only", **_A3, min_depth=500),
    Params("level age 0.5s + depth 300", **_A3, min_level_age_ms=500, min_depth=300),
    Params("level age 2s + depth 300", **_A3, min_level_age_ms=2000, min_depth=300),
    Params("level age 1s + depth 200", **_A3, min_level_age_ms=1000, min_depth=200),
    Params("level age 1s + depth 500", **_A3, min_level_age_ms=1000, min_depth=500),
    Params("A3 + offset 1 tick", **_A3, min_level_age_ms=1000, min_depth=300, offset_ticks=1),
    Params("A3 + cap 40 size skew", **{**_A3, "max_pos": 40}, min_level_age_ms=1000, min_depth=300, size_skew=True),
    Params("A3 + imbalance 0.33", **_A3, min_level_age_ms=1000, min_depth=300, imb_thr=0.33),
    Params("A3, size 10", **{**_A3, "size": 10, "max_pos": 10}, min_level_age_ms=1000, min_depth=300),
    Params("A3, carry to settlement", **{**_A3, "flatten_at_stop": False}, min_level_age_ms=1000, min_depth=300),
]

# depth gate alone was monotone 200 < 300 < 500: where does it turn over?
EVAL3 = [
    Params("depth 500 only (reference)", **_A3, min_depth=500),
    Params("depth 750 only", **_A3, min_depth=750),
    Params("depth 1000 only", **_A3, min_depth=1000),
    Params("depth 1500 only", **_A3, min_depth=1500),
    Params("depth 2000 only", **_A3, min_depth=2000),
    Params("depth 500 + imbalance 0.33", **_A3, min_depth=500, imb_thr=0.33),
    Params("depth 1000 + imbalance 0.33", **_A3, min_depth=1000, imb_thr=0.33),
    Params("depth 500 + cap 40 size skew", **{**_A3, "max_pos": 40}, min_depth=500, size_skew=True),
    Params("depth 1000 + cap 40 size skew", **{**_A3, "max_pos": 40}, min_depth=1000, size_skew=True),
    Params("depth 500, size 50 / cap 50", **{**_A3, "size": 50, "max_pos": 50}, min_depth=500),
    Params("depth 1000, size 50 / cap 50", **{**_A3, "size": 50, "max_pos": 50}, min_depth=1000),
]

# depth 1000: how does the edge scale with size (cap = size; $100 capital unless noted)?
_D = dict(**_M2, flatten_at_stop=True, min_depth=1000)
SIZES = [
    *[Params(f"depth 1000, size {n}, {q}", **_D, size=n, max_pos=n, capital=100, queue=q) for q in ("prorata", "pessimistic") for n in (5, 10, 20, 50, 100)],
    *[Params(f"depth 1000, size {n}, {q}, unlimited capital", **_D, size=n, max_pos=n, queue=q) for q in ("prorata", "pessimistic") for n in (100, 200, 500)],
    *[Params(f"depth 1000, size {n} / cap {2*n}, {q}, unlimited capital", **_D, size=n, max_pos=2*n, queue=q) for q in ("prorata", "pessimistic") for n in (50, 100)],
]

# KXETH15M under the corrected model: no BTC-fitted join tables, touch ~80 contracts so depth gates are scaled down
_E = dict(signal_move=2.0, stop_before_s=300, greeks_cap=0.05, price_priority=True, engine_lag_ms=6.0,
          place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11, size=20, max_pos=20, capital=100, flatten_at_stop=True)
ETHSET = [
    Params("ETH touch joiner, greeks cap, signal cancel", **_E),
    Params("ETH no gates at all", **{**_E, "greeks_cap": None, "signal_move": None}),
    Params("ETH signal cancel $20/1s (ETH scale)", **{**_E, "signal_move": 20.0}),
    Params("ETH depth >= 50", **_E, min_depth=50),
    Params("ETH depth >= 100", **_E, min_depth=100),
    Params("ETH depth >= 200", **_E, min_depth=200),
    Params("ETH size 5 / cap 5", **{**_E, "size": 5, "max_pos": 5}),
    Params("ETH size 50 / cap 50", **{**_E, "size": 50, "max_pos": 50}),
    Params("ETH touch joiner, pessimistic queue", **_E, queue="pessimistic"),
    Params("ETH depth >= 100, pessimistic queue", **_E, min_depth=100, queue="pessimistic"),
]

# Non-crypto series from the exchange-wide survey: no spot signal, no strike, linear grid, many concurrent markets.
_NC = dict(stop_before_s=300, price_priority=True, engine_lag_ms=6.0, place_latency_ms=9, cancel_latency_ms=5,
           size=20, max_pos=20, capital=500, global_capital=True, flatten_at_stop=True)
NONCRYPTO = [
    Params("touch joiner", **_NC),
    Params("touch joiner, size 5", **{**_NC, "size": 5, "max_pos": 5}),
    Params("touch joiner, depth >= 50", **_NC, min_depth=50),
    Params("join only, never improve", **_NC, no_improve=True),
    Params("touch joiner, pessimistic queue", **_NC, queue="pessimistic"),
    Params("touch joiner, carry (no flatten)", **{**_NC, "flatten_at_stop": False}),
]

# in-play sports: the spread is the market's event detector
INPLAY = [
    Params("touch joiner (baseline)", **_NC),
    Params("no improve when spread > 2 ticks", **_NC, wide_spread_ticks=2),
    Params("no improve when spread > 1 tick (join only)", **_NC, no_improve=True),
    Params("pull when spread > 3 ticks", **_NC, wide_spread_ticks=3, wide_spread_pull=True),
    Params("pull when spread > 2 ticks", **_NC, wide_spread_ticks=2, wide_spread_pull=True),
    Params("pause 10 s after a 5c jump", **_NC, post_jump_pause_s=10),
    Params("pause 30 s after a 5c jump", **_NC, post_jump_pause_s=30),
    Params("join only + pause 10 s", **_NC, no_improve=True, post_jump_pause_s=10),
    Params("pull > 2 ticks + pause 10 s", **_NC, wide_spread_ticks=2, wide_spread_pull=True, post_jump_pause_s=10),
    Params("pull > 2 ticks + pause 10 s, size 5", **{**_NC, "size": 5, "max_pos": 5}, wide_spread_ticks=2, wide_spread_pull=True, post_jump_pause_s=10),
]

# KXBTCD: hourly-settling strips of strikes, each alive ~25 h. Quote all strikes closing within max_ttx_h; capital shared.
_HR = dict(signal_move=2.0, stop_before_s=300, greeks_cap=0.05, price_priority=True, engine_lag_ms=6.0,
           place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11, size=20, max_pos=20, capital=300, global_capital=True, flatten_at_stop=True)
HOURLY = [
    Params("hourly: all strikes, ttx <= 1 h", **_HR, max_ttx_h=1),
    Params("hourly: all strikes, ttx <= 3 h", **_HR, max_ttx_h=3),
    Params("hourly: ttx <= 3 h, no signal cancel", **{**_HR, "signal_move": None}, max_ttx_h=3),
    Params("hourly: ttx <= 3 h, no gates", **{**_HR, "signal_move": None, "greeks_cap": None}, max_ttx_h=3),
    Params("hourly: ttx <= 3 h, carry to settlement", **{**_HR, "flatten_at_stop": False}, max_ttx_h=3),
    Params("hourly: ttx <= 3 h, size 5", **{**_HR, "size": 5, "max_pos": 5}, max_ttx_h=3),
    Params("hourly: ttx <= 3 h, pessimistic queue", **_HR, max_ttx_h=3, queue="pessimistic"),
]

# only rest on prices that have already been the touch for a while (the benign class in the age table)
_O = dict(signal_move=2.0, stop_before_s=300, greeks_cap=0.05, price_priority=True, engine_lag_ms=6.0,
          place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11, size=20, max_pos=20, capital=100, flatten_at_stop=True)
OLD = [
    Params("baseline touch joiner", **_O),
    Params("touch age >= 50 ms", **_O, min_touch_age_ms=50, no_improve=True),
    Params("touch age >= 200 ms", **_O, min_touch_age_ms=200, no_improve=True),
    Params("touch age >= 500 ms", **_O, min_touch_age_ms=500, no_improve=True),
    Params("touch age >= 1000 ms", **_O, min_touch_age_ms=1000, no_improve=True),
    Params("touch age >= 200 ms, improves allowed", **_O, min_touch_age_ms=200),
    Params("touch age >= 200 ms + depth gate", **_O, min_touch_age_ms=200, no_improve=True, min_depth=100),
    Params("touch age >= 200 ms, size 5", **{**_O, "size": 5, "max_pos": 5}, min_touch_age_ms=200, no_improve=True),
    Params("touch age >= 200 ms, pessimistic queue", **_O, min_touch_age_ms=200, no_improve=True, queue="pessimistic"),
]

# where do our fills come from, and which kinds pay? (per-fill diagnostics printed with the table)
_D2 = dict(signal_move=2.0, stop_before_s=300, greeks_cap=0.05, price_priority=True, engine_lag_ms=6.0,
           place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11, size=20, max_pos=20, capital=100, flatten_at_stop=True)
DIAG = [
    Params("touch joiner (baseline, no join tables)", **_D2),
    Params("join only, never improve", **_D2, no_improve=True),
    Params("improve only, never join", **_D2, improve_only=True),
    Params("pre-position 1 tick behind", **_D2, offset_ticks=1),
    Params("persistence: min rest 1 s, reprice >= 2 ticks", **_D2, min_rest_ms=1000, reprice_ticks=2),
]

# hindsight / learned presence policies via external veto intervals (research/veto_*.parquet)
_V = dict(signal_move=2.0, stop_before_s=300, join_theta=0.0, greeks_cap=0.05, price_priority=True, engine_lag_ms=6.0,
          place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11, size=20, max_pos=20, capital=100, flatten_at_stop=True)
def _veto_set(day: str, series: str = "KXBTC15M") -> list:
    import os
    R = "../research/" + ("" if series == "KXBTC15M" else f"{series}_")
    base = dict(_V) if series == "KXBTC15M" else {**_V, "join_theta": None}   # no ETH edge tables
    out = [
        Params("baseline", **base),
        Params("oracle: dodge every sweep-through, 50 ms warning", **_V, veto_file=f"{R}veto_oracle50_{day}.parquet"),
        Params("oracle: dodge every sweep-through, 250 ms warning", **_V, veto_file=f"{R}veto_oracle250_{day}.parquet"),
        Params("oracle: dodge every sweep-through, 1 s warning", **_V, veto_file=f"{R}veto_oracle1000_{day}.parquet"),
        Params("oracle: dodge adverse fills only (mo30 < 0), 250 ms", **_V, veto_file=f"{R}veto_oracleadv250_{day}.parquet"),
        Params("learned: vacate model p>0.5 @250 ms (walk-forward)", **_V, veto_file=f"{R}veto_model50_{day}.parquet"),
        Params("learned: vacate model p>0.3 @250 ms", **_V, veto_file=f"{R}veto_model30_{day}.parquet"),
        Params("learned: vacate model p>0.7 @250 ms", **_V, veto_file=f"{R}veto_model70_{day}.parquet"),
    ]
    out = [o for o in out if o.veto_file is None or os.path.exists(o.veto_file)]
    for o in out:
        if series != "KXBTC15M":
            o.join_theta = None
    return out

# spot-triggered improve: post-only at the vacating touch on the spot trigger (first at the new level)
_S = dict(stop_before_s=300, join_theta=0.0, greeks_cap=0.05, price_priority=True, engine_lag_ms=6.0,
          place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11, size=20, max_pos=20, capital=100, flatten_at_stop=True)
SIGIMP = [
    Params("baseline (signal cancel $2/1s)", **_S, signal_move=2.0),
    Params("signal improve $2/1s, hold 2 s", **_S, signal_move=2.0, signal_improve=True),
    Params("signal improve $2/1s, hold 0.5 s", **_S, signal_move=2.0, signal_improve=True, signal_hold_ms=500),
    Params("signal improve $2/1s, hold 5 s", **_S, signal_move=2.0, signal_improve=True, signal_hold_ms=5000),
    Params("signal improve $3/1s, hold 2 s", **_S, signal_move=3.0, signal_improve=True),
    Params("signal improve $5/1s, hold 2 s", **_S, signal_move=5.0, signal_improve=True),
    Params("signal improve $2/1s, hold 2 s, no join gate", **{**_S, "join_theta": None}, signal_move=2.0, signal_improve=True),
    Params("signal improve $2/1s, hold 2 s, pessimistic queue", **_S, signal_move=2.0, signal_improve=True, queue="pessimistic"),
    Params("signal improve $2/1s, hold 2 s, FIX-like 5/3/9", **{**_S, "place_latency_ms": 5, "cancel_latency_ms": 3, "signal_latency_ms": 9}, signal_move=2.0, signal_improve=True),
    Params("signal improve $2/1s, hold 2 s, size 50", **{**_S, "size": 50, "max_pos": 50}, signal_move=2.0, signal_improve=True),
]

# what is latency worth under the corrected model? (engine lag 6 ms is physical; the 0 ms rows show the feed's share)
_L = dict(signal_move=2.0, stop_before_s=300, join_theta=0.0, greeks_cap=0.05, price_priority=True, size=20, max_pos=20, capital=100, flatten_at_stop=True)
LATENCY2 = [
    *[Params(f"place {pl} / cancel {c} / signal {sg}, engine lag 6", **_L, engine_lag_ms=6.0, place_latency_ms=pl, cancel_latency_ms=c, signal_latency_ms=sg)
      for pl, c, sg in ((9, 5, 11), (5, 3, 11), (3, 3, 11), (2, 2, 11), (2, 2, 2), (1, 1, 1))],
    *[Params(f"place {pl} / cancel {c} / signal {sg}, engine lag 0 (hypothetical)", **_L, engine_lag_ms=0.0, place_latency_ms=pl, cancel_latency_ms=c, signal_latency_ms=sg)
      for pl, c, sg in ((9, 5, 11), (2, 2, 2))],
    *[Params(f"place {pl} / cancel {c} / signal {sg}, engine lag 6, pessimistic queue", **_L, engine_lag_ms=6.0, place_latency_ms=pl, cancel_latency_ms=c, signal_latency_ms=sg, queue="pessimistic")
      for pl, c, sg in ((9, 5, 11), (2, 2, 11))],
]

# the depth gate joins behind 1000+ contracts: does its edge survive the queue model nobody has measured?
EVAL4 = [
    Params("baseline, prorata queue", **_A3),
    Params("baseline, pessimistic queue", **_A3, queue="pessimistic"),
    Params("depth 500, pessimistic queue", **_A3, min_depth=500, queue="pessimistic"),
    Params("depth 1000, pessimistic queue", **_A3, min_depth=1000, queue="pessimistic"),
    Params("depth 1500, pessimistic queue", **_A3, min_depth=1500, queue="pessimistic"),
    Params("depth 1000, pessimistic, size 50 / cap 50", **{**_A3, "size": 50, "max_pos": 50}, min_depth=1000, queue="pessimistic"),
]

PRIORITY = [
    Params("live config, prorata, 9/5/11 (old model)", **_Q, queue="prorata", place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11),
    Params("live config, prorata + price priority", **_Q, queue="prorata", place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11, price_priority=True),
    Params("live config, FIFO + price priority", **_Q, queue="pessimistic", place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11, price_priority=True),
    Params("standing 100/200, prorata + price priority", **{**_Q, "size": 100, "max_pos": 200, "capital": None}, queue="prorata", place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11, price_priority=True),
    Params("standing 100/200, prorata + price priority, 2/2/2", **{**_Q, "size": 100, "max_pos": 200, "capital": None}, queue="prorata", place_latency_ms=2, cancel_latency_ms=2, signal_latency_ms=2, price_priority=True),
]

QUEUE = [
    Params("live config, prorata queue, place 9 / cancel 5 / signal 11", **_Q, queue="prorata", place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11),
    Params("live config, FIFO queue (cancels from behind), 9/5/11", **_Q, queue="pessimistic", place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11),
    Params("FIFO, 2/2/2 (no engine latency)", **_Q, queue="pessimistic", place_latency_ms=2, cancel_latency_ms=2, signal_latency_ms=2),
    Params("FIFO, 5/3/8 (FIX-like)", **_Q, queue="pessimistic", place_latency_ms=5, cancel_latency_ms=3, signal_latency_ms=8),
    Params("FIFO, 17/13/22 (auto-routed REST)", **_Q, queue="pessimistic", place_latency_ms=17, cancel_latency_ms=13, signal_latency_ms=22),
    Params("FIFO, 9/5/11, cap 40 + size skew", **{**_Q, "max_pos": 40}, queue="pessimistic", place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11, size_skew=True),
    Params("FIFO, 9/5/11, standing size 100 / max 200", **{**_Q, "size": 100, "max_pos": 200, "capital": None}, queue="pessimistic", place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11),
    Params("FIFO, 9/5/11, standing, no join gate/greeks", **{**_Q, "size": 100, "max_pos": 200, "capital": None, "join_theta": None, "greeks_cap": None}, queue="pessimistic", place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11),
]

FLATTEN = [
    Params("live config (size 20 / max 100, $100), carry to settlement", **_I, size=20, max_pos=100, capital=100),
    Params("+ flatten at stop (take the touch)", **_I, size=20, max_pos=100, capital=100, flatten_at_stop=True),
    Params("+ reduce-only exempt + flatten", **_I, size=20, max_pos=100, capital=100, reduce_only_exempt=True, flatten_at_stop=True),
    Params("+ reduce-only exempt + skew 50% + flatten", **_I, size=20, max_pos=100, capital=100, reduce_only_exempt=True, skew_at=0.5, flatten_at_stop=True),
    Params("+ reduce-only + skew 50% + flatten, stop 3min", **{**_I, "stop_before_s": 180}, size=20, max_pos=100, capital=100, reduce_only_exempt=True, skew_at=0.5, flatten_at_stop=True),
    Params("standing (size 100 / max 200), carry", **_I, size=100, max_pos=200),
    Params("standing + reduce-only + skew 50% + flatten", **_I, size=100, max_pos=200, reduce_only_exempt=True, skew_at=0.5, flatten_at_stop=True),
]

LATSWEEP = [
    Params(f"place {a} / cancel {b} / signal {c}", **{**_M, "place_latency_ms": a, "cancel_latency_ms": b, "signal_latency_ms": c})
    for a, b, c in ((2, 2, 2), (3, 3, 6), (5, 4, 8), (5, 4, 15), (8, 6, 8), (8, 6, 15), (11, 7, 18), (17, 13, 22))
]

PERMKT = [
    Params("base (2ms, cancel $2/1s, stop 5min, max pos 200)", **_G, stop_before_s=300),
    Params("base, max pos 100", latency_ms=2, signal_move=2.0, stop_before_s=300, max_pos=100),
]

PROBE = [
    Params("probe prorata (2ms, cancel $2/1s, stop 5min, max pos 200)", **_F),
    Params("probe pessimistic", **_F, queue="pessimistic"),
    Params("probe live config prorata 9/5/11", **_Q, queue="prorata", place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11),
    Params("probe live config FIFO 9/5/11", **_Q, queue="pessimistic", place_latency_ms=9, cancel_latency_ms=5, signal_latency_ms=11),
]

VALUE_OOS = [
    Params("base (2ms, cancel $2/1s, stop 5min, max pos 200)", **_F),
    Params("value policy: cancel if edge < 0, debounce 300ms", **_F, edge_theta=0.0, edge_debounce_ms=300),
    Params("value policy: cancel if edge < 0, no debounce", **_F, edge_theta=0.0),
]

VALUE = [
    Params("base (2ms, cancel $2/1s, stop 5min, max pos 200)", **_F),
    Params("value policy: cancel if edge < 0, no debounce", **_F, edge_theta=0.0),
    Params("value policy: cancel if edge < 0, debounce 300ms", **_F, edge_theta=0.0, edge_debounce_ms=300),
    Params("value policy: cancel if edge < -0.25c, debounce 300ms", **_F, edge_theta=0.25, edge_debounce_ms=300),
    Params("value policy: cancel if edge < -0.5c, debounce 300ms", **_F, edge_theta=0.5, edge_debounce_ms=300),
    Params("value policy: cancel if edge < -0.25c, debounce 1s", **_F, edge_theta=0.25, edge_debounce_ms=1000),
    Params("value policy -0.25c/300ms + greeks cap 5c", **_F, edge_theta=0.25, edge_debounce_ms=300, greeks_cap=0.05),
]

FILTERS2 = [
    Params("base (2ms, cancel $2/1s, stop 5min, max pos 200)", **_F),
    Params("mild: alpha $3", **_F, alpha_thr=3.0),
    Params("mild: imbalance 0.6", **_F, imb_thr=0.6),
    Params("mild: thin 100", **_F, min_depth=100),
    Params("mild: alpha $3 + imb 0.6 + thin 100 + greeks 5c", **_F, alpha_thr=3.0, imb_thr=0.6, min_depth=100, greeks_cap=0.05),
    Params("queue-aware: alpha $1 + imb 0.33, keep if ahead<200", **_F, alpha_thr=1.0, imb_thr=0.33, keep_if_ahead_lt=200),
    Params("queue-aware: alpha $1 + imb 0.33 + thin 500, keep<200", **_F, alpha_thr=1.0, imb_thr=0.33, min_depth=500, keep_if_ahead_lt=200),
    Params("queue-aware: all five, keep if ahead<200", **_F, alpha_thr=1.0, greeks_cap=0.05, min_depth=500, imb_thr=0.33, cluster_ms=2000, keep_if_ahead_lt=200),
    Params("queue-aware: all five, keep if ahead<500", **_F, alpha_thr=1.0, greeks_cap=0.05, min_depth=500, imb_thr=0.33, cluster_ms=2000, keep_if_ahead_lt=500),
]

FILTERS = [
    Params("base (2ms, cancel $2/1s, stop 5min, max pos 200)", **_F),
    Params("+ alpha filter $0.5", **_F, alpha_thr=0.5),
    Params("+ alpha filter $1", **_F, alpha_thr=1.0),
    Params("+ greeks cap 5c", **_F, greeks_cap=0.05),
    Params("+ thin touch veto (<500)", **_F, min_depth=500),
    Params("+ imbalance veto (0.33)", **_F, imb_thr=0.33),
    Params("+ cluster veto 2s", **_F, cluster_ms=2000),
    Params("all: alpha $1 + greeks 5c + thin 500 + imb 0.33 + cluster 2s", **_F, alpha_thr=1.0, greeks_cap=0.05, min_depth=500, imb_thr=0.33, cluster_ms=2000),
    Params("all but thin", **_F, alpha_thr=1.0, greeks_cap=0.05, imb_thr=0.33, cluster_ms=2000),
]

INVENTORY = [
    Params(f"max pos {mp}, 2ms, cancel $2/1s, stop 5min", latency_ms=2, signal_move=2.0, stop_before_s=300, max_pos=mp)
    for mp in (100, 150, 200, 300, 500, 1000)
]

SWEEP = [
    *[Params(f"latency {l}ms, cancel $2/1s, stop 5min", latency_ms=l, signal_move=2.0, stop_before_s=300) for l in (1, 2, 5, 10, 20, 40, 80)],
    *[Params(f"size {sz}, 2ms, cancel $2/1s, stop 5min", latency_ms=2, signal_move=2.0, stop_before_s=300, size=sz, max_pos=5 * sz) for sz in (50, 200, 500, 1000)],
]

CONFIGS = [
    Params("home 40ms, no signal", latency_ms=40),
    Params("aws 2ms, no signal", latency_ms=2),
    Params("aws 2ms, cancel on $2/1s", latency_ms=2, signal_move=2.0),
    Params("aws 2ms, cancel on $2/1s, pessimistic queue", latency_ms=2, signal_move=2.0, queue="pessimistic"),
    Params("aws 2ms, cancel on $2/1s, size 20", latency_ms=2, signal_move=2.0, size=20),
    Params("aws 2ms, cancel on $5/1s", latency_ms=2, signal_move=5.0),
    Params("aws 2ms, cancel on $2/1s, stop 5min", latency_ms=2, signal_move=2.0, stop_before_s=300),
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, default=Path("../data"))
    ap.add_argument("--series", default="KXBTC15M")
    ap.add_argument("--venue", default="coinbase")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--sweep", action="store_true", help="run the latency/size sweep instead of the base configs")
    ap.add_argument("--inventory", action="store_true", help="run the position-limit sweep")
    ap.add_argument("--filters", action="store_true", help="run the adverse-selection filter study (needs research/alpha_<day>.parquet)")
    ap.add_argument("--filters2", action="store_true", help="milder and queue-aware filter variants")
    ap.add_argument("--value", action="store_true", help="value-function hold/cancel policy study")
    ap.add_argument("--value-oos", action="store_true", help="value policy, out-of-sample split reported")
    ap.add_argument("--probe", action="store_true", help="measure queue advancement and time-to-fill of our orders")
    ap.add_argument("--join", action="store_true", help="join-gating study")
    ap.add_argument("--fair", action="store_true", help="fair-value gap rules study")
    ap.add_argument("--dfair", action="store_true", help="delta-scaled repricing study")
    ap.add_argument("--dfair2", action="store_true", help="delta-scaled repricing, 1s window and fat-tailed kernel")
    ap.add_argument("--tables-from", type=date.fromisoformat, default=None, help="fit alpha/edge tables on this day's sweep dataset instead of the run day (walk-forward)")
    ap.add_argument("--walk", action="store_true", help="walk-forward config set")
    ap.add_argument("--per-market", type=Path, default=None, help="run PERMKT configs and write per-market P&L rows to this parquet")
    ap.add_argument("--measured", action="store_true", help="measured AWS order-entry latencies")
    ap.add_argument("--latsweep", action="store_true", help="sweep place/cancel/signal latency combinations")
    ap.add_argument("--awstape", action="store_true", help="measured latencies for the AWS-recorded tape (no clock-skew conversion)")
    ap.add_argument("--feeds", action="store_true", help="stale-feed veto and composite-signal study (AWS tape)")
    ap.add_argument("--feeds2", action="store_true", help="gemini / kraken as cancel-signal venues")
    ap.add_argument("--capital", action="store_true", help="capital-constrained sizing study (AWS tape)")
    ap.add_argument("--inventory2", action="store_true", help="reduce-only exemption and inventory skew (AWS tape)")
    ap.add_argument("--flatten", action="store_true", help="flatten at the endgame stop vs carry to settlement (AWS tape)")
    ap.add_argument("--flat", action="store_true", help="stay-flat policies: lean, tight cap, take to flatten (AWS tape)")
    ap.add_argument("--caps", action="store_true", help="position cap sweep with flatten at stop (AWS tape)")
    ap.add_argument("--sizeskew", action="store_true", help="A-S by quote size: shrink the increasing side, grow the reducing side (AWS tape)")
    ap.add_argument("--queue", action="store_true", help="queue model (prorata vs FIFO) and latency under FIFO (AWS tape)")
    ap.add_argument("--priority", action="store_true", help="price-priority fills from multi-level sweeps (AWS tape)")
    ap.add_argument("--eval", action="store_true", help="post-audit evaluation set under the corrected model (AWS tape)")
    ap.add_argument("--eval2", action="store_true", help="neighbourhood of the EVAL winner (A3)")
    ap.add_argument("--eval3", action="store_true", help="depth-gate threshold sweep")
    ap.add_argument("--eval4", action="store_true", help="depth gate under the pessimistic (no advancement) queue")
    ap.add_argument("--baseline", action="store_true", help="the live/paper configuration only (for paper_vs_sim)")
    ap.add_argument("--inplay", action="store_true", help="in-play sports rule set")
    ap.add_argument("--noncrypto", action="store_true", help="non-crypto configuration set (use --series <series>, --no-spot)")
    ap.add_argument("--fills-out", type=Path, default=None, help="write every fill of the FIRST config to this parquet")
    ap.add_argument("--warm-days", type=int, default=0, help="rebuild books from this many earlier days first (broad tape)")
    ap.add_argument("--no-spot", action="store_true", help="do not merge the spot feeds (series with no spot reference)")
    ap.add_argument("--hourly", action="store_true", help="KXBTCD configuration set (use --series KXBTCD)")
    ap.add_argument("--chunk", type=str, default=None, help="i/n: run the i-th of n slices of the chosen config set (memory)")
    ap.add_argument("--old", action="store_true", help="quote only established touch prices")
    ap.add_argument("--diag", action="store_true", help="fill-source diagnostics set (any series)")
    ap.add_argument("--eth", action="store_true", help="KXETH15M configuration set (use --series KXETH15M)")
    ap.add_argument("--eth-part", type=int, default=0, help="1 or 2: run half of the ETH set (memory)")
    ap.add_argument("--veto", action="store_true", help="hindsight and learned presence policies (needs research/veto_*.parquet for the day)")
    ap.add_argument("--sigimp", action="store_true", help="spot-triggered improve study")
    ap.add_argument("--latency2", action="store_true", help="latency sweep under the corrected model")
    ap.add_argument("--sizes", action="store_true", help="depth 1000 size sweep under both queue models")
    ap.add_argument("--depth1000", action="store_true", help="the paper configuration from 2026-09-17 16:22 UTC: baseline + min depth 1000")
    a = ap.parse_args()
    configs = SWEEP if a.sweep else INVENTORY if a.inventory else FILTERS if a.filters else FILTERS2 if a.filters2 else VALUE if a.value else VALUE_OOS if a.value_oos else PROBE if a.probe else JOIN if a.join else FAIR if a.fair else DFAIR if a.dfair else DFAIR2 if a.dfair2 else WALK if a.walk else MEASURED if a.measured else LATSWEEP if a.latsweep else AWSTAPE if a.awstape else FEEDS if a.feeds else FEEDS2 if a.feeds2 else CAPITAL if a.capital else INVENTORY2 if a.inventory2 else FLATTEN if a.flatten else FLAT if a.flat else CAPS if a.caps else SIZESKEW if a.sizeskew else QUEUE if a.queue else PRIORITY if a.priority else EVAL if a.eval else EVAL2 if a.eval2 else EVAL3 if a.eval3 else EVAL4 if a.eval4 else INPLAY if a.inplay else NONCRYPTO if a.noncrypto else HOURLY if a.hourly else OLD if a.old else DIAG if a.diag else (ETHSET if a.eth_part == 0 else ETHSET[:5] if a.eth_part == 1 else ETHSET[5:]) if a.eth else _veto_set(str(a.day), a.series) if a.veto else SIGIMP if a.sigimp else LATENCY2 if a.latency2 else SIZES if a.sizes else EVAL[:1] if a.baseline else [Params("depth 1000 only", **_A3, min_depth=1000)] if a.depth1000 else PERMKT if a.per_market else CONFIGS
    if a.chunk:
        i, n = (int(x) for x in a.chunk.split("/"))
        per = -(-len(configs) // n)
        configs = configs[(i - 1) * per:i * per]
    def checkpoint(partial):
        if not a.out:
            return
        rows = [f"# PARTIAL — {a.series} {a.day}, markets completed so far", "", "| config | markets | pnl_$ | pnl_per_market_$ | t_stat | contracts | fill_markout_30s_c |", "|---|---|---|---|---|---|---|"]
        for r in partial:
            if r.get("markets", 0) == 0:
                rows.append(f"| {r['name']} | 0 | | | | | |")
                continue
            rows.append(f"| {r['name']} | {r['markets']} | {r['pnl_$']:.2f} | {r['pnl_per_market_$']:.2f} | {r['t_stat']:.2f} | {r['contracts']:,.0f} | {r['fill_markout_30s_c']:.2f} |")
        Path(str(a.out) + ".partial.md").write_text("\n".join(rows))

    if a.fills_out:
        _fill_sink: list = []
        _orig_init = Quoter.__init__
        def _patched(self, p, _o=_orig_init):
            _o(self, p)
            if p is configs[0]:
                self.fill_log = _fill_sink
        Quoter.__init__ = _patched
    res, test_from = run(a.data_dir, a.day, a.series, a.venue, configs, Path("../research") / f"alpha_{a.tables_from or a.day}.parquet",
                         train_frac=1.0 if a.tables_from else 0.6, checkpoint=checkpoint, no_spot=a.no_spot, warm_days=a.warm_days)
    cols = ["markets", "pnl_$", "spread_$", "inventory_$", "adverse_10s_$", "test_markets", "test_pnl_$", "test_spread_$", "test_inventory_$", "realized_$", "unrealized_$", "pnl_per_market_$", "pnl_sd_$", "t_stat", "worst_$", "contracts", "pnl_c_per_contract", "fill_markout_30s_c", "improved_fill_%", "fill_share_%", "fills", "avg_max_pos", "end_pos_abs", "flatten_cost_$"]
    L = [f"# Quoter simulation, {a.series}, {a.day}", "",
         "Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. "
         "No market impact. See `python/kalshi_data/research/sim.py`.", "",
         "| config | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 1)]
    if a.probe or a.eval4:
        for r in res:
            print(f"{r['name']}: advance {r['probe_advance_per_s']:.0f} contracts/s | ahead at placement p50 {r['probe_ahead_at_place_p50']:.0f} | "
                  f"orders filled {r['probe_fill_rate']*100:.0f}% | time to first fill p50 {r['probe_ttf_p50']:.2f}s p90 {r['probe_ttf_p90']:.1f}s | "
                  f"ahead at fill p50 {r['probe_ahead_at_fill_p50']:.0f}")
    for r in res:
        if r.get("markets", 0) == 0:
            L.append(f"| {r['name']} | 0 |")
            continue
        cells = []
        for c in cols:
            v = r[c]
            cells.append(f"{v:,.0f}" if c in ("contracts", "fills", "markets", "test_markets") else f"{v:,.2f}")
        L.append(f"| {r['name']} | " + " | ".join(cells) + " |")
        if r.get("vetoes"):
            L.append(f"|  ↳ vetoes: {r['vetoes']} |")
    for r in res:
        fb = r.get("fill_by")
        if not fb:
            continue
        tot = sum(v[1] for v in fb.values()) or 1
        L.append(f"\n{r['name']}: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)\n")
        L.append("| kind | class | touch age | level age | contracts | share | mo30 ¢ |\n|---|---|---|---|---|---|---|")
        for k, (v, q) in sorted(fb.items(), key=lambda kv: -kv[1][1])[:24]:
            L.append(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]} | {q:,.0f} | {q / tot * 100:.0f}% | {v / q:+.2f} |")
        agg = {}
        for k, (v, q) in fb.items():
            slot = agg.setdefault((k[0], k[1]), [0.0, 0.0]); slot[0] += v; slot[1] += q
        L.append("| **by kind/class** | | | | | | |")
        for k, (v, q) in sorted(agg.items(), key=lambda kv: -kv[1][1]):
            L.append(f"| {k[0]} | {k[1]} | — | — | {q:,.0f} | {q / tot * 100:.0f}% | {v / q:+.2f} |")
    text = "\n".join(L)
    print(text)
    if a.out:
        a.out.write_text(text)
    if a.fills_out:
        pl.DataFrame({"ticker": [x[0] for x in _fill_sink], "rx": [x[1] for x in _fill_sink], "side": [x[2] for x in _fill_sink],
                      "price": [x[3] for x in _fill_sink], "qty": [x[4] for x in _fill_sink], "improved": [x[5] for x in _fill_sink],
                      "sweep": [x[6] for x in _fill_sink]}).write_parquet(a.fills_out)
    if a.per_market:
        rows = [{"config": r["name"], "ticker": m.ticker, "stop_rx": m.stop_rx, "pnl": m.mark_pnl, "spread": m.spread_capture,
                 "inventory": m.inventory_pnl, "fills": m.fills, "sweep_fills": m.sweep_fills, "traded": (m.bought + m.sold) / QTY, "market_volume": m.market_volume / QTY,
                 "max_abs_pos": m.max_abs_pos / QTY}
                for r in res for m in r["per_market"] if m.mark_pnl is not None]
        pl.DataFrame(rows).write_parquet(a.per_market)


if __name__ == "__main__":
    main()
