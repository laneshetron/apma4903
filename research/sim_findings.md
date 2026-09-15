# Phase B step 4: quoter simulation — first results (2026-09-14, KXBTC15M)

Data: 46 markets (~11.5h), 45M records. Model: `python/kalshi_data/research/sim.py`.
Tables: `sim_2026-09-14.md`, `sim_2026-09-14_sweep.md`.

## Base configs (100 contracts/side, max position 500)

| config | P&L | matched round trips | remainder | t (46 mkts) | c/contract | fill share |
|---|---|---|---|---|---|---|
| home 40ms, no signal | −$547 | −$1,406 | +$860 | −0.7 | −0.03 | 2.6% |
| AWS 2ms, no signal | +$1,832 | +$573 | +$1,258 | 2.7 | +0.06 | 4.0% |
| AWS 2ms, cancel on $2/1s spot move | +$2,487 | +$1,350 | +$1,137 | 2.9 | +0.10 | 3.1% |
| … pessimistic queue (cancels never help us) | +$2,548 | +$1,098 | +$1,450 | 3.1 | +0.16 | 2.0% |
| … + stop quoting 5 min before expiry | +$2,809 | +$1,471 | +$1,338 | 4.6 | +0.17 | 2.1% |

## Latency sweep (cancel $2/1s, stop 5 min)

| latency | 1ms | 2ms | 5ms | 10ms | 20ms | 40ms | 80ms |
|---|---|---|---|---|---|---|---|
| P&L | $3,638 | $2,957 | $1,528 | $1,097 | $1,257 | $1,170 | $842 |
| realized | $2,275 | $1,615 | $582 | $579 | $866 | $815 | $601 |
| t | 6.0 | 4.8 | 2.6 | 1.9 | 2.2 | 2.1 | 1.5 |

The cliff is between 2ms and 5ms — the queue race (second joiner at 2ms median).

## Size sweep (2ms, cancel $2/1s, stop 5 min, max position = 5x size)

| size/side | 50 | 100 | 200 | 500 | 1000 |
|---|---|---|---|---|---|
| P&L | $1,548 | $2,957 | $5,557 | $10,964 | $15,359 |
| realized | $926 | $1,615 | $2,977 | $4,489 | −$85 |
| fill share of market volume | 1.1% | 2.0% | 3.5% | 6.7% | 9.9% |

Roughly linear to size 500; at 1000 the realized spread vanishes and the P&L is
all inventory mark (we are just accumulating position), and the no-impact
assumption is clearly violated.

## Reading

- With same-AZ latency, a spot-aware touch quoter is positive in this sample:
  ~+0.17c/contract, ~$3k per 46 markets => ~$6k/day gross at 100 lots if the
  numbers held (they will not hold fully; see caveats). Own-fill 30s markout is
  +0.1 to +0.2c, versus −0.56c for a back-of-queue order: queue position and
  cancel-on-signal convert the toxic flow problem into a manageable one.
- Decomposition (per fill, against the pre-sweep mid): spread capture is the
  half-spread, ~0.37c/contract, on every fill; inventory P&L (position x mid
  moves afterwards) is NEGATIVE in every config, −0.2 to −0.4c/contract, and
  almost entirely within 10s of the fill. There is no mean-reversion gain.
  The net edge is the residual: 0.37c earned minus ~0.25c given back.

  | config | spread | inventory | of which <10s | net c/contract |
  |---|---|---|---|---|
  | home 40ms, no rules | +$7,865 | −$8,307 | −$9,795 | −0.02 |
  | AWS 2ms, no rules | +$12,235 | −$10,298 | −$10,579 | +0.06 |
  | AWS 2ms, cancel $2/1s | +$9,286 | −$6,517 | −$6,573 | +0.11 |
  | … + stop 5 min | +$7,319 | −$4,129 | −$4,077 | +0.19 |

  Every lever (latency, cancel-on-signal, endgame stop) works by shrinking
  the adverse term. A ~30% rise in adverse selection — e.g. from our own
  market impact — erases the edge; that is the scale on which the no-impact
  caveat matters. (An earlier realized/unrealized split in this file
  suggested a positive inventory mark; that was an artefact of pairing buys
  with later sells and is superseded by this decomposition.)
