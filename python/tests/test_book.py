import json
from pathlib import Path

import pytest

from kalshi_data.book import NegativeQty, OrderBook, fmt_price, parse_price, parse_qty

FIXTURES = Path(__file__).resolve().parents[2] / "testdata" / "book_cases.json"


def _cases():
    return json.loads(FIXTURES.read_text())["cases"]


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c["name"])
def test_shared_fixture(case):
    b = OrderBook()
    err = None
    for env in case["messages"]:
        try:
            if env["type"] == "orderbook_snapshot":
                b.apply_snapshot(env["msg"])
            elif env["type"] == "orderbook_delta":
                b.apply_delta(env["msg"])
            else:
                raise AssertionError(env["type"])
        except NegativeQty as e:
            err = e
            break
    if "expect_error" in case:
        assert case["expect_error"] == "negative" and isinstance(err, NegativeQty)
        return
    assert err is None
    want = OrderBook.from_levels(case["expected"]["yes"], case["expected"]["no"])
    assert b.diff(want) == []
    if "top" in case:
        top = b.top()
        got = {
            "bid": fmt_price(top.bid[0]) if top.bid else None,
            "ask": fmt_price(top.ask[0]) if top.ask else None,
            "spread": fmt_price(top.spread) if top.spread is not None else None,
            "mid": fmt_price(top.mid) if top.mid is not None else None,
        }
        assert got == case["top"]


def test_parse_and_format():
    assert parse_price("0.0800") == 800
    assert parse_price("0.960") == 9600
    assert parse_price("1") == 10_000
    assert parse_qty("-54.00") == -5400
    assert fmt_price(5025) == "0.5025"
    with pytest.raises(Exception):
        parse_price("0.12345")
    with pytest.raises(Exception):
        parse_price("1.0001")
