"""Normalize recorded spot-exchange frames (data/spot/<venue>/raw/...) into
trades and top-of-book quotes.

Spot venues: coinbase, kraken, bitstamp, gemini_btc / gemini_eth. Perp
venues: coinbase_perp (INTX via Advanced Trade), kraken_futures, okx, bybit,
hyperliquid. Times are unix ms from the exchange; rx_ns is our receive time.
Trade side is the TAKER's side ("buy" = taker bought the asset); sizes are in
units of the asset.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from .raw import Record, iter_records


@dataclass(slots=True)
class SpotTrade:
    rx_ns: int
    venue: str
    asset: str      # BTC, ETH
    price: float
    size: float
    side: str       # taker side: buy | sell
    ts_ms: int      # exchange time


@dataclass(slots=True)
class SpotQuote:
    rx_ns: int
    venue: str
    asset: str
    bid: float
    ask: float
    ts_ms: int | None  # exchange time when the venue provides one


def _iso_ms(s: str) -> int:
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1000)


def _asset(sym: str) -> str:
    a = sym.split("-")[0].split("/")[0].upper()
    return {"PF_XBTUSD": "BTC", "PF_ETHUSD": "ETH", "BTCUSDT": "BTC", "ETHUSDT": "ETH", "XBT": "BTC"}.get(a, a)


# OKX USDT swaps are quoted in contracts of a fixed asset amount
_OKX_CONTRACT = {"BTC": 0.01, "ETH": 0.1}


def normalize(venue: str, rec: Record) -> Iterator[SpotTrade | SpotQuote]:
    raw = rec.raw
    if raw.get("type") == "_local":
        return
    if venue == "coinbase":
        t = raw.get("type")
        if t == "match" or t == "last_match":
            # side is the MAKER side on Coinbase; taker is the opposite
            yield SpotTrade(rec.rx_ns, venue, _asset(raw["product_id"]), float(raw["price"]), float(raw["size"]),
                            "sell" if raw["side"] == "buy" else "buy", _iso_ms(raw["time"]))
        elif t == "ticker" and raw.get("best_bid"):
            yield SpotQuote(rec.rx_ns, venue, _asset(raw["product_id"]), float(raw["best_bid"]), float(raw["best_ask"]), _iso_ms(raw["time"]))
    elif venue == "kraken":
        ch = raw.get("channel")
        if ch == "trade":
            for d in raw.get("data", []):
                yield SpotTrade(rec.rx_ns, venue, _asset(d["symbol"]), float(d["price"]), float(d["qty"]), d["side"], _iso_ms(d["timestamp"]))
        elif ch == "ticker":
            for d in raw.get("data", []):
                yield SpotQuote(rec.rx_ns, venue, _asset(d["symbol"]), float(d["bid"]), float(d["ask"]), _iso_ms(d["timestamp"]) if d.get("timestamp") else None)
    elif venue == "bitstamp":
        if raw.get("event") == "trade":
            d = raw["data"]
            asset = raw["channel"].removeprefix("live_trades_").removesuffix("usd").upper()
            yield SpotTrade(rec.rx_ns, venue, asset, float(d["price"]), float(d["amount"]),
                            "buy" if d["type"] == 0 else "sell", int(d["microtimestamp"]) // 1000)
    elif venue == "coinbase_perp":
        ch = raw.get("channel")
        if ch == "market_trades":
            for e in raw.get("events", []):
                if e.get("type") != "update":
                    continue
                for t in e.get("trades", []):
                    # side is the MAKER side, as on the Exchange feed (checked against the quote)
                    yield SpotTrade(rec.rx_ns, venue, _asset(t["product_id"]), float(t["price"]), float(t["size"]),
                                    "sell" if t["side"] == "BUY" else "buy", _iso_ms(t["time"]))
        elif ch == "ticker":
            ts = _iso_ms(raw["timestamp"])
            for e in raw.get("events", []):
                for t in e.get("tickers", []):
                    if t.get("best_bid") and t.get("best_ask"):
                        yield SpotQuote(rec.rx_ns, venue, _asset(t["product_id"]), float(t["best_bid"]), float(t["best_ask"]), ts)
    elif venue == "kraken_futures":
        feed = raw.get("feed")
        if feed == "trade" and raw.get("type") == "fill":
            yield SpotTrade(rec.rx_ns, venue, _asset(raw["product_id"]), float(raw["price"]), float(raw["qty"]), raw["side"], int(raw["time"]))
        elif feed == "ticker" and raw.get("bid") is not None:
            yield SpotQuote(rec.rx_ns, venue, _asset(raw["product_id"]), float(raw["bid"]), float(raw["ask"]), int(raw["time"]))
    elif venue == "okx":
        ch = (raw.get("arg") or {}).get("channel")
        if ch == "trades" and "data" in raw:
            for d in raw["data"]:
                asset = _asset(d["instId"])
                yield SpotTrade(rec.rx_ns, venue, asset, float(d["px"]), float(d["sz"]) * _OKX_CONTRACT.get(asset, 1.0), d["side"], int(d["ts"]))
        elif ch == "bbo-tbt" and "data" in raw:
            asset = _asset(raw["arg"]["instId"])
            for d in raw["data"]:
                if d.get("bids") and d.get("asks"):
                    yield SpotQuote(rec.rx_ns, venue, asset, float(d["bids"][0][0]), float(d["asks"][0][0]), int(d["ts"]))
    elif venue == "bybit":
        topic = raw.get("topic", "")
        if topic.startswith("publicTrade."):
            for d in raw.get("data", []):
                yield SpotTrade(rec.rx_ns, venue, _asset(d["s"]), float(d["p"]), float(d["v"]), d["S"].lower(), int(d["T"]))
        elif topic.startswith("orderbook.1."):
            d = raw.get("data", {})
            if d.get("b") and d.get("a"):
                yield SpotQuote(rec.rx_ns, venue, _asset(d["s"]), float(d["b"][0][0]), float(d["a"][0][0]), int(raw["ts"]))
    elif venue == "hyperliquid":
        ch = raw.get("channel")
        if ch == "trades":
            for d in raw.get("data", []):
                yield SpotTrade(rec.rx_ns, venue, d["coin"], float(d["px"]), float(d["sz"]), "buy" if d["side"] == "B" else "sell", int(d["time"]))
        elif ch == "bbo":
            d = raw.get("data", {})
            b, a = d.get("bbo", [None, None])
            if b and a:
                yield SpotQuote(rec.rx_ns, venue, d["coin"], float(b["px"]), float(a["px"]), int(d["time"]))
    elif venue.startswith("gemini"):
        if raw.get("type") == "update":
            asset = venue.split("_", 1)[1].upper() if "_" in venue else "BTC"
            ts = raw.get("timestampms")
            for e in raw.get("events", []):
                if e.get("type") == "trade" and ts is not None:
                    yield SpotTrade(rec.rx_ns, venue, asset, float(e["price"]), float(e["amount"]),
                                    "sell" if e["makerSide"] == "bid" else "buy", ts)


def iter_spot(data_dir: Path, venue: str, start: date, end: date | None = None) -> Iterator[SpotTrade | SpotQuote]:
    for rec in iter_records(data_dir / "spot" / venue, start, end):
        yield from normalize(venue, rec)


def venues(data_dir: Path) -> list[str]:
    d = data_dir / "spot"
    return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.is_dir() else []
