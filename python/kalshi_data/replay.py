"""Rebuild order books from a raw log, honoring the collector's local events.

A market's book is invalid ("stale") from a connect/disconnect/gap/resync
event until its next orderbook_snapshot, exactly as in the live collector.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from .book import NegativeQty, OrderBook, parse_price
from .raw import Record


@dataclass(slots=True)
class BookUpdate:
    rx_ns: int
    ticker: str
    book: OrderBook  # live reference; copy() to keep
    kind: str  # "snapshot" | "delta"
    side: str | None = None   # for deltas: the level that changed
    price: int | None = None
    qty: int | None = None    # quantity at that level after the update


@dataclass(slots=True)
class RestCheck:
    rx_ns: int
    ticker: str
    rest: OrderBook
    live: OrderBook | None  # None if the live book was stale at that moment


class Replayer:
    def __init__(self, history_ns: int = 0) -> None:
        self.books: dict[str, OrderBook] = {}
        self.stale: dict[str, bool] = {}
        self.last_seq: dict[int, int] = {}
        self.gaps = 0
        self.negatives = 0
        # when history_ns > 0, keep per-market (rx_ns, side, price, qty_before) for
        # the trailing window so callers can reconstruct slightly earlier states
        self.history_ns = history_ns
        self.history: dict[str, deque] = {}

    def book(self, ticker: str) -> OrderBook:
        b = self.books.get(ticker)
        if b is None:
            b = self.books[ticker] = OrderBook()
            self.stale[ticker] = True
        return b

    def _mark_all_stale(self) -> None:
        for t in self.stale:
            self.stale[t] = True

    def feed(self, rec: Record) -> BookUpdate | RestCheck | None:
        raw = rec.raw
        t = raw.get("type")
        if t == "_local":
            ev = raw.get("event")
            if ev in ("connect", "disconnect"):
                self._mark_all_stale()
                self.last_seq.clear()
            elif ev == "resync":
                for tk in raw.get("markets") or []:
                    self.book(tk)
                    self.stale[tk] = True
            elif ev == "markets_sync":
                # unsubscribed markets receive no further deltas; their book is unknown
                for tk in raw.get("delete") or []:
                    if tk in self.books:
                        self.stale[tk] = True
            elif ev == "rest_snapshot":
                tk = raw["market_ticker"]
                rest = OrderBook.from_levels(raw.get("yes") or [], raw.get("no") or [])
                live = None if self.stale.get(tk, True) else self.book(tk).copy()
                return RestCheck(rec.rx_ns, tk, rest, live)
            return None
        sid, seq = raw.get("sid", 0), raw.get("seq", 0)
        if sid and seq:
            # every message on a sid consumes a seq, including ok responses
            last = self.last_seq.get(sid)
            if last is not None and seq != last + 1:
                self.gaps += 1
                if t in ("orderbook_snapshot", "orderbook_delta"):
                    # The collector marks every market on the sid stale; we do
                    # not know sid membership offline, so mirror it conservatively.
                    self._mark_all_stale()
            self.last_seq[sid] = seq
        if t not in ("orderbook_snapshot", "orderbook_delta"):
            return None

        msg = raw["msg"]
        tk = msg["market_ticker"]
        b = self.book(tk)
        if t == "orderbook_snapshot":
            b.apply_snapshot(msg)
            self.stale[tk] = False
            self.history.pop(tk, None)
            return BookUpdate(rec.rx_ns, tk, b, "snapshot")
        if self.stale[tk]:
            return None
        if self.history_ns:
            h = self.history.setdefault(tk, deque())  # noqa: E501
            h.append((rec.rx_ns, msg["side"], parse_price(msg["price_dollars"]), b.side(msg["side"]).get(parse_price(msg["price_dollars"]), 0)))
            while h and h[0][0] < rec.rx_ns - self.history_ns:
                h.popleft()
        try:
            b.apply_delta(msg)
        except NegativeQty:
            self.negatives += 1
            self.stale[tk] = True
            return None
        side, price = msg["side"], parse_price(msg["price_dollars"])
        return BookUpdate(rec.rx_ns, tk, b, "delta", side, price, b.side(side).get(price, 0))


def replay(records: Iterable[Record]) -> Iterator[BookUpdate | RestCheck]:
    r = Replayer()
    for rec in records:
        out = r.feed(rec)
        if out is not None:
            yield out


def matches_within(r: Replayer, ticker: str, rest: OrderBook, rx_ns: int, window_ns: int) -> tuple[int, float | None]:
    """Smallest level-diff between `rest` and the market's book at any instant in
    [rx_ns - window, rx_ns], by undoing recent deltas in reverse. Returns
    (min_diff, offset_ms of the best match). A REST snapshot is taken before
    its response reaches us, so a busy book legitimately differs at rx_ns."""
    live = r.books[ticker]
    have = {("yes", p): q for p, q in live.yes.items()} | {("no", p): q for p, q in live.no.items()}
    want = {("yes", p): q for p, q in rest.yes.items()} | {("no", p): q for p, q in rest.no.items()}
    diff = sum(1 for k in set(have) | set(want) if have.get(k, 0) != want.get(k, 0))
    best, best_off = diff, 0.0
    for t, side, price, before in reversed(r.history.get(ticker, ())):
        if t < rx_ns - window_ns:
            break
        k = (side, price)
        w = want.get(k, 0)
        was_diff = have.get(k, 0) != w
        if before:
            have[k] = before
        else:
            have.pop(k, None)
        diff += (have.get(k, 0) != w) - was_diff
        if diff < best:
            best, best_off = diff, (t - rx_ns) / 1e6
            if best == 0:
                break
    return best, best_off
