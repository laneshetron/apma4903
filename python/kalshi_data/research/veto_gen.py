"""Presence-veto intervals for the sim (`Params.veto_file`): hindsight oracles and the learned vacate model.

  --oracle DAY      for every trade that sweeps through a touch level on side s (price worse than the
                    touch, or the level emptied) at tape time T: veto s over [T - warning, T + 1 ms].
                    Writes veto_oracle{50,250,1000}_DAY.parquet and veto_oracleadv250_DAY.parquet
                    (adverse sweeps only: maker markout at 30 s < 0).
  --model TRAIN TEST  fit the vacate classifier (250 ms horizon) on vacate_TRAIN.parquet, predict on
                    vacate_TEST.parquet; where p > thr, veto the RESTING side whose touch is predicted to
                    vacate over [rx, rx + 250 ms]. Writes veto_model{30,50,70}_TEST.parquet.

    uv run python -m kalshi_data.research.veto_gen --oracle 2026-09-17 --data-dir ../data_aws
    uv run python -m kalshi_data.research.veto_gen --model 2026-09-16 2026-09-17
"""

from __future__ import annotations

import argparse
import bisect
import sys
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl

from ..book import parse_price, parse_qty
from ..raw import iter_records
from .markouts import FastBook

ONE = 10_000
QTY = 100
R = Path("../research")


def oracle(data_dir: Path, day: date, series: str) -> None:
    pre = "" if series == "KXBTC15M" else f"{series}_"
    books: dict[str, FastBook] = {}
    mids: dict[str, tuple[list, list]] = {}
    sweeps: list[tuple[str, str, int, int, float]] = []   # ticker, side, rx, sign, price_c
    n = 0
    for rec in iter_records(data_dir, day):
        raw = rec.raw
        t = raw.get("type")
        if t not in ("orderbook_snapshot", "orderbook_delta", "trade"):
            continue
        tk = raw["msg"]["market_ticker"]
        if not tk.startswith(series + "-"):
            continue
        n += 1
        if n % 5_000_000 == 0:
            print(f"  {n/1e6:.0f}M msgs, {len(sweeps):,} sweeps", file=sys.stderr)
        b = books.get(tk)
        if b is None:
            b = books[tk] = FastBook()
            mids[tk] = ([], [])
        rx = rec.rx_ns
        if t == "orderbook_snapshot":
            b.snapshot(raw["msg"])
        elif t == "orderbook_delta":
            msg = raw["msg"]
            try:
                b.delta(msg["side"], parse_price(msg["price_dollars"]), parse_qty(msg["delta_fp"]))
            except ValueError:
                continue
        else:
            msg = raw["msg"]
            yes_price = parse_price(msg["yes_price_dollars"])
            hit = "no" if msg["taker_side"] == "yes" else "yes"
            lvl = yes_price if hit == "yes" else ONE - yes_price
            best = b.best(hit)
            if best < 0:
                continue
            if lvl < best or b.side(hit).get(lvl, 0) == 0:
                sweeps.append((tk, hit, rx, 1 if hit == "yes" else -1, yes_price / 100))
        if b.best_yes >= 0 and b.best_no >= 0:
            m = (b.best_yes + ONE - b.best_no) / 2 / 100
            mr, mv = mids[tk]
            if not mv or mv[-1] != m:
                mr.append(rx)
                mv.append(m)
    print(f"{len(sweeps):,} sweep-through trades", file=sys.stderr)
    adverse = []
    for tk, s, rx, sign, pc in sweeps:
        mr, mv = mids[tk]
        i = bisect.bisect_right(mr, rx + 30_000_000_000) - 1
        adverse.append(i >= 0 and sign * (mv[i] - pc) < 0)
    for w in (50, 250, 1000):
        df = pl.DataFrame({"ticker": [x[0] for x in sweeps], "side": [x[1] for x in sweeps],
                           "start_rx": [x[2] - w * 1_000_000 for x in sweeps], "end_rx": [x[2] + 1_000_000 for x in sweeps]})
        df.write_parquet(R / f"{pre}veto_oracle{w}_{day}.parquet")
    sel = [x for x, a in zip(sweeps, adverse) if a]
    print(f"{len(sel):,} adverse ({len(sel)/max(1,len(sweeps))*100:.0f}%)", file=sys.stderr)
    pl.DataFrame({"ticker": [x[0] for x in sel], "side": [x[1] for x in sel],
                  "start_rx": [x[2] - 250_000_000 for x in sel], "end_rx": [x[2] + 1_000_000 for x in sel]}).write_parquet(R / f"{pre}veto_oracleadv250_{day}.parquet")


def model(train_day: date, test_day: date) -> None:
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score
    from .vacate import HORIZONS_MS
    tr = pl.read_parquet(R / f"vacate_{train_day}.parquet")
    te = pl.read_parquet(R / f"vacate_{test_day}.parquet")
    skip = {"ticker", "side", "rx", "our_best", "opp_best", "lead_ms", "formed_2s"} | {f"vacate_{h}" for h in HORIZONS_MS}
    feats = [c for c in tr.columns if c not in skip]
    clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=200, l2_regularization=1.0)
    clf.fit(tr.select(feats).to_numpy().astype(np.float32), tr["vacate_250"].to_numpy())
    p = clf.predict_proba(te.select(feats).to_numpy().astype(np.float32))[:, 1]
    print(f"test AUC {roc_auc_score(te['vacate_250'].to_numpy(), p):.3f}", file=sys.stderr)
    # the row's side s predicts the OPPOSITE touch vacating: that is the resting side at risk
    resting = np.where(te["side"].to_numpy() == "yes", "no", "yes")
    for thr in (0.3, 0.5, 0.7):
        sel = p > thr
        print(f"p > {thr}: {sel.mean()*100:.1f}% of samples vetoed", file=sys.stderr)
        pl.DataFrame({"ticker": te["ticker"].to_numpy()[sel], "side": resting[sel],
                      "start_rx": te["rx"].to_numpy()[sel], "end_rx": te["rx"].to_numpy()[sel] + 250_000_000}).write_parquet(R / f"veto_model{int(thr*100)}_{test_day}.parquet")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--oracle", type=date.fromisoformat)
    ap.add_argument("--model", nargs=2, type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, default=Path("../data_aws"))
    ap.add_argument("--series", default="KXBTC15M")
    a = ap.parse_args()
    if a.oracle:
        oracle(a.data_dir, a.oracle, a.series)
    if a.model:
        model(*a.model)


if __name__ == "__main__":
    main()
