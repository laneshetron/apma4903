"""Read the collector's raw logs: <data_dir>/raw/YYYY-MM-DD/HH.jsonl.gz."""

from __future__ import annotations

import gzip
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import orjson


@dataclass(slots=True)
class Record:
    rx_ns: int
    raw: dict  # the message verbatim; collector events have type "_local"

    @property
    def type(self) -> str:
        return self.raw.get("type", "")

    @property
    def is_local(self) -> bool:
        return self.type == "_local"


def raw_files(data_dir: Path, start: date, end: date | None = None) -> list[Path]:
    """Hourly files for days in [start, end], sorted."""
    end = end or start
    out: list[Path] = []
    d = start
    while d <= end:
        day_dir = data_dir / "raw" / d.isoformat()
        if day_dir.is_dir():
            out.extend(sorted(day_dir.glob("*.jsonl.gz")))
        d = d.fromordinal(d.toordinal() + 1)
    return out


def iter_file(path: Path) -> Iterator[Record]:
    with gzip.open(path, "rb") as f:
        for line in f:
            if not line.strip():
                continue
            obj = orjson.loads(line)
            yield Record(obj["rx_ns"], obj["raw"])


def iter_records(data_dir: Path, start: date, end: date | None = None) -> Iterator[Record]:
    for p in raw_files(data_dir, start, end):
        yield from iter_file(p)
