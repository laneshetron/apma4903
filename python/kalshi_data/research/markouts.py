"""Phase B step 1: sweep-conditioned maker markouts against true mids.

    uv run python -m kalshi_data.research.markouts 2026-09-14 [--data-dir ../data] [--series KXBTC15M ...]

Replays the collector's raw logs (order books + trades) and, for every taker
sweep, measures the passive side's P&L per contract against the reconstructed
mid 1s / 10s / 30s / 60s later.

Why this matters: Phase A averaged markouts over all trades. A resting order
at the touch is filled mostly when its whole level is consumed - which is
when the taker is most likely informed. Here each sweep is classified by how
much of the resting level it took:

  partial  consumed < 100% of the touch level (a back-of-queue order is NOT filled)
  full     consumed the whole touch level (a back-of-queue order IS filled)
  multi    consumed more than one price level (definitely filled, and then some)
  deep     resting price was not at the touch when the sweep started (unexpected)

The `full`+`multi` buckets are the fill-conditioned adverse-selection
estimate for a back-of-queue quoter; `partial` pro-rata is the optimistic
front-of-queue view.

Conventions: prices in cents of YES. taker_side=yes means the taker bought
YES and consumed a NO bid at (100 - p); taker_side=no means the taker bought
NO and consumed a YES bid at p. markout_h = sign * (p - mid(t+h)) with
sign=+1 when the maker is short YES (taker bought YES). markout_0 uses the
pre-trade mid and is the half-spread captured at the touch.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics as st
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ..book import parse_price, parse_qty
from ..raw import iter_records

HORIZONS_S = (1, 10, 30, 60)
SIGNAL_MOVE = 3.0     # $ tick-to-tick index move that counts as a signal
IDX_HORIZONS_S = (1, 5, 30)  # horizons for "does the index follow the sweep?"
DODGE_MS = 5.0        # reaction budget for a same-AZ cancel (tick receipt -> cancel processed)
NY = ZoneInfo("America/New_York")
ONE = 10_000  # price units per dollar


# --------------------------------------------------------------- fast book ---

class FastBook:
    """Bids-only book with O(1) best tracking; prices in 1/10000 $, qty in 1/100."""

    __slots__ = ("yes", "no", "best_yes", "best_no", "stale")

    def __init__(self) -> None:
        self.yes: dict[int, int] = {}
        self.no: dict[int, int] = {}
        self.best_yes = -1
        self.best_no = -1
        self.stale = True

    def side(self, s: str) -> dict[int, int]:
        return self.yes if s == "yes" else self.no

    def best(self, s: str) -> int:
        return self.best_yes if s == "yes" else self.best_no

    def _recompute(self, s: str) -> None:
        m = self.side(s)
        b = max(m) if m else -1
        if s == "yes":
            self.best_yes = b
        else:
            self.best_no = b

    def snapshot(self, msg: dict) -> None:
        self.yes = {parse_price(p): parse_qty(q) for p, q in msg.get("yes_dollars_fp") or [] if parse_qty(q)}
        self.no = {parse_price(p): parse_qty(q) for p, q in msg.get("no_dollars_fp") or [] if parse_qty(q)}
        self._recompute("yes")
        self._recompute("no")
        self.stale = False

    def delta(self, s: str, price: int, d: int) -> int:
        """Apply; returns qty before. Raises ValueError on negative."""
        m = self.side(s)
        before = m.get(price, 0)
        q = before + d
        if q < 0:
            raise ValueError("negative")
        if q == 0:
            m.pop(price, None)
            if price == self.best(s):
                self._recompute(s)
        else:
            m[price] = q
            if price > self.best(s):
                if s == "yes":
                    self.best_yes = price
                else:
                    self.best_no = price
        return before

    def mid(self) -> float | None:
        """Mid of YES in cents, or None if one side is empty."""
        if self.stale or self.best_yes < 0 or self.best_no < 0:
            return None
        return (self.best_yes + (ONE - self.best_no)) / 2 / 100


# ------------------------------------------------------------- per market ---

@dataclass(slots=True)
class Sweep:
    ticker: str
    ts_ms: int
    rx_ns: int
    taker_side: str
    qty: int = 0            # contracts * 100
    prices: set = field(default_factory=set)  # YES prices hit (1/10000 $)
    level_before: int = -1  # resting qty at the (first) resting level before the sweep
    at_touch: bool | None = None
    mid0: float | None = None
    ttx_min: float = 0.0
    mo: dict = field(default_factory=dict)  # horizon -> markout cents (None if unresolved)
    move_1s: float = 0.0        # |index move| over the second before the sweep ($)
    idx0: float | None = None   # index value at the sweep
    didx: dict = field(default_factory=dict)  # horizon -> signed index move after the sweep ($, + = taker's direction)
    dt_signal_ms: float = 1e9   # ms since the last index tick that moved >= SIGNAL_MOVE

    @property
    def klass(self) -> str:
        if self.at_touch is None or self.level_before < 0:
            return "unknown"
        if not self.at_touch:
            return "deep"
        if len(self.prices) > 1:
            return "multi"
        return "full" if self.qty >= self.level_before else "partial"

    @property
    def sign(self) -> int:
        return 1 if self.taker_side == "yes" else -1

    def price_cents(self) -> float:
        # the (first) resting level, in cents of YES
        p = min(self.prices) if self.taker_side == "yes" else max(self.prices)
        return p / 100


class MarketState:
    __slots__ = ("book", "hist", "pending", "open_sweep", "close_ts")

    def __init__(self, close_ts: float):
        self.book = FastBook()
        # (side, price) -> deque of (ts_ms, qty_before) for recent deltas
        self.hist: dict[tuple[str, int], deque] = defaultdict(lambda: deque(maxlen=64))
        # per horizon: deque of (deadline_ns, sweep); each is in deadline order
        self.pending: dict[int, deque] = {h: deque() for h in HORIZONS_S}
        self.open_sweep: Sweep | None = None
        self.close_ts = close_ts


_TICKER_RE = re.compile(r"^([A-Z0-9]+)-(\d\d)([A-Z]{3})(\d\d)(\d\d)(\d\d)?")


def close_time(ticker: str) -> float | None:
    """Market close (unix s) parsed from the ticker's date-time segment (ET)."""
    m = _TICKER_RE.match(ticker)
    if not m:
        return None
    _, yy, mon, dd, hh, mm = m.groups()
    dt = datetime.strptime(f"20{yy}{mon}{dd} {hh}{mm or '00'}", "%Y%b%d %H%M").replace(tzinfo=NY)
    return dt.timestamp()


