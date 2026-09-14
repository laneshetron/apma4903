import json
from pathlib import Path

from kalshi_data.raw import Record
from kalshi_data.spot import SpotQuote, SpotTrade, normalize

FIX = Path(__file__).resolve().parents[2] / "testdata" / "spot"


def _load(venue):
    out = []
    for line in (FIX / f"{venue}.jsonl").read_text().splitlines():
        obj = json.loads(line)
        out += list(normalize(venue, Record(obj["rx_ns"], obj["raw"])))
    return out


def test_coinbase():
    ev = _load("coinbase")
    trades = [e for e in ev if isinstance(e, SpotTrade)]
    quotes = [e for e in ev if isinstance(e, SpotQuote)]
    assert trades and quotes
    t = next(e for e in trades if e.asset == "BTC")
    assert t.price == 77522.57 and t.side == "sell" and t.ts_ms == 1789364889675  # maker buy -> taker sell
    q = quotes[0]
    assert q.asset == "ETH" and q.bid == 2512.48 and q.ask == 2512.49 and q.ts_ms == 1789364888447


def test_kraken():
    ev = _load("kraken")
    t = next(e for e in ev if isinstance(e, SpotTrade))
    assert t.asset == "BTC" and t.price == 77525.4 and t.side == "buy" and t.ts_ms == 1789364892383
    q = next(e for e in ev if isinstance(e, SpotQuote))
    assert q.bid == 77525.3 and q.ask == 77525.4 and q.ts_ms == 1789364889947


def test_bitstamp():
    t = next(e for e in _load("bitstamp") if isinstance(e, SpotTrade))
    assert t.asset == "BTC" and t.price == 77523.34 and t.size == 0.00012899 and t.side == "sell" and t.ts_ms == 1789364890223


def test_gemini():
    t = next(e for e in _load("gemini_btc") if isinstance(e, SpotTrade))
    assert t.asset == "BTC" and t.price == 77524.18 and t.side == "sell" and t.ts_ms == 1789364906855
