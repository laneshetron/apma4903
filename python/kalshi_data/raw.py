"""Read the collector's raw logs: <data_dir>/raw/YYYY-MM-DD/HH.jsonl.{gz,zst}.

The collector writes gzip; archived tapes may be recompressed to zstd
(`deploy/recompress.sh`), which is ~45% smaller and faster to read. Both
extensions are picked up transparently, newest-format-first per hour."""

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
            # one entry per hour; prefer .zst when both exist (a half-finished
            # recompression leaves the .gz in place)
            by_hour: dict[str, Path] = {}
            for pat in ("*.jsonl.gz", "*.jsonl.zst"):
                for f in day_dir.glob(pat):
                    by_hour[f.name.split(".", 1)[0]] = f
            out.extend(p for _, p in sorted(by_hour.items()))
        d = d.fromordinal(d.toordinal() + 1)
    return out


def _open(path: Path):
    """Binary line-reader for a .gz or .zst tape file."""
    if path.suffix == ".zst":
        import io

        import zstandard
        # read_across_frames: a multi-threaded zstd writes one frame per chunk
        rdr = zstandard.ZstdDecompressor().stream_reader(
            path.open("rb"), read_across_frames=True, closefd=True)
        return io.BufferedReader(rdr, buffer_size=1 << 22)
    return gzip.open(path, "rb")


def iter_file(path: Path) -> Iterator[Record]:
    """Yield records from one file.

    Records are one JSON object per line. Files written before the recorder
    trimmed trailing newlines from exchange frames have the closing brace on
    the following line; those are joined transparently. A truncated final
    line (file still being written) is skipped.
    """
    with _open(path) as f:
        pending = b""
        for line in _lines_until_truncation(f):
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


def _lines_until_truncation(f) -> Iterator[bytes]:
    """Iterate lines, stopping cleanly at a truncated gzip stream (a file the
    collector is still writing has no end-of-stream marker yet)."""
    try:
        yield from f
    except EOFError:
        return