class Analyzer:
    def __init__(self, series: set[str] | None):
        self.series = series
        self.markets: dict[str, MarketState] = {}
        self.last_seq: dict[int, int] = {}
        self.sweeps: list[Sweep] = []
        self.gaps = 0
        self.n_trades = 0
        self.n_trades_by_series: dict[str, int] = defaultdict(int)
        self.index_id = "BRTI"
        self.ticks: deque = deque()   # (rx_ns, value) over the last ~2s
        self.last_signal_rx: int = -1 # rx_ns of the last tick moving >= SIGNAL_MOVE
        self.idx_pending: dict[int, deque] = {h: deque() for h in IDX_HORIZONS_S}  # (deadline_ns, sweep)
        self.idx_last: float | None = None

    def _ms(self, ticker: str) -> MarketState | None:
        if self.series and ticker.split("-")[0] not in self.series:
            return None
        ms = self.markets.get(ticker)
        if ms is None:
            ct = close_time(ticker)
            if ct is None:
                return None
            ms = self.markets[ticker] = MarketState(ct)
        return ms

    def _mark_all_stale(self) -> None:
        for ms in self.markets.values():
            ms.book.stale = True

    # -- resolution of pending markouts -----------------------------------
    def _resolve(self, ms: MarketState, now_ns: int) -> None:
        """Resolve markouts whose deadline has passed, using the mid in effect
        just before the update at now_ns."""
        mid = ms.book.mid()
        for h, dq in ms.pending.items():
            while dq and dq[0][0] <= now_ns:
                _, sw = dq.popleft()
                sw.mo[h] = None if mid is None else sw.sign * (sw.price_cents() - mid)

    def _close_sweep(self, ms: MarketState) -> None:
        sw = ms.open_sweep
        if sw is None:
            return
        ms.open_sweep = None
        b = ms.book
        side = "no" if sw.taker_side == "yes" else "yes"
        # resting level: the first price the sweep hit on the resting side
        rest_price = (ONE - min(sw.prices)) if sw.taker_side == "yes" else max(sw.prices)
        # qty at that level before the first delta at/after the trade time
        before = None
        for ts_ms, qb in ms.hist.get((side, rest_price), ()):
            if ts_ms >= sw.ts_ms:
                before = qb
                break
        if before is None:
            before = b.side(side).get(rest_price, 0)  # no delta seen yet: current qty
        sw.level_before = before
        # touch test on the pre-trade book: was rest_price the best on that side?
        # Reconstruct best-before from history: if the current best is worse than
        # rest_price the level was consumed; if better, a better level existed.
        best_now = b.best(side)
        # After the sweep the best is either this level (partially consumed) or
        # worse (emptied); a better surviving level means we were not at the touch.
        sw.at_touch = None if b.stale else rest_price >= best_now
        if not b.stale:
            # pre-trade mid approximation: undo the sweep's own level changes
            # only matters for markout_0 (half-spread captured); use the touch
            yes_b = b.best_yes if side != "yes" else max(b.best_yes, rest_price)
            no_b = b.best_no if side != "no" else max(b.best_no, rest_price)
            if yes_b >= 0 and no_b >= 0:
                sw.mid0 = (yes_b + (ONE - no_b)) / 2 / 100
                sw.mo[0] = sw.sign * (sw.price_cents() - sw.mid0)
        sw.ttx_min = (ms.close_ts - sw.ts_ms / 1000) / 60
        for h in HORIZONS_S:
            ms.pending[h].append((sw.rx_ns + h * 1_000_000_000, sw))
        self.sweeps.append(sw)

    # -- record handling ---------------------------------------------------
    def feed(self, rec) -> None:
        raw = rec.raw
        t = raw.get("type")
        if t == "_local":
            ev = raw.get("event")
            if ev in ("connect", "disconnect"):
                self._mark_all_stale()
                self.last_seq.clear()
            elif ev == "resync":
                for tk in raw.get("markets") or []:
                    if tk in self.markets:
                        self.markets[tk].book.stale = True
            return
        sid, seq = raw.get("sid", 0), raw.get("seq", 0)
        if sid and seq:
            # every message on a sid consumes a seq, including ok responses
            last = self.last_seq.get(sid)
            if last is not None and seq != last + 1:
                self.gaps += 1
                if t in ("orderbook_snapshot", "orderbook_delta"):
                    self._mark_all_stale()
            self.last_seq[sid] = seq
        if t == "cfbenchmarks_value_5hz":
            msg = raw["msg"]
            if msg.get("index_id") != self.index_id:
                return
            v = float(json.loads(msg["data"])["value"])
            rx = rec.rx_ns
            # resolve "index after sweep" lookups with the value in effect just before this tick
            if self.idx_last is not None:
                for h, dq in self.idx_pending.items():
                    while dq and dq[0][0] <= rx:
                        _, sw = dq.popleft()
                        sw.didx[h] = sw.sign * (self.idx_last - sw.idx0)
            self.idx_last = v
            if self.ticks and abs(v - self.ticks[-1][1]) >= SIGNAL_MOVE:
                self.last_signal_rx = rx
            self.ticks.append((rx, v))
            while self.ticks and self.ticks[0][0] < rx - 2_000_000_000:
                self.ticks.popleft()
            return
        if t not in ("orderbook_snapshot", "orderbook_delta", "trade"):
            return
        msg = raw["msg"]
        ms = self._ms(msg["market_ticker"])
        if ms is None:
            return
        rx = rec.rx_ns

        if t == "trade":
            self.n_trades += 1
            self.n_trades_by_series[msg["market_ticker"].split("-")[0]] += 1
            ts_ms = msg["ts_ms"]
            sw = ms.open_sweep
            if sw is not None and (sw.ts_ms != ts_ms or sw.taker_side != msg["taker_side"]):
                self._close_sweep(ms)
                sw = None
            if sw is None:
                sw = ms.open_sweep = Sweep(msg["market_ticker"], ts_ms, rx, msg["taker_side"])
                if self.ticks:
                    recent = [v for r, v in self.ticks if r >= rx - 1_000_000_000]
                    if recent:
                        sw.move_1s = max(abs(self.ticks[-1][1] - v) for v in recent)
                if self.last_signal_rx >= 0:
                    sw.dt_signal_ms = (rx - self.last_signal_rx) / 1e6
                if self.idx_last is not None:
                    sw.idx0 = self.idx_last
                    for h in IDX_HORIZONS_S:
                        self.idx_pending[h].append((rx + h * 1_000_000_000, sw))
            sw.qty += parse_qty(msg["count_fp"])
            sw.prices.add(parse_price(msg["yes_price_dollars"]))
            return

        # book update: close any open sweep whose time has passed, resolve, apply
        if ms.open_sweep is not None and (t == "orderbook_snapshot" or msg.get("ts_ms", 0) > ms.open_sweep.ts_ms):
            self._close_sweep(ms)
        self._resolve(ms, rx)
        if t == "orderbook_snapshot":
            ms.book.snapshot(msg)
            ms.hist.clear()
            return
        if ms.book.stale:
            return
        side, price, d = msg["side"], parse_price(msg["price_dollars"]), parse_qty(msg["delta_fp"])
        try:
            before = ms.book.delta(side, price, d)
        except ValueError:
            ms.book.stale = True
            return
        ms.hist[(side, price)].append((msg.get("ts_ms", 0), before))

    def finish(self, now_ns: int) -> None:
        for ms in self.markets.values():
            self._close_sweep(ms)
            self._resolve(ms, now_ns)


