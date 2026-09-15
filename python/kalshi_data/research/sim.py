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
TICK = 100          # 1c
QTY = 100           # 1 contract
TAKER_FEE = 0.07    # per contract: 0.07 * p * (1-p) dollars


@dataclass(slots=True)
class Params:
    name: str
    size: int = 100                 # contracts per side
    max_pos: int = 500              # contracts
    latency_ms: float = 2.0
    stop_before_s: float = 120.0
    signal_move: float | None = None  # $ over 1s on the spot mid; None disables
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


@dataclass(slots=True)
class Order:
    side: str          # book side we rest on: "yes" (our YES bid) or "no" (our YES ask)
    price: int         # price on that side
    remaining: int     # qty units
    ahead: int | None  # queue ahead of us; None until activation
    active_from: int   # rx_ns when the order is live
    cancel_at: int | None = None  # rx_ns when a cancel lands
    improved: bool = False        # placed one tick inside the touch
    last_seen: int = 0            # rx_ns of the last probe update
    filled_any: bool = False
    unexplained: deque = field(default_factory=deque)  # (rx_ns, ts_ms, qty) negative deltas awaiting a trade


@dataclass(slots=True)
class MarketPnL:
    ticker: str
    fills: int = 0
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
        self.lat = int(p.latency_ms * 1e6)
        self.orders: dict[str, dict[str, Order]] = defaultdict(dict)   # ticker -> side -> Order
        self.pnl: dict[str, MarketPnL] = {}
        self.blocked: dict[str, dict[str, int]] = defaultdict(lambda: {"yes": 0, "no": 0})  # side -> rx_ns until which quoting is off
        self.stopped: set[str] = set()
        self.swept_until: dict[str, dict[str, int]] = defaultdict(lambda: {"yes": 0, "no": 0})
        self.vetoes: dict[str, int] = defaultdict(int)  # reason -> count of (side, requote) decisions blocked
        self.adverse_since: dict[str, dict[str, int]] = defaultdict(lambda: {"yes": -1, "no": -1})
        self.probe_adv_qty = 0.0     # contracts by which live orders advanced
        self.probe_live_s = 0.0      # live-order seconds
        self.probe_ttf: list[float] = []      # seconds from activation to (first) fill
        self.probe_ahead_at_fill: list[float] = []
        self.probe_ahead_at_place: list[float] = []
        self.edge_blocked: dict[str, dict[str, bool]] = defaultdict(lambda: {"yes": False, "no": False})
        self.fill_mo: deque = deque()   # (deadline_ns, ticker, sign, price_cents, qty, horizon) for markouts of our fills
        self.fill_markouts: dict[int, list[tuple[float, int]]] = {10: [], 30: []}  # horizon -> (markout cents, qty)
        self.adverse_10s: float = 0.0   # dollars: mid move in the 10s after our fills, signed (negative = adverse)

    # ---- helpers -----------------------------------------------------------
    def m(self, tk: str) -> MarketPnL:
        r = self.pnl.get(tk)
        if r is None:
            r = self.pnl[tk] = MarketPnL(tk)
        return r

    def _fill(self, tk: str, o: Order, qty: int, rx: int) -> None:
        r = self.m(tk)
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
            self.fill_mo.append((rx + h * 1_000_000_000, tk, sign, px, qty, h, mid))
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
        r.last_mid = book.mid()   # no inventory P&L is booked across a stale gap
        r.pre_mid = r.last_mid

    def resolve_markouts(self, tk: str, rx: int, book: FastBook) -> None:
        while self.fill_mo and self.fill_mo[0][0] <= rx:
            _, t, sign, px, q, h, mid0 = self.fill_mo.popleft()
            r = self.pnl.get(t)
            mid = book.mid() if t == tk else (r.last_mid if r else None)
            if mid is not None:
                self.fill_markouts[h].append((sign * (px - mid), q))
                if h == 10 and mid0 is not None:
                    # mid move in the 10s after the fill, on the filled quantity: the
                    # adverse-selection slice of inventory P&L (negative = moved against us)
                    self.adverse_10s += sign * (mid0 - mid) / 100 * q / QTY

    def on_delta(self, tk: str, rx: int, ts_ms: int, side: str, price: int, before: int, after: int, book: FastBook, close_ns: int, ctx: "Context | None" = None) -> None:
        r = self.m(tk)
        mid = book.mid()
        if ts_ms != r.last_ts:
            r.pre_mid, r.last_ts = r.last_mid, ts_ms
        if mid is not None and r.last_mid is not None and tk not in self.stopped:
            r.inventory_pnl += (r.pos / QTY) * (mid - r.last_mid) / 100
        if mid is not None:
            r.last_mid = mid
        self.resolve_markouts(tk, rx, book)
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
        for oo in self.orders[tk].values():
            prev_ahead = oo.ahead
            self._flush_unexplained(oo, rx, book)
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

    def on_tick(self, tk_list: list[str], rx: int, mid: float, mid_1s_ago: float | None) -> None:
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
                o.cancel_at = rx + self.lat

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
                if mid is not None:
                    r.mark_pnl = r.cash + r.pos / QTY * mid / 100
                    p = mid / 100
                    r.flatten_cost = abs(r.pos) / QTY * (0.005 + TAKER_FEE * p * (1 - p))
            for o in orders.values():
                if o.cancel_at is None:
                    o.cancel_at = rx + self.lat
            return
        if book.stale or book.best_yes < 0 or book.best_no < 0:
            return
        spread = (ONE - book.best_no) - book.best_yes
        want = {
            "yes": book.best_yes + (TICK if spread > TICK else 0),
            "no": book.best_no + (TICK if spread > TICK else 0),
        }
        pos = r.pos
        lim = self.p.max_pos * QTY - self.p.size * QTY
        allow = {"yes": pos <= lim, "no": pos >= -lim}
        p = self.p
        if p.greeks_cap is not None and ctx is not None:
            g = ctx.delta_sigma10(tk, close_ns)
            if g is not None and g >= p.greeks_cap:
                allow = {"yes": False, "no": False}
                self.vetoes["greeks"] += 2
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
            if p.min_depth is not None and spread <= TICK and depth[s] < p.min_depth * QTY and allow[s]:
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
            if o is not None and o.cancel_at is None and (not ok or o.price != want[s]):
                o.cancel_at = rx + self.lat
            if ok and (o is None or o.cancel_at is not None) and not any(
                x.side == s and x.cancel_at is None for x in orders.values()
            ):
                if p.fair_gap_join is not None and gap is not None and (
                        (s == "yes" and gap < -p.fair_gap_join) or (s == "no" and gap > p.fair_gap_join)):
                    self.vetoes["fair_join"] += 1
                    continue
                if p.join_theta is not None and ctx is not None and ctx.edge_model is not None:
                    other = "no" if s == "yes" else "yes"
                    imb = (depth[other] - depth[s]) / (depth[other] + depth[s]) if depth[other] + depth[s] > 0 else 0.0
                    q_join = 0.0 if spread > TICK else depth[s] / QTY
                    e = ctx.edge_model.edge(s, imb, ctx.micro_unsigned(), (close_ns - rx) / 6e10, q_join)
                    if e is not None and e < -p.join_theta:
                        self.vetoes["join"] += 1
                        continue
                # place: becomes live after latency; replaces a cancelled order once it lands
                if o is None or rx >= o.cancel_at:
                    orders[s] = Order(s, want[s], self.p.size * QTY, None, rx + self.lat, improved=spread > TICK)

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
        self.cutoff_rx = int(df["rx_ns"][int(df.height * train_frac)])
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
        self.spot = spot
        self.strikes = strikes
        self.alpha_model = alpha_model
        self.edge_model = edge_model
        self.alpha: float | None = None

    brti_series: SpotSeries | None = None

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
        alpha_parquet: Path | None = None) -> tuple[list[dict], int]:
    quoters = [Quoter(p) for p in configs]
    books: dict[str, FastBook] = {}
    closes: dict[str, int] = {}
    ticks: deque = deque()   # (rx_ns, mid)
    need_fair = any(p.fair_gap_thr is not None or p.fair_gap_join is not None for p in configs)
    need_ctx = need_fair or any(p.alpha_thr is not None or p.greeks_cap is not None or p.edge_theta is not None or p.join_theta is not None for p in configs)
    alpha_model = fit_alpha(alpha_parquet) if (alpha_parquet and any(p.alpha_thr is not None for p in configs)) else None
    test_from = alpha_model[3] if alpha_model else 0
    strikes: dict[str, float] = {}
    if need_fair or any(p.greeks_cap is not None for p in configs):
        tickers = sorted({r.raw["msg"]["market_ticker"] for r in iter_records(data_dir, day)
                          if r.raw.get("type") == "orderbook_snapshot" and r.raw["msg"]["market_ticker"].startswith(series + "-")})
        strikes = fetch_strikes(tickers)
    spot = SpotState()
    edge_model = EdgeModel(alpha_parquet) if (alpha_parquet and any(p.edge_theta is not None or p.join_theta is not None for p in configs)) else None
    if edge_model is not None and not test_from:
        test_from = edge_model.cutoff_rx
    ctx = Context(spot, strikes, alpha_model, edge_model)
    if need_fair:
        ctx.brti_series = SpotSeries()
    asset = "ETH" if "ETH" in series else "BTC"

    def spot_events():
        its = [iter_spot(data_dir, v, day) for v in VENUES]
        yield from heapq.merge(*its, key=lambda e: e.rx_ns)

    def cb_sizes():
        for rec in iter_records(data_dir / "spot" / "coinbase", day):
            raw = rec.raw
            if raw.get("type") == "ticker" and raw.get("product_id") == "BTC-USD" and raw.get("best_bid_size"):
                yield ("cbsz", rec.rx_ns, float(raw["best_bid_size"]), float(raw["best_ask_size"]))

    n = 0
    stream = heapq.merge(iter_records(data_dir, day), spot_events(), cb_sizes(),
                         key=lambda e: e[1] if isinstance(e, tuple) else e.rx_ns)
    for rec in stream:
        n += 1
        if n % 5_000_000 == 0:
            print(f"  {n/1e6:.0f}M records", file=sys.stderr)
        if isinstance(rec, tuple):
            spot.on_quote_sizes(rec[2], rec[3])
            continue
        rx = rec.rx_ns
        if isinstance(rec, SpotTrade):
            if rec.asset == asset:
                spot.on_trade(rec)
            continue
        if isinstance(rec, SpotQuote):
            if rec.asset != asset:
                continue
            spot.on_quote(rec)
            if rec.venue != venue:
                continue
            mid = (rec.bid + rec.ask) / 2
            while ticks and ticks[0][0] < rx - 1_000_000_000:
                ticks.popleft()
            ago = ticks[0][1] if ticks else None
            ticks.append((rx, mid))
            if need_ctx:
                ctx.refresh_alpha(rx)
            live = [tk for tk, b in books.items() if not b.stale]
            for q in quoters:
                q.on_tick(live, rx, mid, ago)
            continue
        raw = rec.raw
        if raw.get("type") == "cfbenchmarks_value_5hz" and raw["msg"].get("index_id") == "BRTI":
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

