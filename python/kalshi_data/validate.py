"""Replay a day of raw logs and check reconstructed books against the REST
snapshots the collector recorded.

    uv run python -m kalshi_data.validate 2026-09-14 [--data-dir ../data] [-v]

A REST snapshot is taken some tens of ms before its response reaches us, so
on a busy market the replayed book at receive time legitimately differs; a
check passes if the book matched at some instant in the preceding 2s. A
market that fails that test is a real divergence.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from pathlib import Path

from .raw import iter_records
from .replay import Replayer, RestCheck, matches_within

WINDOW_NS = 2_000_000_000


def validate(data_dir: Path, day: date, verbose: bool = False) -> int:
    r = Replayer(history_ns=WINDOW_NS)
    checks: Counter[str] = Counter()
    mismatches: Counter[str] = Counter()   # differed at receive time
    failures: Counter[str] = Counter()     # no matching instant within the window
    skipped: Counter[str] = Counter()
    offsets: list[float] = []
    updates = 0
    # forward checks: ticker -> list of [deadline_ns, want, have, diff, best, best_off, rx_ns]
    forward: dict[str, list] = {}

    def settle(tk: str, fc: list, force: bool = False) -> None:
        for f in list(fc):
            if force or f[0] <= now:
                fc.remove(f)
                if f[4] == 0:
                    offsets.append(f[5])
                else:
                    failures[tk] += 1
                    if verbose:
                        print(f"{f[6]} {tk}: best {f[4]} differing levels within -{WINDOW_NS/1e9:g}s..+{WINDOW_NS/1e9:g}s")

    now = 0
    for rec in iter_records(data_dir, day):
        now = rec.rx_ns
        out = r.feed(rec)
        if out is None:
            continue
        if not isinstance(out, RestCheck):
            updates += 1
            fc = forward.get(out.ticker)
            if fc:
                if out.kind == "delta":
                    for f in fc:
                        k = (out.side, out.price)
                        w = f[1].get(k, 0)
                        was = f[2].get(k, 0) != w
                        f[2][k] = out.qty
                        f[3] += (out.qty != w) - was
                        if f[3] < f[4]:
                            f[4], f[5] = f[3], (out.rx_ns - f[6]) / 1e6
                settle(out.ticker, fc)
            continue
        checks[out.ticker] += 1
        if out.live is None:
            skipped[out.ticker] += 1
            continue
        diff = out.live.diff(out.rest)
        if not diff:
            continue
        mismatches[out.ticker] += 1
        best, off = matches_within(r, out.ticker, out.rest, out.rx_ns, WINDOW_NS)
        if best == 0:
            offsets.append(off)
            continue
        # no earlier match: watch the next WINDOW for the stream catching up to REST
        live = r.books[out.ticker]
        have = {("yes", p): q for p, q in live.yes.items()} | {("no", p): q for p, q in live.no.items()}
        want = {("yes", p): q for p, q in out.rest.yes.items()} | {("no", p): q for p, q in out.rest.no.items()}
        forward.setdefault(out.ticker, []).append([out.rx_ns + WINDOW_NS, want, have, len(diff), best, off, out.rx_ns])

    for tk, fc in forward.items():
        settle(tk, fc, force=True)

    print(f"book updates applied: {updates}")
    print(f"seq gaps: {r.gaps}   negative-qty divergences: {r.negatives}")
    print(f"rest checks: {sum(checks.values())} across {len(checks)} markets; skipped (stale): {sum(skipped.values())}")
    print(f"differed at receive time: {sum(mismatches.values())}, of which matched an instant within the window: {len(offsets)}"
          + (f" (median offset {sorted(offsets)[len(offsets)//2]:.0f}ms)" if offsets else ""))
    if failures:
        print(f"FAILED (no match within {WINDOW_NS/1e9:g}s): {sum(failures.values())} checks on "
              + ", ".join(f"{t} x{n}" for t, n in sorted(failures.items())))
        return 1
    print("all checks reconcile")
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
