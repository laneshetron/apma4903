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


def frames(path: Path) -> list[tuple[int, int, int, int]]:
    """Frame table from a .idx sidecar: (byte_offset, first_rx_ns, last_rx_ns, records).

    Written by the Go recorder under CodecZstd. Each frame decompresses on its own
    starting at byte_offset, so a caller wanting a time slice can skip the rest.
    Returns [] when there is no index.
    """
    idx = path.with_suffix("").with_suffix(".idx") if path.name.endswith(".jsonl.zst") else None
    if idx is None or not idx.exists():
        return []
    out = []
    for line in idx.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        a, b, c, d = line.split(",")
        out.append((int(a), int(b), int(c), int(d)))
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


def iter_file(path: Path, since_ns: int | None = None, until_ns: int | None = None) -> Iterator[Record]:
    """Yield records from one file, optionally restricted to [since_ns, until_ns].

    When the file has a frame index and a bound is given, frames that cannot
    contain the range are skipped without being decompressed.

    Records are one JSON object per line. Files written before the recorder
    trimmed trailing newlines from exchange frames have the closing brace on
    the following line; those are joined transparently. A truncated final
    line (file still being written) is skipped.
    """
    if (since_ns is not None or until_ns is not None) and (tab := frames(path)):
        lo, hi = since_ns or -(1 << 62), until_ns or (1 << 62)
        want = [(off, end) for (off, first, last, _), end in
                zip(tab, [t[0] for t in tab[1:]] + [None]) if not (last < lo or first > hi)]
        if not want:
            return
        import zstandard
        dec = zstandard.ZstdDecompressor()
        with path.open("rb") as fh:
            for off, end in want:
                fh.seek(off)
                blob = fh.read(end - off) if end is not None else fh.read()
                for line in dec.decompressobj().decompress(blob).split(b"\n"):
                    if not line.strip():
                        continue
                    try:
                        obj = orjson.loads(line)
                    except orjson.JSONDecodeError:
                        continue
                    if lo <= obj["rx_ns"] <= hi:
                        yield Record(obj["rx_ns"], obj["raw"])
        return

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


def iter_records(data_dir: Path, start: date, end: date | None = None,
                 since_ns: int | None = None, until_ns: int | None = None) -> Iterator[Record]:
    for p in raw_files(data_dir, start, end):
        yield from iter_file(p, since_ns, until_ns)


def _lines_until_truncation(f) -> Iterator[bytes]:
    """Iterate lines, stopping cleanly at a truncated gzip stream (a file the
    collector is still writing has no end-of-stream marker yet)."""
    try:
        yield from f
    except EOFError:
        return
