"""Do fills *away from the touch* revert? (the "catch the wick" question)

Everything we have tested quotes at or within one tick of the touch. A different maker
posture — the one used on continuous venues — is to rest well behind the touch and be filled
only when a sweep runs through you, betting that the overshoot comes back. Whether that pays
is a property of the market, not of the strategy, and it is measurable straight from the tape:

For every touch trade we compute how far the print landed *beyond the pre-trade touch on the
maker's side* (the touch as of `--lookback` ms earlier, so every print in one sweep burst is
measured against the book the sweep started from), then the maker's markout at 10 s / 60 s /
300 s. Bucketing by that offset says whether a resting order 1c, 2c or 5c off the touch is
paid for being run over. Bucketing by time-to-close tests the hypothesis that what matters is
tick size relative to how fast fair value moves: in a market resolving in minutes a 2c sweep
is information, in one resolving in weeks it is someone wanting out.

Everything is in YES terms: markout = sign * (future yes-mid - trade yes price), sign +1 when
the resting YES bid was hit and -1 when the resting NO bid was hit, so + always means the
maker earned. `edge` is the half-spread captured at the fill (against the pre-trade mid), so
    markout ~ edge - adverse selection.

Memory is bounded: mids and touches are kept for the longest horizon only, and trades are
resolved and accumulated as the tape passes them.

    uv run python -m kalshi_data.research.offset_markouts 2026-09-20 --data-dir ../data_broad
    uv run python -m kalshi_data.research.offset_markouts 2026-09-20 --data-dir ../data_aws --series KXBTC15M
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

from ..book import parse_price, parse_qty
from ..raw import iter_records
from .markouts import FastBook, close_time

ONE = 10_000
QTY = 100
HORIZONS = (10, 60, 300)
PRUNE_EVERY = 4096

# offset of the print beyond the pre-trade touch, in cents
OFF_BUCKETS = ((0.0, "at touch"), (1.0, "0-1c"), (2.0, "1-2c"), (5.0, "2-5c"), (float("inf"), "5c+"))
# hours from the trade to the market's close
TTC_BUCKETS = ((0.25, "< 15 min"), (1, "15-60 min"), (6, "1-6 h"), (24, "6-24 h"),
               (24 * 7, "1-7 d"), (float("inf"), "> 7 d"))


def bucket(v: float, table) -> str:
    for hi, name in table:
        if v <= hi:
            return name
    return table[-1][1]


class Acc:
    __slots__ = ("q", "edge", "mo", "n", "win", "px")

    def __init__(self) -> None:
        self.q = 0.0
        self.edge = 0.0
        self.mo = [0.0] * len(HORIZONS)
        self.n = 0
        self.win = 0.0     # contracts whose longest-horizon markout is > 0
        self.px = 0.0      # contract-weighted fill price, YES cents

    def add(self, q: float, edge: float, mo: list[float], pyc: float) -> None:
        self.q += q
        self.edge += edge * q
        self.n += 1
        self.px += pyc * q
        if mo[-1] > 0:
            self.win += q
        for i, m in enumerate(mo):
            self.mo[i] += m * q


class Series:
    """Parallel (rx, value...) lists with bisect lookup and amortised pruning."""

    __slots__ = ("rx", "v", "adds")

    def __init__(self, width: int) -> None:
        self.rx: list[int] = []
        self.v: list[list] = [[] for _ in range(width)]
        self.adds = 0

    def push(self, rx: int, *vals) -> None:
        self.rx.append(rx)
        for col, x in zip(self.v, vals):
            col.append(x)
        self.adds += 1

    def prune(self, before_rx: int) -> None:
        self.adds = 0
        if len(self.rx) < 64:
            return
        cut = bisect.bisect_left(self.rx, before_rx) - 1
        if cut > 0:
            del self.rx[:cut]
            for col in self.v:
                del col[:cut]

    def at(self, rx: int) -> tuple | None:
        """The most recent entry at or before rx."""
        i = bisect.bisect_right(self.rx, rx) - 1
        if i < 0:
            return None
        return tuple(col[i] for col in self.v)


def load_closes(path: Path) -> dict[str, float]:
    from datetime import datetime, timezone
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    out = {}
    for tk, d in raw.items():
        s = d.get("close")
        if s:
            try:
                out[tk] = datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                continue
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--series", default=None, help="restrict to one series prefix")
    ap.add_argument("--lookback", type=float, default=250, help="ms: measure the touch this long before the print")
    ap.add_argument("--min-q", type=float, default=0.0, help="ignore prints smaller than this many contracts")
    ap.add_argument("--closes", type=Path, default=Path("../research/close_times.json"))
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    lookback_ns = int(a.lookback * 1e6)
    keep_ns = (max(HORIZONS) + 5) * 1_000_000_000
    closes = load_closes(a.closes)
    books: dict[str, FastBook] = {}
    mids: dict[str, Series] = defaultdict(lambda: Series(1))
    touch: dict[str, Series] = defaultdict(lambda: Series(2))
    ct_cache: dict[str, float | None] = {}
    pending: deque = deque()
    by_off: dict[str, Acc] = defaultdict(Acc)
    by_ttc_off: dict[tuple[str, str], Acc] = defaultdict(Acc)
    by_series_off: dict[tuple[str, str], Acc] = defaultdict(Acc)
    n_trades = n_scored = n_no_touch = n_no_close = n_no_mark = 0

    def close_of(tk: str) -> float | None:
        if tk in ct_cache:
            return ct_cache[tk]
        c = closes.get(tk)
        if c is None and tk.startswith(("KXBTC", "KXETH", "KXSOL", "KXXRP")):
            try:                      # parsed from the ticker, no REST
                c = close_time(tk)
            except Exception:         # noqa: BLE001
                c = None
        ct_cache[tk] = c
        return c

    def resolve(now_rx: int, flush: bool = False) -> None:
        nonlocal n_scored, n_no_mark
        while pending and (flush or pending[0][0] <= now_rx):
            _, tk, rx, sign, pyc, q, edge, ttcb, offb, series = pending.popleft()
            ms = mids[tk]
            mo = []
            for h in HORIZONS:
                got = ms.at(rx + h * 1_000_000_000)
                mo.append(sign * (got[0] - pyc) if got else None)
            if any(m is None for m in mo):
                n_no_mark += 1
                continue
            n_scored += 1
            by_off[offb].add(q, edge, mo, pyc)
            by_ttc_off[(ttcb, offb)].add(q, edge, mo, pyc)
            by_series_off[(series, offb)].add(q, edge, mo, pyc)

    for rec in iter_records(a.data_dir, a.day):
        raw = rec.raw
        t = raw.get("type")
        if t not in ("orderbook_snapshot", "orderbook_delta", "trade"):
            continue
        msg = raw["msg"]
        tk = msg["market_ticker"]
        if a.series and not tk.startswith(a.series + "-"):
            continue
        rx = rec.rx_ns

        if t == "trade":
            n_trades += 1
            q = parse_qty(msg["count_fp"]) / QTY
            if q < a.min_q:
                continue
            yp = parse_price(msg["yes_price_dollars"])
            hit = "no" if msg["taker_side"] == "yes" else "yes"   # the resting side that was hit
            sign = 1 if hit == "yes" else -1
            pyc = yp / 100                                        # trade price, YES cents
            got = touch[tk].at(rx - lookback_ns)
            if not got or got[0] < 0 or got[1] < 0:
                n_no_touch += 1
                continue
            by_, bn_ = got
            pre_mid = (by_ + (ONE - bn_)) / 2 / 100               # YES mid, cents
            # how far beyond the touch the print landed, on the maker's side
            off = (by_ - yp) / 100 if hit == "yes" else (bn_ - (ONE - yp)) / 100
            if off < -0.001:                                      # inside the touch: stale lookback, skip
                n_no_touch += 1
                continue
            edge = sign * (pre_mid - pyc)
            ct = close_of(tk)
            if ct is None:
                n_no_close += 1
                continue
            ttc_h = (ct - rx / 1e9) / 3600
            if ttc_h <= 0:
                n_no_close += 1
                continue
            pending.append((rx + max(HORIZONS) * 1_000_000_000, tk, rx, sign, pyc, q, edge,
                            bucket(ttc_h, TTC_BUCKETS), bucket(max(off, 0.0), OFF_BUCKETS),
                            tk.split("-")[0]))
            continue

        b = books.setdefault(tk, FastBook())
        if t == "orderbook_snapshot":
            b.snapshot(msg)
        else:
            if b.stale:
                continue
            try:
                b.delta(msg["side"], parse_price(msg["price_dollars"]), parse_qty(msg["delta_fp"]))
            except ValueError:
                b.stale = True
                continue
        th = touch[tk]
        if not th.rx or th.v[0][-1] != b.best_yes or th.v[1][-1] != b.best_no:
            th.push(rx, b.best_yes, b.best_no)
            if th.adds >= PRUNE_EVERY:
                th.prune(rx - max(keep_ns, 2_000_000_000))
        m = b.mid()
        if m is not None:
            ms = mids[tk]
            if not ms.rx or ms.v[0][-1] != m:
                ms.push(rx, m)
                if ms.adds >= PRUNE_EVERY:
                    ms.prune(rx - keep_ns)
        resolve(rx)

    resolve(0, flush=True)

    lines: list[str] = []
    w = lines.append
    tag = a.series or a.data_dir.name
    w(f"# Offset markouts, {tag} {a.day}: {n_trades:,} trades, {n_scored:,} scored "
      f"({n_no_touch:,} no touch, {n_no_close:,} no close, {n_no_mark:,} no mark)\n")
    w("Maker markout by how far the print landed beyond the pre-trade touch on the maker's side "
      f"(touch read {a.lookback:.0f} ms before the print). + = the resting maker earned.\n")
    hdr = " | ".join(f"mo{h}s ¢" for h in HORIZONS)
    w(f"| offset beyond touch | prints | contracts | fill px ¢ | edge at fill ¢ | {hdr} | win% |")
    w("|---|---|---|---|---|" + "---|" * len(HORIZONS) + "---|")
    for _, name in OFF_BUCKETS:
        acc = by_off.get(name)
        if not acc or not acc.q:
            continue
        mo = " | ".join(f"{m / acc.q:+.2f}" for m in acc.mo)
        w(f"| {name} | {acc.n:,} | {acc.q:,.0f} | {acc.px / acc.q:.1f} | {acc.edge / acc.q:+.2f} | {mo} "
          f"| {acc.win / acc.q * 100:.0f}% |")
    w("")

    offs = [n for _, n in OFF_BUCKETS]
    w(f"By time to close — markout at {HORIZONS[-1]} s, contracts in brackets:\n")
    w("| time to close | " + " | ".join(offs) + " |")
    w("|---|" + "---|" * len(offs))
    for _, ttcb in TTC_BUCKETS:
        cells, any_ = [], False
        for offb in offs:
            acc = by_ttc_off.get((ttcb, offb))
            if acc and acc.q:
                any_ = True
                cells.append(f"{acc.mo[-1] / acc.q:+.2f} ({acc.q:,.0f})")
            else:
                cells.append("—")
        if any_:
            w(f"| {ttcb} | " + " | ".join(cells) + " |")
    w("")

    w(f"Top series by volume filled beyond the touch — markout at {HORIZONS[-1]} s:\n")
    w("| series | " + " | ".join(offs) + " |")
    w("|---|" + "---|" * len(offs))
    tot: dict[str, float] = defaultdict(float)
    for (s, offb), acc in by_series_off.items():
        if offb != "at touch":
            tot[s] += acc.q
    for s in sorted(tot, key=lambda x: -tot[x])[:25]:
        cells = []
        for offb in offs:
            acc = by_series_off.get((s, offb))
            cells.append(f"{acc.mo[-1] / acc.q:+.2f} ({acc.q:,.0f})" if acc and acc.q else "—")
        w(f"| {s} | " + " | ".join(cells) + " |")

    text = "\n".join(lines)
    print(text)
    if a.out:
        a.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
