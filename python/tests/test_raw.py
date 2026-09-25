"""Tape files may be archived as zstd; the reader must treat both codecs alike."""

from __future__ import annotations

import gzip
import json
from datetime import date
from pathlib import Path

import pytest

from kalshi_data.raw import iter_records, raw_files

DAY = date(2026, 9, 20)


def _records() -> list[dict]:
    return [
        {"rx_ns": 1_000 + i, "raw": {"type": "orderbook_delta", "msg": {"market_ticker": f"KXT-{i % 3}", "side": "yes"}}}
        for i in range(500)
    ]


def _write(dir_: Path, name: str, recs: list[dict]) -> Path:
    day = dir_ / "raw" / DAY.isoformat()
    day.mkdir(parents=True, exist_ok=True)
    body = b"".join(json.dumps(r).encode() + b"\n" for r in recs)
    p = day / name
    if name.endswith(".zst"):
        zstandard = pytest.importorskip("zstandard")
        p.write_bytes(zstandard.ZstdCompressor(level=3).compress(body))
    else:
        p.write_bytes(gzip.compress(body))
    return p


def test_reads_zstd_identically_to_gzip(tmp_path: Path) -> None:
    recs = _records()
    a, b = tmp_path / "gz", tmp_path / "zst"
    _write(a, "07.jsonl.gz", recs)
    _write(b, "07.jsonl.zst", recs)
    got_gz = [(r.rx_ns, r.raw) for r in iter_records(a, DAY)]
    got_zst = [(r.rx_ns, r.raw) for r in iter_records(b, DAY)]
    assert len(got_gz) == len(recs)
    assert got_gz == got_zst


def test_zstd_preferred_when_both_present(tmp_path: Path) -> None:
    """A half-finished recompression leaves both; the hour must be read once."""
    _write(tmp_path, "07.jsonl.gz", _records())
    _write(tmp_path, "07.jsonl.zst", _records())
    files = raw_files(tmp_path, DAY)
    assert [p.name for p in files] == ["07.jsonl.zst"]
    assert len(list(iter_records(tmp_path, DAY))) == 500


def test_hours_stay_in_order_across_codecs(tmp_path: Path) -> None:
    _write(tmp_path, "08.jsonl.gz", _records())
    _write(tmp_path, "07.jsonl.zst", _records())
    _write(tmp_path, "09.jsonl.gz", _records())
    assert [p.name for p in raw_files(tmp_path, DAY)] == ["07.jsonl.zst", "08.jsonl.gz", "09.jsonl.gz"]
