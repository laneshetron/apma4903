"""Do perpetual-swap feeds anticipate Kalshi repricing better than Coinbase spot?

Two tests on the window where both are recorded:

1. Lead/lag: cross-correlation of 100ms mid returns, each venue vs Coinbase
   spot, at lags -2s..+2s. Positive best lag = the venue moves first.
2. Sweep-conditioned: for each KXBTC15M sweep (from research/alpha_<day>.parquet)
   the signed move of every venue's mid over the prior 300ms / 1s, in bp and
   signed into the taker's direction. A venue whose prior move "agrees" with
   the taker more often than Coinbase's carries information Coinbase does not
   yet show. We also split the sweeps Coinbase calls quiet (|move 1s| < $2) by
   whether a perp already moved, and look at the maker markouts of each half.

Times are our receive times (rx_ns): what a quoter in this location would act
on. The exchange-timestamp version is reported alongside for the lead/lag test.

    uv run python -m kalshi_data.research.perp_lead 2026-09-15 --from 17:25
"""

from __future__ import annotations

import argparse
import bisect
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import polars as pl

from ..spot import SpotQuote, iter_spot

VENUES = ["coinbase", "coinbase_perp", "kraken_futures", "okx", "bybit", "hyperliquid"]
GRID_MS = 100
LAGS = range(-20, 21)


