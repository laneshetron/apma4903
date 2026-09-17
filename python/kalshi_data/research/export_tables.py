"""Export the fitted edge model for the Go quoter, with evaluation fixtures.

    uv run python -m kalshi_data.research.export_tables 2026-09-15 --out ../quoter_tables.json

Writes the additive-marginal edge tables (all / by touch imbalance / by Coinbase
microprice pressure / by minutes to expiry, each by queue-ahead bucket) and a
list of (inputs -> edge) fixtures computed by the Python model so the Go port
can be tested against it bit for bit.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import date
from pathlib import Path

from .sim import IMB_EDGES, MICRO_EDGES, Q_EDGES, TTX_EDGES, EdgeModel


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("day", type=date.fromisoformat, help="day whose sweep dataset (research/alpha_<day>.parquet) to fit on")
    ap.add_argument("--research-dir", type=Path, default=Path("../research"))
    ap.add_argument("--out", type=Path, default=Path("../quoter_tables.json"))
    ap.add_argument("--train-frac", type=float, default=1.0)
    a = ap.parse_args()
    m = EdgeModel(a.research_dir / f"alpha_{a.day}.parquet", train_frac=a.train_frac)
    rng = random.Random(7)
    fixtures = []
    for _ in range(200):
        side = rng.choice(["yes", "no"])
        imb = rng.uniform(-1, 1)
        micro = rng.choice([None, rng.uniform(-2, 2)])
        ttx = rng.uniform(0, 15)
        q = rng.choice([0, 10, 50, 99, 100, 150, 200, 499, 500, 999, 1000, 1999, 2000, 4999, 5000, 20000]) + rng.uniform(0, 0.5)
        fixtures.append({"side": side, "imb": imb, "micro": micro, "ttx_min": ttx, "q": q, "edge": m.edge(side, imb, micro, ttx, q)})
    out = {
        "fitted_on": a.day.isoformat(),
        "q_edges": Q_EDGES[:-1], "imb_edges": IMB_EDGES[1:-1], "micro_edges": MICRO_EDGES[1:-1], "ttx_edges": TTX_EDGES[1:-1],
        "all": m.all,
        "imb": [m.imb[i] for i in range(len(m.imb))],
        "micro": [m.micro[i] for i in range(len(m.micro))],
        "ttx": [m.ttx[i] for i in range(len(m.ttx))],
        "fixtures": fixtures,
    }
    a.out.write_text(json.dumps(out, indent=1))
    print(f"wrote {a.out} ({len(fixtures)} fixtures)")


if __name__ == "__main__":
    main()