PROBE = [
    Params("probe prorata (2ms, cancel $2/1s, stop 5min, max pos 200)", **_F),
    Params("probe pessimistic", **_F, queue="pessimistic"),
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
    a = ap.parse_args()
    configs = SWEEP if a.sweep else INVENTORY if a.inventory else FILTERS if a.filters else FILTERS2 if a.filters2 else VALUE if a.value else VALUE_OOS if a.value_oos else PROBE if a.probe else JOIN if a.join else FAIR if a.fair else CONFIGS
    res, test_from = run(a.data_dir, a.day, a.series, a.venue, configs, Path("../research") / f"alpha_{a.day}.parquet")
    cols = ["markets", "pnl_$", "spread_$", "inventory_$", "adverse_10s_$", "test_markets", "test_pnl_$", "test_spread_$", "test_inventory_$", "realized_$", "unrealized_$", "pnl_per_market_$", "pnl_sd_$", "t_stat", "worst_$", "contracts", "pnl_c_per_contract", "fill_markout_30s_c", "improved_fill_%", "fill_share_%", "fills", "avg_max_pos", "end_pos_abs", "flatten_cost_$"]
    L = [f"# Quoter simulation, {a.series}, {a.day}", "",
         "Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. "
         "No market impact. See `python/kalshi_data/research/sim.py`.", "",
         "| config | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 1)]
    if a.probe:
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
    text = "\n".join(L)
    print(text)
    if a.out:
        a.out.write_text(text)


if __name__ == "__main__":
    main()