def load_mids(data_dir: Path, day: date, start_ns: int, end_ns: int) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """venue -> (rx_ns, ts_ms, mid) for BTC quotes in [start, end]."""
    out = {}
    for v in VENUES:
        rx, ts, mid = [], [], []
        for q in iter_spot(data_dir, v, day):
            if not isinstance(q, SpotQuote) or q.asset != "BTC" or q.rx_ns < start_ns:
                continue
            if q.rx_ns > end_ns:
                break
            rx.append(q.rx_ns)
            ts.append(q.ts_ms if q.ts_ms is not None else q.rx_ns // 1_000_000)
            mid.append((q.bid + q.ask) / 2)
        out[v] = (np.array(rx, dtype=np.int64), np.array(ts, dtype=np.int64), np.array(mid))
        print(f"{v}: {len(rx):,} BTC quotes, rx-ts lag p50 {np.median(np.array(rx) / 1e6 - np.array(ts)):.0f} ms")
    return out


def grid_returns(t_ms: np.ndarray, mid: np.ndarray, t0: int, t1: int) -> np.ndarray:
    grid = np.arange(t0, t1, GRID_MS)
    idx = np.searchsorted(t_ms, grid, side="right") - 1
    m = np.where(idx >= 0, mid[np.clip(idx, 0, len(mid) - 1)], np.nan)
    r = np.diff(np.log(m))
    return np.nan_to_num(r)


def lead_lag(mids, key: int, t0: int, t1: int) -> list[str]:
    """key: 0 -> rx_ns (converted to ms), 1 -> exchange ts_ms."""
    ref = mids["coinbase"]
    tref = ref[0] // 1_000_000 if key == 0 else ref[1]
    r_ref = grid_returns(tref, ref[2], t0, t1)
    lines = ["| venue | best lag (ms) | corr at best | corr lead 100ms | corr lag 100ms | corr 0 | lead-lag asymmetry |", "|---|---|---|---|---|---|---|"]
    for v in VENUES:
        if v == "coinbase":
            continue
        t = mids[v][0] // 1_000_000 if key == 0 else mids[v][1]
        r = grid_returns(t, mids[v][2], t0, t1)
        cs = {}
        for lag in LAGS:
            # lag > 0: venue return at t vs coinbase return at t+lag (venue leads)
            if lag >= 0:
                a, b = r[: len(r) - lag] if lag else r, r_ref[lag:]
            else:
                a, b = r[-lag:], r_ref[: len(r_ref) + lag]
            cs[lag] = float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else 0.0
        best = max(cs, key=cs.get)
        asym = sum(cs[l] for l in LAGS if l > 0) - sum(cs[l] for l in LAGS if l < 0)
        lines.append(f"| {v} | {best * GRID_MS:+d} | {cs[best]:.3f} | {cs[1]:.3f} | {cs[-1]:.3f} | {cs[0]:.3f} | {asym:+.3f} |")
    return lines


def prior_move(rx: np.ndarray, mid: np.ndarray, t_ns: int, back_ns: int) -> float | None:
    i = bisect.bisect_right(rx, t_ns) - 1
    j = bisect.bisect_right(rx, t_ns - back_ns) - 1
    if i < 0 or j < 0:
        return None
    return (mid[i] - mid[j]) / mid[j] * 1e4


def sweep_test(mids, sweeps: pl.DataFrame) -> list[str]:
    sign = np.where(sweeps["taker_side"].to_numpy() == "yes", 1.0, -1.0)
    rx = sweeps["rx_ns"].to_numpy()
    qty = sweeps["qty"].to_numpy()
    full = sweeps["klass"].is_in(["full", "multi"]).to_numpy()
    mo1 = sweeps["mo1"].to_numpy()
    mo10 = sweeps["mo10"].to_numpy()
    feats = {}
    for v in VENUES:
        vrx, _, vmid = mids[v]
        for back_ms in (300, 1000):
            arr = np.array([prior_move(vrx, vmid, t, back_ms * 1_000_000) for t in rx], dtype=float)
            feats[(v, back_ms)] = sign * arr
    cb_quiet = np.abs(feats[("coinbase", 1000)]) < 2 / 76000 * 1e4  # $2 on ~$76k = 0.26 bp

    def wmean(x, m):
        w = qty[m]
        return float(np.nansum(x[m] * w) / w.sum()) if w.sum() else float("nan")

    L = ["Signed prior move of each venue's mid before a sweep (bp, + = in the taker's direction), volume-weighted; "
         "'agrees' = share of volume where the venue moved >= 0.5bp in the taker's direction.", "",
         "| venue | window | all: mean bp | agrees % | full+multi: mean bp | agrees % | partial: mean bp | agrees % |", "|---|---|---|---|---|---|---|---|"]
    for v in VENUES:
        for back_ms in (300, 1000):
            x = feats[(v, back_ms)]
            ok = ~np.isnan(x)
            cells = []
            for m in (ok, ok & full, ok & ~full):
                cells += [f"{wmean(x, m):+.2f}", f"{wmean((x > 0.5).astype(float), m) * 100:.0f}"]
            L.append(f"| {v} | {back_ms}ms | " + " | ".join(cells) + " |")

    L += ["", "Sweeps Coinbase calls quiet (|1s move| < $2), split by whether a perp had already moved >= 1bp in the taker's direction "
          "over the prior 1s. Maker markouts in cents/contract (full+multi only).", "",
          "| perp venue | quiet & perp moved: vol share | mo 1s | mo 10s | quiet & perp flat: vol share | mo 1s | mo 10s |", "|---|---|---|---|---|---|---|"]
    base = cb_quiet & full & ~np.isnan(feats[("coinbase", 1000)])
    tot = qty[full].sum()
    for v in VENUES[1:]:
        x = feats[(v, 1000)]
        moved = base & (x >= 1.0)
        flat = base & ~np.isnan(x) & (np.abs(x) < 1.0)
        L.append(f"| {v} | {qty[moved].sum() / tot * 100:.1f}% | {wmean(mo1, moved):+.2f} | {wmean(mo10, moved):+.2f} | "
                 f"{qty[flat].sum() / tot * 100:.1f}% | {wmean(mo1, flat):+.2f} | {wmean(mo10, flat):+.2f} |")
    L.append(f"| (all quiet full+multi) | {qty[base].sum() / tot * 100:.1f}% | {wmean(mo1, base):+.2f} | {wmean(mo10, base):+.2f} | | | |")
    return L


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--from", dest="from_", default="17:25", help="HH:MM UTC start of the overlap window")
    ap.add_argument("--to", default="23:59", help="HH:MM UTC end")
    ap.add_argument("--data-dir", type=Path, default=Path("../data"))
    ap.add_argument("--research-dir", type=Path, default=Path("../research"))
    a = ap.parse_args()
    t0 = datetime.combine(a.day, datetime.strptime(a.from_, "%H:%M").time(), tzinfo=timezone.utc)
    t1 = datetime.combine(a.day, datetime.strptime(a.to, "%H:%M").time(), tzinfo=timezone.utc)
    s_ns, e_ns = int(t0.timestamp() * 1e9), int(t1.timestamp() * 1e9)
    mids = load_mids(a.data_dir, a.day, s_ns, e_ns)
    t0_ms, t1_ms = int(t0.timestamp() * 1000), int(t1.timestamp() * 1000)
    L = [f"# Perp feeds vs Coinbase spot as a repricing signal, {a.day} {a.from_}-{a.to} UTC", "",
         "## Lead/lag of 100ms mid returns vs Coinbase spot (positive lag = venue leads)", "",
         "By receive time (what we can act on):", ""]
    L += lead_lag(mids, 0, t0_ms, t1_ms)
    L += ["", "By exchange timestamp (intrinsic):", ""]
    L += lead_lag(mids, 1, t0_ms, t1_ms)
    sweeps = pl.read_parquet(a.research_dir / f"alpha_{a.day}.parquet").filter((pl.col("rx_ns") >= s_ns) & (pl.col("rx_ns") <= e_ns))
    L += ["", f"## Sweep-conditioned ({sweeps.height:,} KXBTC15M sweeps, {sweeps['qty'].sum():,.0f} contracts)", ""]
    L += sweep_test(mids, sweeps)
    text = "\n".join(L)
    print(text)
    (a.research_dir / f"perp_lead_{a.day}.md").write_text(text)


if __name__ == "__main__":
    main()
