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
    """Yield records from one file.

    Records are one JSON object per line. Files written before the recorder
    trimmed trailing newlines from exchange frames have the closing brace on
    the following line; those are joined transparently. A truncated final
    line (file still being written) is skipped.
    """
    with gzip.open(path, "rb") as f:
        pending = b""
        for line in f:
            if not line.strip():
                continue
            chunk = pending + line
            try:
                obj = orjson.loads(chunk)
            except orjson.JSONDecodeError:
                if pending or len(chunk) > 64 << 20:
                    pending = b""  # give up on an unrecoverable fragment
                else:
                    pending = chunk
                continue
            pending = b""
            yield Record(obj["rx_ns"], obj["raw"])


def iter_records(data_dir: Path, start: date, end: date | None = None) -> Iterator[Record]:
    for p in raw_files(data_dir, start, end):
        yield from iter_file(p)
