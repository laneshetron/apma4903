"""Rebuild order books from a raw log, honoring the collector's local events.

A market's book is invalid ("stale") from a connect/disconnect/gap/resync
event until its next orderbook_snapshot, exactly as in the live collector.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from .book import NegativeQty, OrderBook
from .raw import Record


@dataclass(slots=True)
class BookUpdate:
    rx_ns: int
    ticker: str
    book: OrderBook  # live reference; copy() to keep
    kind: str  # "snapshot" | "delta"


@dataclass(slots=True)
class RestCheck:
    rx_ns: int
    ticker: str
    rest: OrderBook
    live: OrderBook | None  # None if the live book was stale at that moment


class Replayer:
    def __init__(self) -> None:
        self.books: dict[str, OrderBook] = {}
        self.stale: dict[str, bool] = {}
        self.last_seq: dict[int, int] = {}
        self.gaps = 0
        self.negatives = 0

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
            elif ev == "rest_snapshot":
                tk = raw["market_ticker"]
                rest = OrderBook.from_levels(raw.get("yes") or [], raw.get("no") or [])
                live = None if self.stale.get(tk, True) else self.book(tk).copy()
                return RestCheck(rec.rx_ns, tk, rest, live)
            return None
        if t not in ("orderbook_snapshot", "orderbook_delta"):
            return None

        sid, seq = raw.get("sid", 0), raw.get("seq", 0)
        if seq:
            last = self.last_seq.get(sid)
            if last is not None and seq != last + 1:
                self.gaps += 1
                # The collector marks every market on the sid stale; we do not
                # know sid membership offline, so mirror it conservatively.
                self._mark_all_stale()
            self.last_seq[sid] = seq

        msg = raw["msg"]
        tk = msg["market_ticker"]
        b = self.book(tk)
        if t == "orderbook_snapshot":
            b.apply_snapshot(msg)
            self.stale[tk] = False
            return BookUpdate(rec.rx_ns, tk, b, "snapshot")
        if self.stale[tk]:
            return None
        try:
            b.apply_delta(msg)
        except NegativeQty:
            self.negatives += 1
            self.stale[tk] = True
            return None
        return BookUpdate(rec.rx_ns, tk, b, "delta")


def replay(records: Iterable[Record]) -> Iterator[BookUpdate | RestCheck]:
    r = Replayer()
    for rec in records:
        out = r.feed(rec)
        if out is not None:
            yield out
