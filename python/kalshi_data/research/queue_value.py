"""Expected edge of a resting order as a function of queue position and toxicity state.

    uv run python -m kalshi_data.research.queue_value 2026-09-14

An order with q contracts ahead of it is filled only by sweeps of size S > q,
receiving min(size, S - q). So E[markout | fill from q, x] is the fill-weighted
markout of sweeps with S > q in state x. Edge = half-spread + markout. The
optimal hold/cancel rule is: hold while edge(q, x) > value of rejoining at
the back (~0). Uses research/alpha_<day>.parquet.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import polars as pl

Q_AHEAD = [0, 50, 100, 200, 500, 1000, 2000, 5000]
ORDER = 100  # contracts, our order size


def edge_table(df: pl.DataFrame, state_col: str | None, edges, labels, horizon: str = "mo30") -> list[str]:
    L = []
    hdr = "| state \\ q ahead | " + " | ".join(str(q) for q in Q_AHEAD) + " |"
    L.append(hdr)
    L.append("|" + "---|" * (len(Q_AHEAD) + 1))
    buckets = [(None, None, "all")] if state_col is None else list(zip(edges[:-1], edges[1:], labels))
    for lo, hi, name in buckets:
        d = df if state_col is None else df.filter((pl.col(state_col) >= lo) & (pl.col(state_col) < hi))
        d = d.filter(pl.col(horizon).is_not_null() & pl.col("mo0").is_not_null())
        cells = []
        for q in Q_AHEAD:
            f = d.filter(pl.col("qty") > q).with_columns(pl.min_horizontal(pl.lit(ORDER), pl.col("qty") - q).alias("fill"))
            if f.height < 50:
                cells.append("  n/a ")
                continue
            w = f["fill"]
            edge = float(((f["mo0"] + f[horizon]) * w).sum() / w.sum())   # half-spread captured + markout
            cells.append(f"{edge:+.2f}")
        L.append(f"| {name} | " + " | ".join(cells) + " |")
    return L


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--research-dir", type=Path, default=Path("../research"))
    a = ap.parse_args()
    df = pl.read_parquet(a.research_dir / f"alpha_{a.day}.parquet")
    df = df.filter(pl.col("klass") != "unknown")
    L = [f"# Expected edge of a resting {ORDER}-lot by queue position, {a.day}", "",
         "Cells: fill-weighted (half-spread captured + 30s markout), cents/contract, for an order with q contracts ahead "
         "(filled only by sweeps larger than q). Positive = hold, negative = the fills you would get lose money.", ""]
    L.append("## All states"); L.append("")
    L += edge_table(df, None, None, None); L.append("")
    L.append("## By 1s markout horizon (all states) — immediate vs 30s")
    L.append("")
    L += edge_table(df, None, None, None, horizon="mo1"); L.append("")
    L.append("## By Kalshi touch imbalance (other − hit)/(other + hit)"); L.append("")
    L += edge_table(df, "touch_imb", [-1e9, -0.33, 0.33, 1e9], ["hit side deeper", "balanced", "other side deeper"]); L.append("")
    L.append("## By Coinbase microprice − mid, signed into the taker's direction"); L.append("")
    L += edge_table(df, "cb_micro", [-1e9, -0.5, 0.5, 1e9], ["against >$0.5", "flat", "agrees >$0.5"]); L.append("")
    L.append("## By minutes to expiry"); L.append("")
    L += edge_table(df, "ttx_min", [0, 2, 5, 10, 16], ["0-2", "2-5", "5-10", "10-15"]); L.append("")
    L.append("## By delta × σ(10s)"); L.append("")
    L += edge_table(df, "delta_x_sigma10", [0, 0.01, 0.05, 1], ["<1c", "1-5c", ">5c"]); L.append("")
    text = "\n".join(L)
    (a.research_dir / f"queue_value_{a.day}.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
