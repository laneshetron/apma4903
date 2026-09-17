"""Does the paper (or live) quoter agree with the offline simulator on the same markets?

Per market the quoter traded: our tape's cash / position / fill count (position
marked at the collector mid when the market was left, or the recorded mark_pnl)
against the sim's per-market result for one configuration. Agreement here is
what qualifies the paper executor as a stand-in for live.

    uv run python -m kalshi_data.research.sim 2026-09-17 --data-dir ../data_aws --eval --tables-from 2026-09-15 --per-market ../research/permkt_eval_2026-09-17.parquet
    uv run python -m kalshi_data.research.paper_vs_sim 2026-09-17 --permkt ../research/permkt_eval_2026-09-17.parquet --config "live 20/20 $100 flatten (baseline)" [--from 04:13]
"""

from __future__ import annotations

import argparse
import collections
from datetime import date, datetime, timezone
from pathlib import Path

import polars as pl

from ..raw import iter_records
from .fill_markouts import mid_at, mid_series


def quoter_markets(tape: Path, day: date, start_ns: int) -> dict[str, dict]:
    out: dict[str, dict] = collections.defaultdict(lambda: {"cash": 0.0, "pos": 0.0, "fills": 0, "sweep": 0, "contracts": 0.0, "done_rx": None, "mark_pnl": None})
    for rec in iter_records(tape, day):
        raw = rec.raw
        if raw.get("type") != "_local" or raw.get("event") != "quoter" or rec.rx_ns < start_ns:
            continue
        m = out[raw["ticker"]] if "ticker" in raw else None
        if raw.get("kind") == "fill" and not raw.get("taker"):
            q, px = float(raw["qty"]), float(raw["price"])
            if raw["side"] == "yes":
                m["cash"] -= q * px
                m["pos"] += q
            else:
                m["cash"] += q * (1 - px)
                m["pos"] -= q
            m["fills"] += 1
            m["contracts"] += q
            m["sweep"] += bool(raw.get("sweep"))
        elif raw.get("kind") == "fill":  # taker (flatten)
            q, px = float(raw["qty"]), float(raw["price"])
            if raw["side"] == "yes":
                m["cash"] -= q * px
                m["pos"] += q
            else:
                m["cash"] += q * (1 - px)
                m["pos"] -= q
            m["cash"] -= float(raw.get("fee", 0) or 0)
        elif raw.get("kind") == "market_done":
            m["done_rx"] = rec.rx_ns
            if "mark_pnl" in raw:
                m["mark_pnl"] = float(raw["mark_pnl"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, default=Path("../data_aws"))
    ap.add_argument("--mode", default="paper", choices=("paper", "live"))
    ap.add_argument("--permkt", type=Path, required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--from", dest="from_", default="00:00")
    a = ap.parse_args()
    start_ns = int(datetime.combine(a.day, datetime.strptime(a.from_, "%H:%M").time(), tzinfo=timezone.utc).timestamp() * 1e9)
    ours = quoter_markets(a.data_dir / "quoter" / a.mode, a.day, start_ns)
    ours = {t: m for t, m in ours.items() if m["done_rx"] is not None}
    series = mid_series(a.data_dir, a.day, set(ours))
    sim = pl.read_parquet(a.permkt).filter(pl.col("config") == a.config)
    simd = {r["ticker"]: r for r in sim.to_dicts()}
    print(f"# {a.mode} vs sim [{a.config}], {a.day} from {a.from_} UTC\n")
    print("| market | ours $ | sim $ | ours fills | sim fills | ours contracts | sim contracts | sweep fills % ours / sim |\n|---|---|---|---|---|---|---|---|")
    tot = collections.Counter()
    pairs = []
    for tk in sorted(ours):
        m = ours[tk]
        if m["mark_pnl"] is not None:
            pnl = m["mark_pnl"]
        else:
            mid = mid_at(series[tk], m["done_rx"]) if tk in series and len(series[tk][0]) else None
            if mid is None:
                continue
            pnl = m["cash"] + m["pos"] * mid / 100
        s = simd.get(tk)
        if s is None or m["fills"] == 0:
            continue  # not simulated, or the quoter was not running (or halted) for this market
        pairs.append((pnl, s["pnl"]))
        sw = f"{m['sweep'] / m['fills'] * 100:.0f}%"
        ssw = f"{s['sweep_fills'] / s['fills'] * 100:.0f}%" if s.get("sweep_fills") is not None and s["fills"] else "—"
        print(f"| {tk[-7:]} | {pnl:+.2f} | {s['pnl']:+.2f} | {m['fills']} | {s['fills']} | {m['contracts']:,.0f} | {s['traded']:,.0f} | {sw} / {ssw} |")
        tot.update(ours_pnl=pnl, sim_pnl=s["pnl"], ours_fills=m["fills"], sim_fills=s["fills"], ours_c=m["contracts"], sim_c=s["traded"])
    if pairs:
        df = pl.DataFrame(pairs, schema=["ours", "sim"], orient="row")
        corr = df.select(pl.corr("ours", "sim")).item() if len(pairs) > 2 else float("nan")
        print(f"\n{len(pairs)} markets: {a.mode} {tot['ours_pnl']:+.2f} vs sim {tot['sim_pnl']:+.2f}; fills {tot['ours_fills']} vs {tot['sim_fills']}; "
              f"contracts {tot['ours_c']:,.0f} vs {tot['sim_c']:,.0f}; per-market corr {corr:.2f}")


if __name__ == "__main__":
    main()
