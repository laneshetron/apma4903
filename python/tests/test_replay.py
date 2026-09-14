import gzip
from datetime import date
from pathlib import Path

import orjson

from kalshi_data.raw import iter_records
from kalshi_data.replay import BookUpdate, RestCheck, replay
from kalshi_data.to_parquet import convert
from kalshi_data.validate import validate


def _write_day(data_dir: Path, day: date, lines: list[tuple[int, dict]], legacy_split: bool = False) -> None:
    d = data_dir / "raw" / day.isoformat()
    d.mkdir(parents=True)
    with gzip.open(d / "00.jsonl.gz", "wb") as f:
        for rx, raw in lines:
            rec = orjson.dumps({"rx_ns": rx, "raw": raw})
            if legacy_split and raw.get("type") != "_local":
                rec = rec[:-1] + b"\n}"  # closing brace on its own line, as early files have
            f.write(rec + b"\n")


def test_legacy_split_records(tmp_path):
    day = date(2026, 9, 14)
    _write_day(tmp_path, day, LINES, legacy_split=True)
    recs = list(iter_records(tmp_path, day))
    assert len(recs) == len(LINES)
    assert [r.raw for r in recs] == [raw for _, raw in LINES]


def _snap(sid, seq, tk, yes, no):
    return {"type": "orderbook_snapshot", "sid": sid, "seq": seq,
            "msg": {"market_ticker": tk, "yes_dollars_fp": yes, "no_dollars_fp": no}}


def _delta(sid, seq, tk, side, price, d):
    return {"type": "orderbook_delta", "sid": sid, "seq": seq,
            "msg": {"market_ticker": tk, "side": side, "price_dollars": price, "delta_fp": d, "ts_ms": 1}}


LINES = [
    (1, {"type": "_local", "event": "connect", "gen": 1}),
    (2, {"id": 1, "type": "subscribed", "msg": {"channel": "orderbook_delta", "sid": 1}}),
    (3, _snap(1, 1, "A", [["0.5000", "10.00"]], [["0.4000", "5.00"]])),
    (4, _delta(1, 2, "A", "yes", "0.5100", "3.00")),
    (4, {"id": 9, "type": "ok", "sid": 1, "seq": 3, "msg": {"market_tickers": []}}),  # consumes seq 3; not a gap
    (5, {"type": "trade", "sid": 2, "seq": 1, "msg": {"market_ticker": "A", "trade_id": "t1", "yes_price_dollars": "0.5000",
         "no_price_dollars": "0.5000", "count_fp": "1.00", "taker_side": "yes", "is_block_trade": False, "ts_ms": 1}}),
    # REST agrees with the live book
    (6, {"type": "_local", "event": "rest_snapshot", "market_ticker": "A", "yes": [["0.5000", "10.00"], ["0.5100", "3.00"]], "no": [["0.4000", "5.00"]]}),
    # gap 2 -> 4: A stale; delta ignored; snapshot restores
    (7, _delta(1, 5, "A", "yes", "0.5100", "100.00")),
    (8, {"type": "_local", "event": "gap", "sid": 1, "expected": 4, "got": 5}),
    (9, {"type": "_local", "event": "rest_snapshot", "market_ticker": "A", "yes": [], "no": []}),  # skipped: stale
    (10, _snap(1, 6, "A", [["0.6000", "1.00"]], [])),
    (11, {"type": "_local", "event": "rest_snapshot", "market_ticker": "A", "yes": [["0.6000", "2.00"]], "no": []}),  # mismatch
    (12, {"type": "_local", "event": "disconnect", "gen": 1, "err": "eof"}),
]


def test_replay_and_validate(tmp_path, capsys):
    day = date(2026, 9, 14)
    _write_day(tmp_path, day, LINES)
    events = list(replay(iter_records(tmp_path, day)))
    kinds = [(type(e).__name__, getattr(e, "kind", None)) for e in events]
    assert kinds == [("BookUpdate", "snapshot"), ("BookUpdate", "delta"), ("RestCheck", None),
                     ("RestCheck", None), ("BookUpdate", "snapshot"), ("RestCheck", None)]
    ok, skipped, bad = events[2], events[3], events[5]
    assert isinstance(ok, RestCheck) and ok.live is not None and ok.live.diff(ok.rest) == []
    assert isinstance(skipped, RestCheck) and skipped.live is None
    assert isinstance(bad, RestCheck) and bad.live is not None and bad.live.diff(bad.rest) == [("yes", 6000, 100, 200)]
    assert isinstance(events[4], BookUpdate) and events[4].book.bids("yes") == [(6000, 100)]

    assert validate(tmp_path, day, verbose=True) == 1  # the final mismatch never reconciles
    out = capsys.readouterr().out
    assert "seq gaps: 1" in out and "differed at receive time: 1" in out and "skipped (stale): 1" in out and "FAILED" in out

    counts = convert(tmp_path, day)
    assert counts == {"orderbook_snapshot_levels": 3, "orderbook_delta": 2, "trade": 1, "local_event": 6}
    import polars as pl
    df = pl.read_parquet(tmp_path / "parquet" / "orderbook_delta" / f"date={day}" / "part-0.parquet")
    assert df["price"].to_list() == [5100, 5100] and df["delta"].to_list() == [300, 10000]
