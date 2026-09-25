"""Cluster-robust standard errors for a sim's per-market P&L.

`sim --per-market` scores each market independently and reports a t-stat computed across
markets as if they were independent draws. They are not: 284 KXNFLSPREAD markets are strikes
on ~15 games, and every strike of a game reprices on the same touchdowns. The naive t is
therefore inflated by roughly sqrt(markets per cluster) when within-game correlation is high.

Three views, weakest assumption last:

  naive        t across markets, what sim.py prints
  clustered    CR1 cluster-robust SE on the market-level mean, clustered by game
  game-level   sum P&L per game, then a plain t across games (n = number of games)

Also reports the intraclass correlation, which is what decides how far apart those are.

    uv run python -m kalshi_data.research.cluster_se ../research/permkt_offset3_KXNFLSPREAD_2026-09-20.parquet
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import polars as pl


def game_of(ticker: str) -> str:
    """KXNFLSPREAD-26SEP24ATLGB-GB28 -> 26SEP24ATLGB (the event every strike shares)."""
    parts = ticker.split("-")
    return parts[1] if len(parts) > 2 else ticker


def icc(y: np.ndarray, g: np.ndarray) -> float:
    """One-way ANOVA intraclass correlation: between-cluster share of total variance."""
    groups = [y[g == k] for k in np.unique(g)]
    n = len(y)
    k = len(groups)
    if k < 2 or n <= k:
        return float("nan")
    grand = y.mean()
    ss_b = sum(len(x) * (x.mean() - grand) ** 2 for x in groups)
    ss_w = sum(((x - x.mean()) ** 2).sum() for x in groups)
    ms_b, ms_w = ss_b / (k - 1), ss_w / (n - k)
    sizes = np.array([len(x) for x in groups], dtype=float)
    n0 = (n - (sizes**2).sum() / n) / (k - 1)
    var_b = (ms_b - ms_w) / n0
    return float(var_b / (var_b + ms_w)) if (var_b + ms_w) > 0 else float("nan")


def stats(y: np.ndarray, g: np.ndarray) -> dict:
    n = len(y)
    mean = y.mean()
    sd = y.std(ddof=1)
    t_naive = mean / (sd / math.sqrt(n)) if sd > 0 else float("nan")

    # CR1 cluster-robust variance of the mean: (1/n^2) * sum_g (sum_i e_i)^2, with the
    # usual finite-cluster correction G/(G-1).
    keys = np.unique(g)
    gsum = np.array([(y[g == k] - mean).sum() for k in keys])
    G = len(keys)
    var_cl = gsum @ gsum / n**2 * (G / (G - 1)) if G > 1 else float("nan")
    t_cl = mean / math.sqrt(var_cl) if var_cl and var_cl > 0 else float("nan")

    # game-level: total P&L per game, plain t across games
    tot = np.array([y[g == k].sum() for k in keys])
    t_game = tot.mean() / (tot.std(ddof=1) / math.sqrt(G)) if G > 2 and tot.std(ddof=1) > 0 else float("nan")

    return {"markets": n, "games": G, "mean": mean, "total": y.sum(), "t_naive": t_naive,
            "t_clustered": t_cl, "game_total_mean": tot.mean(), "t_game": t_game,
            "games_positive": int((tot > 0).sum()), "icc": icc(y, g), "worst_game": tot.min()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("parquet", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    df = pl.read_parquet(a.parquet).with_columns(
        pl.col("ticker").map_elements(game_of, return_dtype=pl.String).alias("game"))

    lines = [f"# Cluster-robust standard errors, {a.parquet.name}\n",
             "Markets within a game share every information event, so the market-level t is inflated. "
             "`t_clustered` is CR1 clustered by game; `t_game` treats each game's total P&L as one observation.\n",
             "| config | markets | games | $/market | total $ | t naive | **t clustered** | **t game** | $/game | games + | ICC | worst game |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name in df["config"].unique(maintain_order=True):
        d = df.filter(pl.col("config") == name)
        s = stats(d["pnl"].to_numpy(), d["game"].to_numpy())
        lines.append(
            f"| {name} | {s['markets']} | {s['games']} | {s['mean']:+.2f} | {s['total']:+.1f} | {s['t_naive']:+.2f} | "
            f"**{s['t_clustered']:+.2f}** | **{s['t_game']:+.2f}** | {s['game_total_mean']:+.2f} | "
            f"{s['games_positive']}/{s['games']} | {s['icc']:.2f} | {s['worst_game']:+.1f} |")

    text = "\n".join(lines)
    print(text)
    if a.out:
        a.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
