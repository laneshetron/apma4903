"""Reference order book, mirroring internal/book in Go exactly.

Prices are ints in 1/10000 dollar, quantities ints in 1/100 contract. The
book is bids-only on both sides: a YES bid at p is a NO ask at 10000 - p.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

ONE_DOLLAR = 10_000
PRICE_SCALE = Decimal(10_000)
QTY_SCALE = Decimal(100)


class BookError(Exception):
    pass


class NegativeQty(BookError):
    """A delta drove a level below zero: the local book has diverged."""


def parse_price(s: str) -> int:
    try:
        d = Decimal(s) * PRICE_SCALE
    except InvalidOperation as e:
        raise BookError(f"bad price {s!r}") from e
    if d != d.to_integral_value():
        raise BookError(f"price {s!r} has more than 4 decimals")
    v = int(d)
    if not 0 <= v <= ONE_DOLLAR:
        raise BookError(f"price {s!r} out of range")
    return v


def parse_qty(s: str) -> int:
    try:
        d = Decimal(s) * QTY_SCALE
    except InvalidOperation as e:
        raise BookError(f"bad qty {s!r}") from e
    if d != d.to_integral_value():
        raise BookError(f"qty {s!r} has more than 2 decimals")
    return int(d)


def fmt_price(p: int) -> str:
    return f"{p // ONE_DOLLAR}.{p % ONE_DOLLAR:04d}"


def fmt_qty(q: int) -> str:
    sign = "-" if q < 0 else ""
    q = abs(q)
    return f"{sign}{q // 100}.{q % 100:02d}"


@dataclass(slots=True)
class Top:
    bid: tuple[int, int] | None  # (price, qty)
    ask: tuple[int, int] | None  # implied from best NO bid

    @property
    def spread(self) -> int | None:
        if self.bid is None or self.ask is None:
            return None
        return self.ask[0] - self.bid[0]

    @property
    def mid(self) -> int | None:
        if self.bid is None or self.ask is None:
            return None
        return (self.ask[0] + self.bid[0]) // 2


@dataclass(slots=True)
class OrderBook:
    yes: dict[int, int] = field(default_factory=dict)
    no: dict[int, int] = field(default_factory=dict)

    def side(self, side: str) -> dict[int, int]:
        if side == "yes":
            return self.yes
        if side == "no":
            return self.no
        raise BookError(f"unknown side {side!r}")

    def apply_snapshot(self, msg: dict) -> None:
        """Replace the book from an orderbook_snapshot msg body."""
        self.yes = _levels(msg.get("yes_dollars_fp") or [])
        self.no = _levels(msg.get("no_dollars_fp") or [])

    def apply_delta(self, msg: dict) -> None:
        """Apply an orderbook_delta msg body. Leaves the book unchanged on NegativeQty."""
        m = self.side(msg["side"])
        p = parse_price(msg["price_dollars"])
        q = m.get(p, 0) + parse_qty(msg["delta_fp"])
        if q < 0:
            raise NegativeQty(f"{msg['side']} @ {msg['price_dollars']} -> {fmt_qty(q)}")
        if q == 0:
            m.pop(p, None)
        else:
            m[p] = q

    @classmethod
    def from_levels(cls, yes: list, no: list) -> OrderBook:
        return cls(_levels(yes), _levels(no))

    def bids(self, side: str) -> list[tuple[int, int]]:
        return sorted(self.side(side).items(), reverse=True)

    def best_bid(self, side: str) -> tuple[int, int] | None:
        b = self.bids(side)
        return b[0] if b else None

    def best_ask(self, side: str) -> tuple[int, int] | None:
        other = self.best_bid("no" if side == "yes" else "yes")
        if other is None:
            return None
        return (ONE_DOLLAR - other[0], other[1])

    def top(self) -> Top:
        return Top(self.best_bid("yes"), self.best_ask("yes"))

    def diff(self, other: OrderBook) -> list[tuple[str, int, int, int]]:
        """Levels that differ: (side, price, have, want), best-first per side."""
        out = []
        for side in ("yes", "no"):
            have, want = self.side(side), other.side(side)
            for p in sorted(set(have) | set(want), reverse=True):
                if have.get(p, 0) != want.get(p, 0):
                    out.append((side, p, have.get(p, 0), want.get(p, 0)))
        return out

    def copy(self) -> OrderBook:
        return OrderBook(dict(self.yes), dict(self.no))

    def to_wire(self) -> dict:
        return {
            "yes": [[fmt_price(p), fmt_qty(q)] for p, q in self.bids("yes")],
            "no": [[fmt_price(p), fmt_qty(q)] for p, q in self.bids("no")],
        }


def _levels(levels: list) -> dict[int, int]:
    out: dict[int, int] = {}
    for price, qty in levels:
        q = parse_qty(qty)
        if q != 0:
            out[parse_price(price)] = q
    return out