- Stopping 5 min before expiry beats 2 min: the endgame is where losses sit.
- Home latency without the extra rules loses; with them it is marginally
  positive but fragile (t~2).

## Caveats (in order of importance)

1. **No market impact.** The sim assumes 100-1000 lots at every touch change
   nothing about other participants. At 2-7% of market volume that is false:
   real fill share will be lower and informed flow will find us more often.
   Only a live, small-size paper run can calibrate this.
2. **One day, one regime.** 46 markets from a single session. Needs several
   days including a high-vol session before the t-stats mean much.
3. **Inventory carried to the stop time** is marked at mid; the pessimistic
   flatten bound (cross + taker fee) was $165-230 total, small, but a
   350-contract average end position near expiry is a real risk if passive
   unwind fails.
4. Queue model: pro-rata vs pessimistic barely changes P&L, so this is not the
   driver.

## Next

1. Re-run daily as data accumulates (`sim.py <date>`); look for sign
   stability across days and vol regimes.
2. Calibrate market impact with a live paper run: real orders, 5-10 lots, in
   the target AZ; compare realized fill share and own-fill markouts to the
   sim's predictions at that size.
3. Only then: production quoter in Go (fair value from spot feeds, queue-aware
   requoting, cancel-on-signal, inventory skew, endgame stop).

## Inventory: position-limit sweep (2ms, cancel $2/1s, stop 5 min)

| max position | P&L | per market | sd per market | mean/sd | c/contract | avg end position |
|---|---|---|---|---|---|---|
| 100 | $1,382 | $28 | $18 | 1.58 | 0.17 | 34 |
| 150 | $1,974 | $39 | $28 | 1.41 | 0.16 | 53 |
| 200 | $2,399 | $48 | $36 | 1.35 | 0.17 | 82 |
| 300 | $2,804 | $56 | $49 | 1.14 | 0.18 | 136 |
| 500 | $3,195 | $64 | $89 | 0.72 | 0.19 | 283 |
| 1000 | $3,101 | $62 | $182 | 0.34 | 0.17 | 647 |

The per-contract edge is flat: inventory control does not change fill
quality (the adverse term is a property of the fill process). It changes
risk: 500 -> 100 gives up 57% of the mean for 80% of the variance, and
removes most of the settlement tail. Above ~300 extra inventory adds
variance and no P&L. A hard one-sided stop is the crudest controller; a
continuous skew (Avellaneda-Stoikov / GLFT reservation price, threshold-
shaped by the 1c tick) plus a receding-horizon endgame unwind is the
candidate to beat this baseline: target the ~$56/market of the 300 limit
at the $18-36 sd of the 100-200 limits.

## Adverse-selection filters in the sim (2ms, cancel $2/1s, stop 5 min, max pos 200)

Signals from `alpha_2026-09-14.md` used as presence rules (don't rest a side
when flagged). Tables: `sim_2026-09-14_filters.md`, `sim_2026-09-14_filters2.md`.

| rule | day P&L | spread | adverse | c/contract | fill share |
|---|---|---|---|---|---|
| base | $2,447 | $6,438 | −$3,993 | 0.16 | 1.55% |
| alpha tail cut ($3 over 5s) | $2,485 | $5,997 | −$3,513 | 0.18 | 1.44% |
| Greeks cap (delta x sigma10 >= 5c) | $2,328 | $5,570 | −$3,243 | 0.17 | 1.37% |
| thin-touch veto (< 100) | $2,172 | $4,580 | −$2,407 | 0.20 | 1.11% |
| imbalance veto (0.6) | $2,188 | $2,461 | −$270 | 0.35 | 0.63% |
| imbalance veto (0.33) | $1,784 | $1,472 | +$313 | 0.47 | 0.39% |
| all five, queue-aware keep | $724–775 | $768–839 | −$44–64 | 0.43 | 0.17% |

The signals work: the adverse term can be driven to zero. Total P&L does
not improve because (1) the vetoed flow is net positive (0.37c spread vs
~0.25c adverse), so a veto gives up more than it saves, and (2) every veto
resets queue position in a FIFO market; queues are thousands deep so a
"keep if near the front" exception rarely applies.

