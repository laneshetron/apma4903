"""Survivability of the Hyperliquid deep-resting strategy under leverage.

Point estimates cannot answer "does this blow up", because ruin is path dependent: the edge
comes from being run over by a cascade and waiting for the snap-back, and the question is
whether the account survives the waiting. So this replays the real tape rather than an
invented distribution.

Stage 1 (`--extract`) walks the tape once and caches, per coin, a 1 s mid grid and every deep
(>= --min-off bp) sweep fill at 1% participation. Stage 2 resamples whole UTC days with
replacement to build synthetic years -- a *block* bootstrap, because deep fills arrive in
clusters and an i.i.d. resample of individual fills would destroy exactly the autocorrelation
that causes ruin.

Accounting, marked every second across all coins jointly:

    at a fill    equity += sign * (mid - px) / px * notional      (edge captured at the fill)
                 inventory += sign * notional
    each second  equity += inventory * (mid_t / mid_{t-1} - 1)
    after 300 s  the position is closed
    ruin         equity <= maint * sum |inventory|

Because position sizing is fixed (set by leverage, not by current equity), each real day has a
*deterministic* P&L path, so a day collapses to two numbers:

    total_pnl_d   the day's P&L
    threshold_d   max_t (maint * gross_t - cumpnl_t)

and the day kills an account iff its starting equity <= threshold_d. Both scale linearly with
participation, so they are computed once at 1% and rescaled. That makes the Monte Carlo exact
(given fixed sizing) and fast.

    uv run python -m kalshi_data.research.hl_mc --extract --data-dir ../data_hl
    uv run python -m kalshi_data.research.hl_mc --paths 20000
"""

from __future__ import annotations

import argparse
import bisect
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

from ..raw import iter_records

HOLD_S = 300
DAY_S = 86_400
CACHE = Path("../research/hl_mc_cache.npz")


# --------------------------------------------------------------------------- extract

