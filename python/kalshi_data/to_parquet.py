"""Convert one day of raw logs into typed Parquet tables.

    uv run python -m kalshi_data.to_parquet 2026-09-14 [--data-dir ../data]

Writes <data_dir>/parquet/<table>/date=YYYY-MM-DD/part-0.parquet for tables
orderbook_snapshot_levels, orderbook_delta, trade, local_event.
Prices are int32 in 1/10000 dollar; quantities int64 in 1/100 contract.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import orjson
import polars as pl

from .book import parse_price, parse_qty
from .raw import iter_records

SCHEMAS = {
    "orderbook_snapshot_levels": {
        "rx_ns": pl.Int64, "sid": pl.Int64, "seq": pl.Int64, "ticker": pl.Utf8,
        "side": pl.Utf8, "price": pl.Int32, "qty": pl.Int64,
    },
    "orderbook_delta": {
        "rx_ns": pl.Int64, "sid": pl.Int64, "seq": pl.Int64, "ticker": pl.Utf8,
        "side": pl.Utf8, "price": pl.Int32, "delta": pl.Int64, "ts_ms": pl.Int64,
    },
    "trade": {
        "rx_ns": pl.Int64, "sid": pl.Int64, "seq": pl.Int64, "ticker": pl.Utf8,
        "trade_id": pl.Utf8, "yes_price": pl.Int32, "no_price": pl.Int32, "count": pl.Int64,
        "taker_side": pl.Utf8, "is_block_trade": pl.Boolean, "ts_ms": pl.Int64,
    },
    "local_event": {"rx_ns": pl.Int64, "event": pl.Utf8, "payload": pl.Utf8},
}


def convert(data_dir: Path, day: date) -> dict[str, int]:
    rows: dict[str, list[dict]] = {k: [] for k in SCHEMAS}
    for rec in iter_records(data_dir, day):
        raw, t = rec.raw, rec.type
        if t == "_local":
            payload = {k: v for k, v in raw.items() if k not in ("type", "event")}
            rows["local_event"].append({"rx_ns": rec.rx_ns, "event": raw.get("event"), "payload": orjson.dumps(payload).decode()})
            continue
        msg = raw.get("msg") or {}
        base = {"rx_ns": rec.rx_ns, "sid": raw.get("sid"), "seq": raw.get("seq"), "ticker": msg.get("market_ticker")}
        if t == "orderbook_snapshot":
            for side in ("yes", "no"):
                for price, qty in msg.get(f"{side}_dollars_fp") or []:
                    rows["orderbook_snapshot_levels"].append({**base, "side": side, "price": parse_price(price), "qty": parse_qty(qty)})
        elif t == "orderbook_delta":
            rows["orderbook_delta"].append({**base, "side": msg["side"], "price": parse_price(msg["price_dollars"]),
                                            "delta": parse_qty(msg["delta_fp"]), "ts_ms": msg.get("ts_ms")})
        elif t == "trade":
            rows["trade"].append({**base, "trade_id": msg.get("trade_id"),
                                  "yes_price": parse_price(msg["yes_price_dollars"]), "no_price": parse_price(msg["no_price_dollars"]),
                                  "count": parse_qty(msg["count_fp"]), "taker_side": msg.get("taker_side"),
                                  "is_block_trade": bool(msg.get("is_block_trade")), "ts_ms": msg.get("ts_ms")})
    counts = {}
    for table, schema in SCHEMAS.items():
        df = pl.DataFrame(rows[table], schema=schema, orient="row")
        out = data_dir / "parquet" / table / f"date={day.isoformat()}"
        out.mkdir(parents=True, exist_ok=True)
        df.write_parquet(out / "part-0.parquet")
        counts[table] = len(df)
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, default=Path("../data"))
    a = ap.parse_args()
    for table, n in convert(a.data_dir, a.day).items():
        print(f"{table:28s} {n:>10d} rows")


if __name__ == "__main__":
    main()
