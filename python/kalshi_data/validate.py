"""Replay a day of raw logs and check reconstructed books against the REST
snapshots the collector recorded.

    uv run python -m kalshi_data.validate 2026-09-14 [--data-dir ../data] [-v]

REST and the stream are not atomically consistent, so a small number of
one-off mismatches is normal; the same market mismatching on consecutive
checks is not.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from .book import fmt_price, fmt_qty
from .raw import iter_records
from .replay import Replayer, RestCheck


def validate(data_dir: Path, day: date, verbose: bool = False) -> int:
    r = Replayer()
    checks: Counter[str] = Counter()
    mismatches: Counter[str] = Counter()
    skipped: Counter[str] = Counter()
    streak: dict[str, int] = defaultdict(int)
    persistent: set[str] = set()
    updates = 0
    for rec in iter_records(data_dir, day):
        out = r.feed(rec)
        if out is None:
            continue
        if not isinstance(out, RestCheck):
            updates += 1
            continue
        checks[out.ticker] += 1
        if out.live is None:
            skipped[out.ticker] += 1
            continue
        diff = out.live.diff(out.rest)
        if not diff:
            streak[out.ticker] = 0
            continue
        mismatches[out.ticker] += 1
        streak[out.ticker] += 1
        if streak[out.ticker] >= 2:
            persistent.add(out.ticker)
        if verbose:
            side, p, have, want = diff[0]
            print(f"{out.rx_ns} {out.ticker}: {len(diff)} levels differ; first {side} {fmt_price(p)} have={fmt_qty(have)} want={fmt_qty(want)}")

    print(f"book updates applied: {updates}")
    print(f"seq gaps: {r.gaps}   negative-qty divergences: {r.negatives}")
    print(f"rest checks: {sum(checks.values())} across {len(checks)} markets; "
          f"mismatched: {sum(mismatches.values())}; skipped (stale): {sum(skipped.values())}")
    if persistent:
        print("PERSISTENT mismatches (>=2 consecutive checks):", ", ".join(sorted(persistent)))
        return 1
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, default=Path("../data"))
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    raise SystemExit(validate(a.data_dir, a.day, a.verbose))


if __name__ == "__main__":
    main()
