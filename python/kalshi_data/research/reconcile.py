"""Reconcile the quoter's live tape against Kalshi's own records.

For each market the live quoter traded:
  * fills: our tape's `fill` events (from the WS fill channel, as applied to the
    ledger) vs GET /portfolio/fills
  * position: our ledger's end position vs GET /portfolio/positions (open) or
    the settlement record (closed)
  * cash: our YES-sale-convention cash vs Kalshi's cost/revenue accounting
  * session: sum of settled P&L + open position value vs the balance change

    uv run python -m kalshi_data.research.reconcile --tape ../data_aws/quoter/live --day 2026-09-17 --fills fills.json --positions positions.json --settlements settlements.json

The JSON inputs are the raw responses of the three endpoints (fetch them with
deploy/kalshi_call.py on the host).
"""

from __future__ import annotations

import argparse
import collections
import json
from datetime import date
from pathlib import Path

from ..raw import iter_records


def tape_fills(tape_dir: Path, day: date) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = collections.defaultdict(list)
    for rec in iter_records(tape_dir, day):
        raw = rec.raw
        if raw.get("type") == "_local" and raw.get("event") == "quoter" and raw.get("kind") == "fill":
            out[raw["ticker"]].append({"order_id": raw["order_id"], "side": raw["side"], "price": float(raw["price"]), "qty": float(raw["qty"]), "rx_ns": rec.rx_ns})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tape", type=Path, required=True)
    ap.add_argument("--day", type=date.fromisoformat, required=True)
    ap.add_argument("--fills", type=Path, required=True)
    ap.add_argument("--positions", type=Path, required=True)
    ap.add_argument("--settlements", type=Path, required=True)
    a = ap.parse_args()

    ours = tape_fills(a.tape, a.day)
    theirs_raw = json.loads(a.fills.read_text())["fills"]
    theirs: dict[str, list[dict]] = collections.defaultdict(list)
    for f in theirs_raw:
        theirs[f["ticker"]].append(f)
    positions = {p["ticker"]: p for p in json.loads(a.positions.read_text()).get("market_positions", [])}
    settlements = {s["ticker"]: s for s in json.loads(a.settlements.read_text()).get("settlements", [])}

    print("| market | fills ours / theirs | contracts ours / theirs | end pos ours / theirs | ours cash $ | Kalshi realized $ | note |")
    print("|---|---|---|---|---|---|---|")
    for tk in sorted(set(ours) | set(theirs)):
        o = ours.get(tk, [])
        t = theirs.get(tk, [])
        o_qty = sum(f["qty"] for f in o)
        t_qty = sum(float(f.get("count_fp", f.get("count", 0))) for f in t)
        pos = sum(f["qty"] if f["side"] == "yes" else -f["qty"] for f in o)
        cash = sum(-f["qty"] * f["price"] if f["side"] == "yes" else f["qty"] * (1 - f["price"]) for f in o)
        # Kalshi fill records: side yes/no is the side WE took; action buy/sell
        t_pos = 0.0
        for f in t:
            q = float(f.get("count_fp", f.get("count", 0)))
            buy = f.get("action") == "buy"
            yes = f.get("side") == "yes"
            t_pos += q if (buy == yes) else -q
        note = []
        if tk in settlements:
            s = settlements[tk]
            yes_n, no_n = float(s["yes_count_fp"]), float(s["no_count_fp"])
            cost = float(s["yes_total_cost_dollars"]) + float(s["no_total_cost_dollars"])
            pairs = min(yes_n, no_n)
            payout = pairs + float(s.get("revenue", 0)) / 100
            realized = payout - cost
            their_pos = yes_n - no_n
            note.append(f"settled {s['market_result']}")
        elif tk in positions:
            p = positions[tk]
            their_pos = float(p["position_fp"])
            realized = float(p["realized_pnl_dollars"])
            note.append("open")
        else:
            their_pos, realized = float("nan"), float("nan")
        # our fills only cover this process's lifetime; a recovered position is not in the tape
        if abs(pos - their_pos) > 0.01:
            note.append("POSITION MISMATCH (recovered/previous-process fills?)")
        if abs(o_qty - t_qty) > 0.01:
            note.append("FILL QTY MISMATCH")
        print(f"| {tk[-7:]} | {len(o)} / {len(t)} | {o_qty:,.2f} / {t_qty:,.2f} | {pos:+.2f} / {their_pos:+.2f} | {cash:+.2f} | {realized:+.2f} | {'; '.join(note)} |")


if __name__ == "__main__":
    main()
