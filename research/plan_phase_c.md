# Phase C plan: validation on accumulated data, then paper trading

Status 2026-09-15: ~26h recorded (Sun 13 -> Mon 14 ET), one regime. All
models (alpha, edge tables, hazards) were fit and tested within that day.

## Data wanted

- Minimum 1 week, preferred 2: 5 weekdays with US hours, plus at least one
  high-vol day (macro print or >3% BTC move). ~700-1,400 markets.
- Power is not the constraint (per-market sd ~$35 vs mean ~$50); regime
  coverage and out-of-sample transfer are.
- Move both recorders to the AWS host now: the laptop dropped the network
  twice on 2026-09-14 (13:00-14:30, 18:00-20:30 ET) and hour files 17-18
  UTC are ~5% of normal size.

## Steps

1. Walk-forward ledger, automated daily: for day D fit alpha, edge tables
   and hazards on days < D; run the fixed config set (base, + join gate,
   + Greeks cap, max pos 100/200/300) on day D; append P&L, spread,
   adverse, c/contract, fill share, sd per config.
2. Go/no-go for the production quoter, from the ledger:
   - walk-forward P&L > 0 on >= 5 of 7 days for base + join gate
   - adverse selection per contract within +/-50% of the day-1 estimate
     on the high-vol day
   - alpha OOS correlation >= 0.1 and join gate >= neutral on unseen days
   - worst day no worse than -2x the mean day
3. In parallel (no data needed): recorders on the same-AZ host with
   systemd; tail-corrected kernel from historical candles (Greeks and
   valuation only); Go quoter skeleton with paper mode, logic per sim.py.
4. Impact calibration: paper run at 5-10 lots from the AWS host; compare
   realized fill share and own-fill markouts with the sim at that size.
   This decides deployment size.