# ---------------------------------------------------------------- report ---

def wmean(pairs):
    pairs = [(v, w) for v, w in pairs if v is not None]
    tot = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / tot if tot else None


def fmt(x):
    return "   n/a" if x is None else f"{x:+6.2f}"


def report(series: str, sweeps: list[Sweep], gaps: int, n_trades: int, index_note: str = "") -> str:
    L = [f"## {series}", ""]
    vol = sum(s.qty for s in sweeps) / 100
    L.append(f"- {len(sweeps):,} sweeps from {n_trades:,} trades, {vol:,.0f} contracts; seq gaps in log: {gaps}")
    by = defaultdict(list)
    for s in sweeps:
        by[s.klass].append(s)
    L.append("- volume by sweep class: " + ", ".join(
        f"{k} {sum(s.qty for s in v)/100/vol*100:.0f}%" for k, v in sorted(by.items(), key=lambda kv: -sum(s.qty for s in kv[1]))))
    sizes = sorted(s.qty / 100 for s in sweeps)
    if sizes:
        L.append(f"- sweep size: median {st.median(sizes):.0f}, p90 {sizes[int(.9*len(sizes))]:.0f}, p99 {sizes[int(.99*len(sizes))]:.0f} contracts")
    L.append("")
    L.append("Maker markout vs true mid, cents/contract, volume-weighted. markout_0 = half-spread captured at the touch.")
    L.append("")
    hdr = "| class | vol share | 0 | 1s | 10s | 30s | 60s |"
    L.append(hdr)
    L.append("|---|---|---|---|---|---|---|")

    def row(name, ss, share):
        cells = [fmt(wmean((s.mo.get(h), s.qty) for s in ss)) for h in (0, *HORIZONS_S)]
        return f"| {name} | {share:.0f}% | " + " | ".join(cells) + " |"

    for k in ("partial", "full", "multi", "deep", "unknown"):
        ss = by.get(k, [])
        if ss:
            L.append(row(k, ss, sum(s.qty for s in ss) / 100 / vol * 100))
    fm = by.get("full", []) + by.get("multi", [])
    if fm:
        L.append(row("**full+multi (fill-conditioned)**", fm, sum(s.qty for s in fm) / 100 / vol * 100))
    L.append(row("all", sweeps, 100))
    L.append("")
    L.append("Fill-conditioned (full+multi) markout by minutes to expiry:")
    L.append("")
    L.append("| min to expiry | vol share | 0 | 1s | 10s | 30s | 60s |")
    L.append("|---|---|---|---|---|---|---|")
    buckets = defaultdict(list)
    for s in fm:
        b = int(s.ttx_min) if s.ttx_min < 10 else (10 if s.ttx_min < 15 else 15)
        buckets[b].append(s)
    fmvol = sum(s.qty for s in fm) / 100 or 1
    for b in sorted(buckets):
        name = f"{b}" if b < 10 else ("10-14" if b == 10 else "15+")
        L.append(row(name, buckets[b], sum(s.qty for s in buckets[b]) / 100 / fmvol * 100))
    L.append("")
    L.append("")
    L.append(f"Markouts by index-signal context (signal = {index_note}). A same-AZ quoter can cancel")
    L.append(f"before sweeps arriving > {DODGE_MS:.0f}ms after the tick; earlier ones are unavoidable.")
    L.append("")
    L.append("| context | class | vol share | 0 | 1s | 10s | 30s | 60s |")
    L.append("|---|---|---|---|---|---|---|---|")

    def ctx(sw):
        if sw.dt_signal_ms <= DODGE_MS:
            return "post-signal, unavoidable (<=%dms)" % DODGE_MS
        if sw.dt_signal_ms <= 1000:
            return "post-signal, dodgeable (%d-1000ms)" % DODGE_MS
        return "quiet (no signal in 1s)"

    for name in ("quiet (no signal in 1s)", "post-signal, dodgeable (%d-1000ms)" % DODGE_MS, "post-signal, unavoidable (<=%dms)" % DODGE_MS):
        for kname, ks in (("all", sweeps), ("full+multi", fm), ("partial", by.get("partial", []))):
            ss = [s for s in ks if ctx(s) == name]
            if ss:
                cells = [fmt(wmean((s.mo.get(h), s.qty) for s in ss)) for h in (0, *HORIZONS_S)]
                L.append(f"| {name} | {kname} | {sum(s.qty for s in ss)/100/vol*100:.0f}% | " + " | ".join(cells) + " |")
    L.append("")
    L.append("Does the index follow the sweep? Mean signed index move after the sweep, $ (+ = in the taker's direction), volume-weighted:")
    L.append("")
    L.append("| class | 1s | 5s | 30s | n |")
    L.append("|---|---|---|---|---|")
    for kname, ks in (("partial", by.get("partial", [])), ("full+multi", fm), ("all", sweeps)):
        ss = [s for s in ks if s.idx0 is not None]
        if ss:
            cells = [fmt(wmean((s.didx.get(h), s.qty) for s in ss)) for h in IDX_HORIZONS_S]
            L.append(f"| {kname} | " + " | ".join(cells) + f" | {len(ss):,} |")
    L.append("")
    excl = [s for s in fm if s.ttx_min >= 2]
    if excl:
        L.append("Fill-conditioned, excluding the last 2 minutes: " + ", ".join(
            f"{h}s {fmt(wmean((s.mo.get(h), s.qty) for s in excl)).strip()}c" for h in HORIZONS_S)
            + f" (half-spread {fmt(wmean((s.mo.get(0), s.qty) for s in excl)).strip()}c)")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--end", type=date.fromisoformat, default=None)
    ap.add_argument("--data-dir", type=Path, default=Path("../data"))
    ap.add_argument("--series", nargs="*", default=["KXBTC15M", "KXETH15M", "KXBTCD"])
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--index", default="BRTI", help="index used for signal context (BRTI for BTC, ETHUSD_RTI for ETH)")
    a = ap.parse_args()

    an = Analyzer(set(a.series))
    an.index_id = a.index
    n = 0
    last_rx = 0
    for rec in iter_records(a.data_dir, a.day, a.end):
        an.feed(rec)
        last_rx = rec.rx_ns
        n += 1
        if n % 1_000_000 == 0:
            print(f"  {n/1e6:.0f}M records, {len(an.sweeps):,} sweeps", file=sys.stderr)
    an.finish(last_rx + 120 * 1_000_000_000)

    by_series = defaultdict(list)
    for s in an.sweeps:
        by_series[s.ticker.split("-")[0]].append(s)
    out = [f"# Sweep-conditioned markouts, {a.day}" + (f" to {a.end}" if a.end else ""), "",
           f"{n:,} raw records; {an.n_trades:,} trades; {len(an.sweeps):,} sweeps; {len(an.markets)} markets. "
           "Method: `python/kalshi_data/research/markouts.py`.", ""]
    for s in a.series:
        if by_series.get(s):
            out.append(report(s, by_series[s], an.gaps, an.n_trades_by_series[s],
                              f"{an.index_id} tick-to-tick move >= ${SIGNAL_MOVE:g}"))
            out.append("")
    text = "\n".join(out)
    print(text)
    if a.out:
        a.out.write_text(text)


if __name__ == "__main__":
    main()
