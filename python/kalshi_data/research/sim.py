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

from ..book import parse_price, parse_qty
from ..raw import iter_records
from ..spot import SpotQuote, iter_spot
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


@dataclass(slots=True)
class Order:
    side: str          # book side we rest on: "yes" (our YES bid) or "no" (our YES ask)
    price: int         # price on that side
    remaining: int     # qty units
    ahead: int | None  # queue ahead of us; None until activation
    active_from: int   # rx_ns when the order is live
    cancel_at: int | None = None  # rx_ns when a cancel lands
    improved: bool = False        # placed one tick inside the touch
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


class Quoter:
    """One strategy configuration, run against every market of the series."""

    def __init__(self, p: Params):
        self.p = p
        self.lat = int(p.latency_ms * 1e6)
        self.orders: dict[str, dict[str, Order]] = defaultdict(dict)   # ticker -> side -> Order
        self.pnl: dict[str, MarketPnL] = {}
        self.blocked: dict[str, dict[str, int]] = defaultdict(lambda: {"yes": 0, "no": 0})  # side -> rx_ns until which quoting is off
        self.stopped: set[str] = set()
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

    def on_delta(self, tk: str, rx: int, ts_ms: int, side: str, price: int, before: int, after: int, book: FastBook, close_ns: int) -> None:
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
            elif o.ahead is not None and after < before:
                o.unexplained.append((rx, ts_ms, before - after))
            elif o.ahead is None and after > before:
                pass  # arrivals before activation are ahead of us anyway
        for oo in self.orders[tk].values():
            self._flush_unexplained(oo, rx, book)
            if oo.ahead is None and rx >= oo.active_from:
                oo.ahead = book.side(oo.side).get(oo.price, 0)
        self._requote(tk, rx, book, close_ns)

    def on_trade(self, tk: str, rx: int, ts_ms: int, taker_side: str, yes_price: int, qty: int, book: FastBook) -> None:
        self.m(tk).market_volume += qty
        side = "yes" if taker_side == "no" else "no"        # resting side consumed
        price = yes_price if side == "yes" else ONE - yes_price
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
            o.ahead -= qty
        else:
            spill = qty - o.ahead
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

    def _requote(self, tk: str, rx: int, book: FastBook, close_ns: int) -> None:
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
        for s in ("yes", "no"):
            o = orders.get(s)
            ok = allow[s] and rx >= self.blocked[tk][s]
            if o is not None and o.cancel_at is None and (not ok or o.price != want[s]):
                o.cancel_at = rx + self.lat
            if ok and (o is None or o.cancel_at is not None) and not any(
                x.side == s and x.cancel_at is None for x in orders.values()
            ):
                # place: becomes live after latency; replaces a cancelled order once it lands
                if o is None or rx >= o.cancel_at:
                    orders[s] = Order(s, want[s], self.p.size * QTY, None, rx + self.lat, improved=spread > TICK)

    # ---- summary ---------------------------------------------------------------
    def summary(self) -> dict:
        ms = [r for r in self.pnl.values() if r.mark_pnl is not None]
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
        return {
            "name": self.p.name,
            "markets": len(ms),
            "pnl_$": sum(pnl),
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


# ------------------------------------------------------------------- driver ---

def run(data_dir: Path, day: date, series: str, venue: str, configs: list[Params]) -> list[dict]:
    quoters = [Quoter(p) for p in configs]
    books: dict[str, FastBook] = {}
    closes: dict[str, int] = {}
    ticks: deque = deque()   # (rx_ns, mid)
    stale_all = True

    def quotes():
        for q in iter_spot(data_dir, venue, day):
            if isinstance(q, SpotQuote) and q.asset == ("ETH" if "ETH" in series else "BTC"):
                yield q

    n = 0
    for rec in heapq.merge(iter_records(data_dir, day), quotes(), key=lambda r: r.rx_ns):
        n += 1
        if n % 5_000_000 == 0:
            print(f"  {n/1e6:.0f}M records", file=sys.stderr)
        rx = rec.rx_ns
        if not hasattr(rec, "raw"):
            mid = (rec.bid + rec.ask) / 2
            while ticks and ticks[0][0] < rx - 1_000_000_000:
                ticks.popleft()
            ago = ticks[0][1] if ticks else None
            ticks.append((rx, mid))
            live = [tk for tk, b in books.items() if not b.stale]
            for q in quoters:
                q.on_tick(live, rx, mid, ago)
            continue
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
            q.on_delta(tk, rx, msg.get("ts_ms", 0), side, price, before, before + d, b, closes[tk])
    return [q.summary() for q in quoters]


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
    a = ap.parse_args()
    res = run(a.data_dir, a.day, a.series, a.venue, SWEEP if a.sweep else CONFIGS)
    cols = ["markets", "pnl_$", "spread_$", "inventory_$", "adverse_10s_$", "realized_$", "unrealized_$", "pnl_per_market_$", "pnl_sd_$", "t_stat", "worst_$", "contracts", "pnl_c_per_contract", "fill_markout_30s_c", "improved_fill_%", "fill_share_%", "fills", "avg_max_pos", "end_pos_abs", "flatten_cost_$"]
    L = [f"# Quoter simulation, {a.series}, {a.day}", "",
         "Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. "
         "No market impact. See `python/kalshi_data/research/sim.py`.", "",
         "| config | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 1)]
    for r in res:
        if r.get("markets", 0) == 0:
            L.append(f"| {r['name']} | 0 |")
            continue
        cells = []
        for c in cols:
            v = r[c]
            cells.append(f"{v:,.0f}" if c in ("contracts", "fills", "markets") else f"{v:,.2f}")
        L.append(f"| {r['name']} | " + " | ".join(cells) + " |")
    text = "\n".join(L)
    print(text)
    if a.out:
        a.out.write_text(text)


if __name__ == "__main__":
    main()