def extract(data_dir: Path, start: date, end: date, min_off: float, share: float, out: Path) -> None:
    mid_rx: dict[str, list[int]] = defaultdict(list)
    mid_v: dict[str, list[float]] = defaultdict(list)
    cur: dict[str, list] = {}
    fills: list[tuple[int, str, float, float, float, float]] = []
    grid: dict[str, list[tuple[int, float]]] = defaultdict(list)
    last_sec: dict[str, int] = {}

    def mid_at(coin: str, at: int) -> float | None:
        r = mid_rx[coin]
        i = bisect.bisect_right(r, at) - 1
        return mid_v[coin][i] if i >= 0 else None

    def flush(coin: str) -> None:
        got = cur.pop(coin, None)
        if not got:
            return
        _, side, rx, prints = got
        ref = mid_at(coin, rx)
        if ref is None:
            return
        walk = [p for p, _ in prints]
        ok = (all(b >= a for a, b in zip(walk, walk[1:])) if side == "B"
              else all(b <= a for a, b in zip(walk, walk[1:])))
        if len(walk) > 1 and not ok:
            return
        px0, sign = walk[0], (-1.0 if side == "B" else 1.0)
        for px, sz in prints:
            off_bp = ((px - px0) if side == "B" else (px0 - px)) / ref * 1e4
            if off_bp < min_off:
                continue
            fills.append((rx, coin, sign, px * sz * share, px, ref))

    for rec in iter_records(data_dir, start, end):
        r = rec.raw
        ch = r.get("channel")
        rx = rec.rx_ns
        if ch == "bbo":
            d = r["data"]
            b, o = d["bbo"]
            if not b or not o:
                continue
            c = d["coin"]
            m = (float(b["px"]) + float(o["px"])) / 2
            if not mid_v[c] or mid_v[c][-1] != m:
                mid_rx[c].append(rx)
                mid_v[c].append(m)
                if len(mid_rx[c]) > 8192:
                    del mid_rx[c][:4096]
                    del mid_v[c][:4096]
            s = rx // 1_000_000_000
            if last_sec.get(c) != s:
                last_sec[c] = s
                grid[c].append((s, m))
            continue
        if ch != "trades":
            continue
        for t in r["data"]:
            c = t["coin"]
            g = cur.get(c)
            if g is not None and (g[0] != t["time"] or g[1] != t["side"]):
                flush(c)
                g = None
            if g is None:
                cur[c] = [t["time"], t["side"], rx, []]
            cur[c][3].append((float(t["px"]), float(t["sz"])))
    for c in list(cur):
        flush(c)

    coins = sorted(grid)
    payload: dict[str, np.ndarray] = {"coins": np.array(coins)}
    for c in coins:
        g = np.array(grid[c], dtype=np.float64)
        payload[f"grid_s_{c}"], payload[f"grid_m_{c}"] = g[:, 0], g[:, 1]
    payload["fill_s"] = np.array([x[0] // 1_000_000_000 for x in fills], dtype=np.float64)
    payload["fill_coin"] = np.array([coins.index(x[1]) for x in fills], dtype=np.int32)
    payload["fill_sign"] = np.array([x[2] for x in fills], dtype=np.float64)
    payload["fill_notional"] = np.array([x[3] for x in fills], dtype=np.float64)
    payload["fill_px"] = np.array([x[4] for x in fills], dtype=np.float64)
    payload["fill_mid"] = np.array([x[5] for x in fills], dtype=np.float64)
    np.savez_compressed(out, **payload)
    print(f"cached {len(fills):,} deep fills, {sum(len(grid[c]) for c in coins):,} mid samples -> {out}")


# ------------------------------------------------------------------- per-day reduction

def day_stats(z, maint: float, fee_bp: float = 1.5) -> tuple[np.ndarray, np.ndarray]:
    """Per real day at 1% participation: (total_pnl, threshold).

    threshold is the starting equity at or below which the day is fatal.
    """
    coins = [str(c) for c in z["coins"]]
    fs, fc = z["fill_s"], z["fill_coin"]
    day_ids = sorted({int(s) // DAY_S for s in fs})
    totals, thresholds = [], []
    for d in day_ids:
        lo = d * DAY_S
        cum = np.zeros(DAY_S)      # cumulative P&L within the day
        gross = np.zeros(DAY_S)    # gross |inventory| within the day
        any_coin = False
        for ci, c in enumerate(coins):
            gs, gm = z[f"grid_s_{c}"], z[f"grid_m_{c}"]
            sel = (gs >= lo) & (gs < lo + DAY_S)
            if sel.sum() < 100:
                continue
            any_coin = True
            idx = (gs[sel] - lo).astype(int)
            mid = np.full(DAY_S, np.nan)
            mid[idx] = gm[sel]
            # forward-fill: a price holds until it next prints. Linear interpolation
            # would invent intermediate moves that never happened.
            first = int(np.flatnonzero(~np.isnan(mid))[0])
            mid[:first] = mid[first]
            fwd = np.maximum.accumulate(np.where(np.isnan(mid), 0, np.arange(DAY_S)))
            mid = mid[fwd]

            fsel = (fc == ci) & (fs >= lo) & (fs < lo + DAY_S)
            fsec = (fs[fsel] - lo).astype(int)
            sign, notl = z["fill_sign"][fsel], z["fill_notional"][fsel]
            px = z["fill_px"][fsel]

            delta = np.zeros(DAY_S + HOLD_S + 1)
            np.add.at(delta, fsec, sign * notl)
            np.add.at(delta, fsec + HOLD_S, -sign * notl)
            inv = np.cumsum(delta)[:DAY_S]

            # Book the edge against the same mark the position is then carried at
            # (the grid), not against the full-resolution bbo mid: otherwise the
            # difference between the two is silently dropped at exactly the sweep.
            edge = np.zeros(DAY_S)
            np.add.at(edge, fsec, sign * (mid[fsec] - px) / px * notl)
            # maker fee is charged on filled notional (HL perps tier 0 = 1.5 bp)
            np.add.at(edge, fsec, -fee_bp * 1e-4 * notl)

            ret = np.zeros(DAY_S)
            ret[1:] = mid[1:] / mid[:-1] - 1.0
            cum += np.cumsum(edge + np.concatenate(([0.0], inv[:-1] * ret[1:])))
            gross += np.abs(inv)
        if not any_coin:
            continue
        totals.append(cum[-1])
        thresholds.append(float(np.max(maint * gross - cum)))
    return np.array(totals), np.array(thresholds)


# --------------------------------------------------------------------------- monte carlo

def simulate(totals: np.ndarray, thresholds: np.ndarray, scale: float, capital: float,
             paths: int, days: int, rng: np.random.Generator) -> dict:
    t, thr = totals * scale, thresholds * scale
    eq = np.full(paths, capital)
    alive = np.ones(paths, dtype=bool)
    peak = np.full(paths, capital)
    maxdd = np.zeros(paths)
    for _ in range(days):
        pick = rng.integers(0, len(t), size=paths)
        dead_now = alive & (eq <= thr[pick])
        alive &= ~dead_now
        eq = np.where(alive, eq + t[pick], 0.0)
        peak = np.where(alive, np.maximum(peak, eq), peak)
        with np.errstate(invalid="ignore", divide="ignore"):
            dd = np.where(alive & (peak > 0), 1.0 - eq / peak, maxdd)
        maxdd = np.maximum(maxdd, np.nan_to_num(dd))
    final_all = np.where(alive, eq, 0.0)
    return {"ruin": 1.0 - alive.mean(), "final": eq[alive], "maxdd": maxdd[alive],
            "n_alive": int(alive.sum()),
            "p_loss": float((final_all < capital).mean()),
            "p_half": float((final_all < 0.5 * capital).mean()),
            "dd99": float(np.percentile(maxdd[alive], 99)) if alive.any() else 1.0}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extract", action="store_true")
    ap.add_argument("--data-dir", type=Path, default=Path("../data_hl"))
    ap.add_argument("--start", type=date.fromisoformat, default=date(2026, 9, 16))
    ap.add_argument("--end", type=date.fromisoformat, default=date(2026, 9, 25))
    ap.add_argument("--min-off", type=float, default=3.0)
    ap.add_argument("--share", type=float, default=0.01)
    ap.add_argument("--cache", type=Path, default=CACHE)
    ap.add_argument("--capital", type=float, default=10_000)
    ap.add_argument("--peak-inv-1pc", type=float, default=1_748_569)
    ap.add_argument("--maint", type=float, default=0.0125)
    ap.add_argument("--maker-fee-bp", type=float, default=1.5,
                    help="maker fee charged on filled notional; HL perps tier 0 is 1.5 bp, tier 4+ is 0")
    ap.add_argument("--paths", type=int, default=20_000)
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    if a.extract:
        extract(a.data_dir, a.start, a.end, a.min_off, a.share, a.cache)
        return

    z = np.load(a.cache, allow_pickle=False)
    totals, thresholds = day_stats(z, a.maint, a.maker_fee_bp)
    rng = np.random.default_rng(a.seed)
    lines = [f"# Monte Carlo survivability, {a.paths:,} paths x {a.days} days, "
             f"block-bootstrapped from {len(totals)} real days\n",
             f"Capital ${a.capital:,.0f}; leverage sets participation so peak inventory = capital x leverage. "
             f"Maintenance margin {a.maint*100:.2f}% of gross notional; maker fee {a.maker_fee_bp:.2f} bp on filled "
             f"notional. No exit slippage or funding charged.\n",
             f"Source days: P&L per day at 1% participation ranges "
             f"${totals.min():,.0f} to ${totals.max():,.0f} (median ${np.median(totals):,.0f}).\n",
             "`ruin` is literal liquidation (equity <= maintenance margin). On a perp that is a very low "
             "bar -- at 1.25% maintenance you are only dead after losing ~99% -- so `P(-50%)` is the more "
             "useful column.\n",
             "| leverage | participation | peak inv | **ruin %** | **P(-50%)** | P(lose) | median /yr | p5 | p95 | median maxDD | p99 maxDD |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for L in (1, 2, 3, 5, 8, 10):
        scale = a.capital * L / a.peak_inv_1pc
        r = simulate(totals, thresholds, scale, a.capital, a.paths, a.days, rng)
        if r["n_alive"]:
            ret = (r["final"] / a.capital - 1) * 100
            med, p5, p95 = np.median(ret), np.percentile(ret, 5), np.percentile(ret, 95)
            dd = np.median(r["maxdd"]) * 100
            cells = f"{med:+.0f}% | {p5:+.0f}% | {p95:+.0f}% | {dd:.0f}% | {r['dd99']*100:.0f}%"
        else:
            cells = "— | — | — | — | —"
        lines.append(f"| {L}x | {scale:.4f}% | ${a.capital*L:,.0f} | **{r['ruin']*100:.1f}%** | "
                     f"**{r['p_half']*100:.1f}%** | {r['p_loss']*100:.1f}% | {cells} |")
    text = "\n".join(lines)
    print(text)
    if a.out:
        a.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