Conclusion: use toxicity signals to modulate size and skew (continuous, no
queue reset) and gate presence only in the extreme tail. Keep the alpha
tail cut and the Greeks cap (P&L-neutral, better quality, principled
endgame). The signals matter most at larger size (fills constrained by our
own impact) and on worse-than-today adverse-selection days — this is a
quality/quantity frontier whose right operating point depends on capacity
and regime.

## Value-function hold/cancel policy (2ms, max pos 200, stop 5 min)

`queue_value_2026-09-14.md`: expected edge (half-spread + 30s markout) of a
resting 100-lot by contracts ahead and state. Queue position matters (front
+0.5c, back of 2,000+ negative) but state dominates: "other side deeper"
and "microprice agrees with taker" are negative at every position.
Vetoing those states nevertheless lost money because the states are
transient while a cancel forfeits the queue position permanently.

Policy: cancel a live order when edge(q, state) < -theta for at least a
debounce time (stand-in for the DP's episode/hazard term); rejoin when
edge >= 0. Edge table fit on the first 60% of the day.

| policy | day P&L | adverse | c/contract | OOS P&L (32 mkts) | OOS adverse |
|---|---|---|---|---|---|
| base | $2,861 | −$4,539 | 0.16 | $1,269 | −$1,567 |
| cancel if edge < 0, 300ms debounce | $2,901 | −$3,462 | 0.19 | $1,128 | −$1,322 |
| cancel if edge < 0, no debounce | $2,415 | −$1,913 | 0.23 | $965 | −$697 |

More efficient than flags (11-24% of P&L for 16-56% less adverse
selection, vs 20-30% for the vetoes) but no OOS gain in total P&L on this
day. Next: hazard conditional on the adverse state and a continuation term
for queue advancement (the real DP), and a second day of data.

## DP hold/cancel with measured parameters (hazard.py, --probe, --join)

Measured: sweeps hitting a side arrive at ~8/s (12/s while that side is thin
with spot leaning against it; 2.3x for sweeps > 500 contracts); adverse
book/microprice episodes last 0.05-0.13 s; resting orders advance at
~1,245 contracts/s (pro-rata) / 512/s (pessimistic), median time to first
fill 0.6 s, 22-35% of placed orders fill before being requoted.

Consequences: a queue position is worth ~1 s of advancement, a transient
adverse episode costs ~0.1 s of elevated hazard — cancelling is a ~10:1
losing trade, which is why every cancel-based rule lost. The decision with
no position at stake — whether to JOIN — is where the signals pay:

| config (2ms, max pos 200, stop 5 min) | day P&L | adverse | OOS P&L | OOS adverse | sd/mkt |
|---|---|---|---|---|---|
| base | $2,994 | −$4,761 | $1,402 | −$1,691 | 35 |
| join gate: edge(depth, state) >= 0 | $3,008 | −$4,031 | $1,342 | −$1,460 | 33 |
| join gate + hold policy (300 ms) | $2,984 | −$3,404 | $1,238 | −$1,317 | 36 |

Policy structure: (1) gate joins on expected edge; (2) hold through
transient states; (3) leave/avoid persistent adverse regimes (time to
expiry, moneyness: Greeks cap, endgame stop); (4) inventory limit/skew.
A full state-space DP adds little while queues advance this fast; revisit
for slow markets or sizes where our orders dominate the queue.

## Fair value model (fair.py, sim --fair)

Settlement-aware model (60s BRTI average vs strike, realized vol). Validation
(`fair_2026-09-14.md`): calibration vs settlement equals the Kalshi mid's;
corr with mid 0.99; typical |fair − mid| 3.6c; mid = 0.935 fair + 0.04 (the
market prices more vol than 5-min realized); the gap predicts mid
convergence weakly (beta 0.04 at 10s, 0.12 at 60s; >3c gap -> ~1c move in
30s).

As a quoting gate it sits on the same quality/quantity frontier as the other
filters and below the edge join gate (P&L −11% to −30%, c/contract 0.19–0.24,
vetoes lopsided toward the bid by the +1.15c bias). Roles that remain:
Greeks for regime and inventory skew, position valuation and the endgame
mechanics, and a small drift term in the reservation price.

## Fair value tails and delta-scaled repricing (sim --dfair, --dfair2)

Tail check (`fair.py` + standardized realized outcomes): vol level is right
(implied 0.64 vs realized 0.57-0.65 bp/sqrt-s; std of standardized outcomes
1.03) but the shape is not normal: fewer moderate moves, fatter tails, and
the market prices ~t(3-4)-like tails (P(YES | 2-sigma strike) 3.6% vs 0.8%
normal). |fair - mid| (~3.5c) does not scale with delta -> model-form error
in the tails, not reference-price noise.

Delta-scaled repricing (cancel when fair moved >= 0.25-1c against the
quote, Coinbase spot, normal or fat-tailed kernel): $2,605-2,943 vs $2,994
for the flat "$2 spot move in 1s" rule; adverse -5.8k to -7.2k vs -4.8k.
The flat rule works as a market-wide toxicity signal (informed flow active
now), not as a staleness correction; a corrected kernel does not change
adverse selection. Keep the tail fix for Greeks, inventory valuation and
the endgame.

## Market impact event study (impact.py, 2026-09-14/15)

Response of the book to a single order joining the touch, by size: cancels,
joins, taker volume, sweep probability and mid move are flat across 1-20 to
>=1000 contracts (e.g. swept within 1s 23-25% for every bucket; Δmid
+0.1-0.3c with no trend; cancels 3.4-3.9k/s vs 3.5k control). Others join
behind large orders slightly more and taker volume at the level is 10-15%
higher. Touch churn (~3.5k cancels and ~5k joins per second on a ~3k level)
makes a 100-lot order noise. Improving orders are more exposed: 1-100 lot
improvers are swept within 1s ~50% of the time.

The no-impact assumption for joining at <=100 lots is supported for
mechanical impact; adaptive impact (competitors learning a persistent
quoter) remains untested and is the reason for the live run, which can
start at 50-100 lots.

## Day-2 rerun (2026-09-15, 59 markets through 15:50 UTC, tables fitted on 09-14)

Out-of-sample walk-forward on the first clean collection day (`sim_2026-09-15_walk.md`, `alpha_2026-09-15.md`). Day 2 was 45% busier than day 1 (136M vs 94M contracts swept by 15:50 UTC).

| config | day 1 (in-sample, 50 mkts) $/mkt | ¢/ct | t | day 2 (OOS, 59 mkts) $/mkt | ¢/ct | t |
|---|---|---|---|---|---|---|
| base 2ms, cancel $2/1s, stop 5min, max pos 200 | 47.98 | 0.17 | 9.5 | 25.32 | 0.09 | 4.9 |
| + join gate (edge >= 0) | — | — | — | 25.98 | 0.10 | 5.0 |
| + join gate + greeks cap 5¢ | — | — | — | 24.09 | 0.12 | 5.5 |
| base, max pos 100 | 27.65 | 0.17 | 11.2 | 21.43 | 0.13 | 8.5 |
| home 40ms, no rules, stop 2min | ≈0 | -0.02 | -0.6 | -29.91 | -0.07 | -3.7 |

- Still profitable out of sample at every same-AZ config; t-stats 5-8.5 on 59 markets. Net edge per contract roughly halved for max pos 200 (0.17 -> 0.09¢): spread capture per contract is the same (0.43¢) but adverse selection at 10s rose from ~0.26¢ to 0.37¢/ct. Max pos 100 degraded least (0.17 -> 0.13¢) and has the best t-stat, consistent with the day-1 risk-efficiency finding.
- Home latency flipped from breakeven to clearly negative (-$30/mkt). The same-AZ requirement is not optional.
- Join gate and greeks cap transfer out of sample: neutral-to-slightly-positive on P&L, 10-35% less adverse, higher ¢/ct and t-stat. Rules fitted on day 1 did not overfit.
- α stability: Kalshi book-state features (touch imbalance, prior full sweep, touch depth) reproduce within 0.1¢ across days. The spot ridge α does not: OOS corr 0.17 -> 0.10 and ret_30s, kr_minus_cb, kraken/bitstamp 5s flow all flipped sign. Only cb_imb, coinbase_flow_1s and gemini_btc_flow_5s are stable; trim the α model to those.
- Day-2 bucket where α > +$2: spot moved +$4.77 in the taker's direction but maker markouts were ~flat (-0.07¢ at 1s vs -0.21¢ on day 1) — the spot->Kalshi pass-through varied between days, another reason not to use α as a veto.
