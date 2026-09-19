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

## Day-2 rerun (2026-09-15, tables fitted on 09-14)

Out-of-sample walk-forward on day 2 (`sim_2026-09-15_walk.md`, `alpha_2026-09-15.md`). Table below is the 15:50 UTC cut (59 markets); the full day (78 markets, US afternoon holey from laptop outages) came in at base $25.93/mkt (t 6.1, 0.10c/ct), join gate $25.69, join+greeks $24.97 (t 6.7, 0.13c/ct), max pos 100 $20.13 (t 9.5, 0.14c/ct), home 40ms negative. Same picture.

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

## Vol vs P&L per market, and KXBTCD (2026-09-14 to 09-15)

Per-market base-config P&L joined with each market's median realized BRTI vol (`permkt_<day>.parquet`, `fair_<day>.parquet`; 120 markets):

| BRTI vol quartile | median vol (bp/sqrt-s) | P&L/mkt | spread $ | adverse $ | contracts | c/ct |
|---|---|---|---|---|---|---|
| low | 0.34 | 33 | 144 | -111 | 32k | 0.10 |
| mid-low | 0.46 | 34 | 125 | -91 | 30k | 0.11 |
| mid-high | 0.58 | 33 | 113 | -80 | 28k | 0.12 |
| high | 0.99 | 39 | 90 | -53 | 23k | 0.17 |

- Within a day vol does not hurt: P&L/market is flat-to-up and c/ct rises with vol because cancel-on-signal keeps us off the touch during moves (30% fewer contracts, proportionally less adverse).
- The day-2 degradation is therefore not vol. Day 2 markets were less volatile (median 0.47 vs 0.58) yet adverse selection per market rose (-$69 -> -$99) at similar spread capture in every UTC session. It is flow composition (more informed volume per unit of spread), the nonstationarity the daily ledger must track.
- Widening on a 1c-tick market = queueing behind the touch: only multi-level (most informed) sweeps reach a one-tick-back quote; the partial-sweep uninformed flow (54-61% of volume, +0.2-0.3c) never does. Queue-position table already says edge turns negative past ~1000 ahead.

KXBTCD (hourly strikes, `markouts_KXBTCD.md`): 52.8M contracts over the two days, 7,354 markets. Fill-conditioned (full+multi) markout -1.08c at 1s / -0.89c at 30s vs +0.48c half-spread — worse than KXBTC15M (-0.56 / -0.99 vs +0.32). Partial sweeps are ~0 (vs +0.2-0.3c on 15M), full sweeps are 13% of volume (vs 6%), and 22% of volume is post-signal (vs 11%). Lower gamma does not buy a calmer regime; the flow is simply sharper. Not a candidate.

Spot recorder now also records perps: coinbase_perp (INTX via Advanced Trade WS), kraken_futures, okx, bybit, hyperliquid (from 2026-09-15 17:23 UTC).

## Perp feeds as a repricing signal (2026-09-15 17:25-22:40 UTC, `perp_lead_2026-09-15.md`)

- Lead/lag of 100ms mid returns vs Coinbase spot: OKX and Bybit lead by ~100ms on exchange timestamps (asymmetry +0.15 / +0.12) but their feeds arrive ~90-110ms late, so by receive time there is no lead; Coinbase INTX perp, Kraken futures and Hyperliquid lag spot outright.
- Sweep-conditioned (208k sweeps, 31M contracts): no perp's prior 300ms/1s move agrees with the taker more often than Coinbase's does. Of full+multi sweeps Coinbase calls quiet (55% of informed volume) only 1-3% had a perp move >= 1bp in the taker's direction, and their markouts are no worse.
- Conclusion (one holey afternoon; rerun on a clean day): the residual adverse selection is not an upstream BTC price lead. Kalshi book-state features remain the only stable predictors. Perps stay recorded but are not a planned input.

## Day 3 (2026-09-16 through 15:40 UTC, 60 markets, tables fitted on 09-15)

| config | 09-14 in-sample | 09-15 OOS | 09-16 OOS |
|---|---|---|---|
| base 2ms, max pos 200: $/mkt (c/ct, t) | 47.98 (0.17, 9.5) | 25.93 (0.10, 6.1) | 25.56 (0.11, 4.7) |
| + join gate | — | 25.69 (0.11, 5.9) | 30.35 (0.13, 5.9) |
| + join gate + greeks cap | — | 24.97 (0.13, 6.7) | 23.41 (0.14, 4.9) |
| base, max pos 100 | 27.65 (0.17, 11.2) | 20.13 (0.14, 9.5) | 18.01 (0.13, 6.8) |

- Two consecutive OOS days agree: ~$25/mkt base, join gate adds +$5 on day 3 (best day-3 config), greeks cap trades P&L for ¢/ct. Day-1's $48 was the optimistic draw.
- Adverse-selection features stable for a third day (other-side-deeper -1.01c, prev full sweep -1.22c at 1s); spot ridge OOS corr 0.17 -> 0.11 -> 0.085, only cb_imb stable.
- Perp lead/lag on a clean 15.7h window (`perp_lead_2026-09-16.md`): OKX/Bybit lead Coinbase by ~100ms intrinsically (asym +0.48/+0.39) but transport lag (70-90ms) removes it by receive time; the other perps lag. Only 0.5-1.2% of Coinbase-quiet informed sweeps had a perp move first. Closed: perps are not the missing signal.

## AWS deployment measurements (2026-09-16, us-east-2)

AZ probe (`deploy/azprobe.py`, `deploy/az-*.json`): WS load-balancer nodes in all three AZs; nodes in use2-az1 pay ~1.1 ms extra to reach the WS backend, az2/az3 nodes ~1.1-1.25 ms total. With the az3 recorder idle and the az2 recorder loaded, az2 still wins on every metric: intra-AZ TCP RTT 0.16-0.18 vs 0.34-0.37 ms, WS TTFB 1.32 vs 1.36 ms, trading-api 0.26 vs 0.44 ms. Recorder load on a t3.micro inflated the earlier az3 TTFB by ~0.1-0.2 ms, so the first-pass az2 margin was overstated; the ranking stands. Deployed in **use2-az2**.

Feed arrival from az3, 17:35-18:30 UTC, exchange timestamp -> our receipt (p10/p50/p90 ms): Coinbase 9/11/34, Kraken 50/55/78, OKX 81/82/85, Bybit 104/107/113, Kraken futures 50/67/287, Coinbase perp 117/175/220, Hyperliquid 267/316/437. Kalshi: engine ts_ms -> receipt 4.8/6.2/8.1 ms (deltas), Kalshi's BRTI received_at -> receipt 3.8 ms, CF source -> receipt 43 ms.

Laptop clock caveat: identical Kalshi messages show laptop rx *earlier* than AWS rx by 2.8 ms median, i.e. the laptop clock ran ~15 ms fast. Absolute lags measured on the laptop were understated by that much; relative timings (both legs on the laptop clock) are unaffected.

Clock-independent taker speed (Kalshi engine ts_ms minus Coinbase exchange ts, KXBTC15M trades within 1 s of a $2/1s Coinbase move, 1.2M contracts): 4% within 5 ms, 7% within 12 ms, 11% within 30 ms, 28% within 100 ms. From Ohio we see Coinbase at ~11 ms and can cancel by ~12-13 ms engine time, so ~93% of post-signal volume is dodgeable; a us-east-1 taker gains nothing on us because Coinbase->Ohio and Virginia->Ohio are the same hop.

## Order-entry latency and the AWS tape (2026-09-16)

REST order entry from use2-az2 (`cmd/orderprobe`, 50 iterations each): auto-routed create 11.2 ms send->engine ts_ms (p90 13.5), cancel 6.7; with explicit `exchange_index=2` create 9.0 (p90 11.8), cancel 5.2 (p90 5.9). Engine->HTTP ack 1.5 ms; engine->public delta / user_orders ~5.5 ms. Tier (Basic->Advanced) has no latency effect. FIX (`cmd/fixprobe`, KalshiNR) logon rejected: "API usage level is not allowed for FIX" (Premier tier; 100M contracts/30d or manual grant).

Latency sweep on the laptop tape (day 3, OOS) put break-even at ~3-4 ms placement latency, with placement dominant over the spot-cancel leg. But a matched 12-market comparison showed the laptop tape fills ~65% fewer contracts than the AWS tape at identical settings: the tape's own receive delay (laptop ~19 ms + jitter vs AWS 6-7 ms) is added to modelled latency and pushes us back in every queue. Laptop-tape results were a pessimistic bound.

AWS tape, 17:35-22:10 UTC, 18 markets, tables from 09-15 (`sim_2026-09-16_awstape.md`): 2 ms reference $42.9/mkt; REST explicit (place 9 / cancel 5 / spot-cancel 11) $19.2 (0.10c/ct, t 2.3); + join gate + greeks cap $28.3 (0.21c/ct, t 3.7); max pos 100 $11.8; FIX-like 5/3/9 $27.5; 3/3/9 $30.6. The REST path with the two rules keeps ~65% of the zero-latency P&L.

Upstream feed lag from Ohio: Coinbase (ws-feed, via Cloudflare) 11 ms p50 in calm periods but 100-130 ms p50 / 1-1.5 s p90 in busy 10-minute windows (18:00-18:20 UTC); OKX flat 79-84 ms at 20x the message rate; Kalshi deltas flat 7 ms. Coinbase stalls are Coinbase-side. Sweeps bucketed by the delivery lag of our latest Coinbase message: 74% of volume arrives with a fresh (<15 ms) view; the 15-300 ms buckets (19% of volume) show full+multi markouts of -0.35 to -0.68c at 1s vs -0.32c fresh. Real but modest (~0.03c/ct overall); a freshest-source composite signal (OKX/Bybit when Coinbase is stalled) is a cheap incremental improvement, not the main adverse-selection source.

Kalshi WS delivery (engine ts_ms -> receipt) is 6-7 ms and identical on the single-market probe connection and the 320-market collector connection; second joiners at a fresh level arrive ~2 ms after the first, so they are not reacting to the WS delta. The race is won by pre-positioning (resting one tick away before the level forms), not by parsing faster. That is the next sim variant.

## Feed-quality rules and multiple WS connections (AWS tape 2026-09-16, `sim_2026-09-16_feeds.md`)

Standing config (REST explicit + join gate + greeks cap): $28.3/mkt, 0.21c/ct, t 3.7. Every feed rule tested lowers it:
- pull quotes while the latest Coinbase message was >30 / >100 / >300 ms late: $18.6 / $21.5 / $19.9. Same lesson as the presence vetoes: leaving the touch costs queue position and spread capture more than the stale-feed adverse selection it avoids.
- composite cancel signal (coinbase|okx|bybit): $14.0; OKX-only: $22.7. The 80 ms-lagged venues add late, redundant cancels that mostly cost queue position.
Conclusion: keep Coinbase as the sole cancel signal; feed staleness is not worth acting on. Rules that decide *before* joining (join gate, greeks cap) transfer; rules that pull resting orders do not.

`cmd/wsprobe`: four connections pinned to az2 WS nodes, same market, 98k deltas: engine->rx 5.6-5.9 ms p50 per connection; taking the earliest copy of each delta gains mean 0.88 ms (p50 0.56, p90 1.9, p99 5.9) over a single connection. Node 18.217.10.53 was first 39% of the time and ~0.3 ms faster at p50. Cheap and worth building into the quoter: pin to the fastest node and de-duplicate 2-3 sessions by content.

Gemini as a cancel-signal venue (`sim_2026-09-16_feeds2.md`; Gemini top-of-book quotes now normalized, 677k updates vs Coinbase's 134k in 4.6 h, exchange ts -> receipt 28/48/81 ms p10/p50/p90 from Ohio): gemini-only $19.1/mkt (0.16c/ct), coinbase|gemini $22.4, coinbase|kraken $27.1, vs Coinbase-only $28.3. Gemini is a stable, moderately lagged feed and the best fallback among what we record, but it neither replaces nor improves on Coinbase as the trigger.

## Capital-constrained sizing (AWS tapes 09-16 17:35-24:00 and 09-17 00:00-02:45, 36 markets, `sim_*_capital.md`)

Sim now reserves price x qty for resting bids and holds collateral against the NET position (offsetting pairs settle, as on Kalshi). Standing rules (join gate, greeks cap, explicit-shard latencies) throughout.

| config | 09-16 $/mkt (c/ct, t) | 09-17 $/mkt (c/ct, t) | contracts/mkt |
|---|---|---|---|
| size 100 / max 200, unlimited | 22.7 (0.14, 2.9) | 25.6 (0.12, 2.8) | 16-22k |
| size 5 / max 10, $5 (the live run) | 0.05 (0.01, 0.1) | -0.73 (-0.14, -0.8) | 400-500 |
| size 10 / max 50, $100 | 3.56 (0.16, 1.5) | 4.38 (0.14, 1.5) | 2.2-3.1k |
| size 20 / max 100, $100 | 8.07 (0.19, 1.7) | 7.89 (0.13, 1.5) | 4.2-6.0k |
| size 20 / max 60, $150 | 3.22 (0.08, 1.1) | 5.67 (0.10, 1.6) | 3.9-5.6k |
| size 50 / max 100, $300 | 9.96 (0.12, 2.3) | 11.61 (0.10, 2.4) | 8.4-11.8k |

- $100 is not binding for size 10 / max 50 (identical to unlimited): the position rarely needs more than $50. $100 also carries size 20 / max 100 at ~$8/mkt.
- size 5 / max 10 is ~zero in the sim as well: pinned at the cap, one-sided. Consistent with the live result.
- Per-contract edge is flat across sizes (0.10-0.19c); P&L scales with contracts traded, i.e. with size, so capital buys throughput roughly linearly until the cap binds.
- Live sizing with polled balance: Kalshi's balance is gross cash; free = balance - resting reservations - fills since the poll (conservative for closing fills).

## Inventory: caps, flatten at stop, A-S size skew (AWS tapes 09-16/09-17, 40 markets, `sim_*_{caps,flatten,flat,sizeskew}.md`)

- The sim (and paper mode) never settled positions: end-of-market inventory was marked at the T-5min mid. Live carried +80 YES into a NO settlement on 2026-09-17 00:45 UTC (-$44 on $100). `flatten_at_stop` (take the touch at T-5, taker fee) costs ~$0.6/mkt at size 20 and is the missing step that makes live match what the sim assumed. Now on in the Go quoter.
- Taking to flatten intra-market is ruinous (paying ~1c spread vs 0.2c edge): "take above 20" -$33..-$42/mkt. Takes are a backstop only.
- Skewing PRICE (improving the reducing side) cannot be evaluated on the tape (fills at levels that did not exist); live-only.
- Position cap sweep (size 20, $100, flatten): cap 100 $7.5/6.1 per mkt SD 23/18; cap 40 $2.9/4.7 SD 10/7.8; **cap 20 $3.2/2.6 SD 3.6/4.5 (t 4.5/2.2)**. Per-contract edge unchanged (0.10-0.15c): inventory adds variance, no return.
- A-S by SIZE (increasing side size*(1-|q|/cap), reducing side size*(1+|q|/cap)): cap 40 + skew $5.1/4.5 per mkt, SD 7.7/7.1, t 3.3/2.5, avg max pos ~30; at the standing size $24.6/21.2 (from 22.7/17.3) with lower SD. Best mean per unit variance among the tested configs; cap 20 remains the lowest-variance.
- Live config as of 2026-09-17 04:15 UTC: size 20 / max 20 / flatten at stop / $20 session stop. Candidate upgrade after a baseline: size 20 / max 40 + size skew.

## Why live loses where paper wins (2026-09-17 04:13-04:45 UTC, cap-20 config, same markets, `fill_markouts.py`)

| | fills | contracts | half-spread at fill | mo 1s | mo 10s | mo 30s | P&L@30s |
|---|---|---|---|---|---|---|---|
| live | 567 | 8,491 | +0.23c | -0.08 | -0.15 | **-0.18c** | -$15.5 |
| paper | 776 | 8,912 | +0.21c | +0.03 | +0.06 | **+0.03c** | +$2.8 |

Spread capture is identical; adverse selection is 2x worse live (-0.41c vs -0.18c per contract). Split by whether our level was emptied within 300 ms of the fill: live fills are 36% full-sweep (mo30 -0.97c) vs paper 25% (-0.62c); partial-sweep fills earn +0.27c in both. Live gets more of the toxic full-sweep fills and they are more toxic: the paper queue model (pro-rata cancels ahead of us) advances our order too fast, so paper fills on partial sweeps that never reach us in reality. Fix the model to FIFO with cancels from behind (`queue="pessimistic"`) and re-base every P&L estimate on it before trading again.

## Observed live queue positions vs the model (`queue_obs.py`, 994 live orders, 04:13-04:45 UTC)

| | live | sim prorata (same config/day) | sim FIFO |
|---|---|---|---|
| orders filled at least partly | **48%** | 39% | 21% |
| time to first fill p50 / p90 | 0.71 / 2.6 s | 0.78 / 2.4 s | 0.58 / 3.3 s |
| ahead at placement p50 | 1,461 | 2,349 | 1,850 |
| share of the level ahead that traded before our fill | p25 0.09, p50 0.44, p75 1.00 | — | — |

Live orders advance through the queue at least as fast as the pro-rata model (half of our fills came after <44% of the level ahead had traded), so queue position is not the problem. The loss is in *when* we get filled: fills on orders younger than 0.5 s (44% of contracts) mark out -0.37..-0.74c; fills on orders older than 2 s mark out +0.44c; improving orders +1.81c (35 fills). Order lifetime p50 is 0.41 s: the quoter reprices ~2.5x/s and is therefore always among the newest orders at freshly formed levels, which are exactly the levels that get swept. The toxicity is a product of our own repricing churn, not of the queue model.

## Price-priority fills: the tape can see most of the "invisible" demand (`sim_*_priority.md`)

A taker that trades at a worse price after clearing our level would, by price priority, have filled our resting order first. The sim only filled from trades AT our price, so it credited us with surviving multi-level sweeps (33% of volume, the informed class). With `price_priority=True`:

| config | 09-17 $/mkt (old model) | 09-17 (priority) | 09-16 (old) | 09-16 (priority) |
|---|---|---|---|---|
| live config (20/20, $100), prorata 9/5/11 | +2.13 | **-0.50** | +3.24 | **+0.59** |
| live config, FIFO + priority | — | -4.21 | — | -0.48 |
| standing 100/200, prorata 9/5/11 | +24.65 (FIFO) | **-8.69** | +2.49 | +6.39 |
| standing 100/200, 2/2/2 | — | +23.87 | — | +26.52 |

On the two markets traded live (00:30, 00:45 UTC): FIFO + priority gives -$14.5 on 514 fills / 6,380 contracts vs live -$15.5 on 567 fills / 8,491 — the corrected model reproduces the live loss. Conclusion: at the measured ~9 ms placement latency, touch-joining as configured has no edge; the earlier positive estimates were the artefact of ignoring sweeps that went through our level. Only the 2 ms rows remain positive (~$24-27/mkt at the standing size), i.e. the edge exists only at the very front of the queue.

## 2026-09-17 — post-audit evaluation (corrected model, both AWS days)

Model: price priority, engine lag 6 ms added to placement/cancel (AWS tape 9/5 → 15/11 tape-time), tapered tick grid, markets settled from the recorded BRTI 60 s average. 44 markets (25 on 09-16, 19 on 09-17), $100 capital, size 20 / cap 20 unless noted. `research/sim_2026-09-1{6,7}_eval.md`, per-market `permkt_eval_*.parquet`.

| config | 09-16 $/mkt (t) | 09-17 $/mkt (t) | pooled $/mkt (t) | win % | sweep fills* |
|---|---|---|---|---|---|
| **A3 join gate: level age ≥ 1 s + depth ≥ 300** | +0.50 (0.5) | +1.16 (1.5) | **+0.78 (1.2)** | 57% | 997 |
| C2 pre-position 1 tick + persistence | −0.78 | +0.28 | −0.32 (−0.8) | 48% | |
| C pre-position 1 tick | −1.10 | −0.19 | −0.71 (−1.0) | 52% | |
| live baseline 20/20 flatten | −0.42 | −2.59 | −1.36 (−1.8) | 48% | 3,180 |
| A2 level age ≥ 1 s only | −0.65 | −2.43 | −1.42 (−2.2) | 41% | 1,909 |
| A4 A3 + persistence | −1.27 | −2.30 | −1.71 (−2.8) | 41% | 2,869 |
| baseline, carry to settlement | −1.66 | −2.66 | −2.09 (−2.1) | | |
| A1 persistence (min rest 1 s, reprice ≥ 2 ticks) | −1.72 | −2.77 | −2.17 (−3.4) | 34% | |
| D2 cap 40 + size skew + A4 | −1.05 | −4.19 | −2.41 (−1.9) | | |
| D cap 40 + size skew | −0.58 | −5.19 | −2.57 (−2.0) | | |
| standing 100/200 flatten | +1.05 | −13.63 | −5.29 (−0.9) | | |
| standing 100/200 + A4 | −0.90 | −13.03 | −6.14 (−1.0) | | |
| raw touch quoter, no gates | −24.73 | −49.16 | −35.28 (−4.4) | | |

\* `priority_fills` on 09-17: fills we only receive because a taker swept through our level.

- **Only A3 is positive on both days**, and it is marginal: +$34 over 44 markets, t = 1.2, and 09-16 is carried by one market (+$9.96; ex-best +$2.42 over the other 24). 09-17 is broad (13/19 winners, median +$2.10). Expect ~$0.5–1/market at size 20, i.e. $50–100/day at 96 markets, before anything the tape cannot see.
- The ingredient is the **depth gate, not level age**: A2 (age alone) is no better than baseline; A3 cuts sweep fills from 3,180 to 997 and traded volume in half. The gate is also a presence veto (`spread ≤ tick` and our-side depth < 300 → cancel), so it leaves a level as it thins, before the sweep finishes.
- **Persistence hurts** everywhere (A1 −2.17, A4 < A3, C2 ≈ C): a resting order that is not repriced for 1 s is run over by the next move. The live "orders alive 2–5 s earned +0.44¢" was survivorship — the orders that lived that long were the ones nothing ran through. "Stop chasing" must be done by not joining, not by not leaving.
- Pre-positioning one tick behind (C) trades a tenth of the volume and still loses; the front-of-queue partials are not enough to pay for being the level a sweep lands on.
- Size skew at cap 40 (D, D2) is negative under the corrected model — larger inventory only buys more sweep exposure. The old "+75% mean" result is void.
- Settlement vs flatten: carrying to settlement costs $0.7/market vs flattening at T−5 (baseline −1.36 vs −2.09); flattening stays on.
- Standing size 100/200 loses at 9 ms with or without gates; nothing above size 20 is justified.

Next: neighbourhood of A3 (`--eval2`: depth 200/300/500 alone, age 0.5/1/2 s, + offset, + skew, + imbalance, size 10, carry) to check that A3 is not a knife-edge before porting the depth/age gate to the Go quoter.

### A3 neighbourhood and depth-threshold sweeps (`--eval2`, `--eval3`; 44 markets pooled)

| config | 09-16 | 09-17 | pooled $/mkt (t) | win | contracts | worst mkt |
|---|---|---|---|---|---|---|
| depth ≥ 2000 only | +2.98 | +2.96 | **+2.97 (6.2)** | 86% | 44,643 | −5.0 |
| depth ≥ 1500 only | +2.68 | +3.18 | +2.90 (5.6) | 82% | 50,154 | −5.1 |
| depth ≥ 1000 only | +2.79 | +2.28 | +2.57 (4.8) | 77% | 59,426 | −4.0 |
| depth ≥ 750 only | +2.99 | +1.87 | +2.51 (5.0) | 77% | 65,415 | −3.4 |
| depth ≥ 500 only | +2.58 | +1.41 | +2.08 (3.8) | 77% | 73,122 | −7.8 |
| depth ≥ 300 only | +1.45 | +1.43 | +1.44 (2.9) | 70% | 80,831 | |
| depth ≥ 200 only | +1.03 | +0.95 | +1.00 (1.6) | 61% | 87,099 | |
| A3 = age 1 s + depth 300 | +0.50 | +1.16 | +0.78 (1.2) | 57% | 60,280 | |
| depth 1000 + imbalance 0.33 | +2.89 | +2.34 | +2.65 (4.7) | 75% | 35,041 | −8.8 |
| depth 1000 + cap 40 size skew | +5.32 | +4.99 | +5.18 (5.1) | 84% | 103,857 | −12.6 |
| depth 1000, size 50 / cap 50 | +6.42 | +5.85 | **+6.17 (5.1)** | 84% | 136,159 | −13.3 |
| depth 500, size 50 / cap 50 | +6.49 | +3.44 | +5.17 (4.1) | 75% | 167,778 | −12.9 |
| A3 + offset 1 tick / size 10 / carry / age 2 s | ≈ 0 | | | | | |

- **The level-age gate was a mistake; the depth gate alone is the edge.** Removing the age condition from A3 nearly doubles it (+0.78 → +1.44), and the gate is monotone in the threshold up to ~1,500–2,000 contracts, positive on both days at every threshold ≥ 300, with 77–86% winning markets and the worst market at −$5. It is one parameter, so the selection bias from ~37 configs on 44 markets is limited, but the threshold itself (1,000 vs 2,000) is within noise.
- Mechanism: the gate is a presence veto, so we only rest on thick levels and leave as a level thins. At depth 1000 on 09-17: 2,205 fills, 40% by price priority (sweeps through a thick level), 29% improves, the rest queue advancement; fill markout +0.21¢/contract at 30 s vs −0.05¢ for the baseline. A sweep that clears 1,000+ contracts is rarer and, when it happens, we are far back and lose little; a sweep through a 200-lot level is the informed trade.
- Size scales: size 50 / cap 50 with depth 1000 gives +$6.2/market (t 5.1), i.e. ~$600/day at 96 markets on ~$170 of collateral in use — but the sim has no market impact above ~100-lot joins and the pessimistic-queue check below matters more at these depths.
- Imbalance on top of the depth gate halves volume for no gain; size skew at cap 40 adds ~+2.6/market on top of depth 1000 (unlike at cap 40 without the gate, where it lost).

### Does the depth gate survive the queue model? (`--eval4`, pessimistic = no advancement from cancels ahead)

| config | prorata $/mkt (t) | pessimistic $/mkt (t) | orders filled: prorata / pessimistic |
|---|---|---|---|
| baseline 20/20 | −1.36 (−1.8) | −3.78 (−5.6) | 33% / 16% |
| depth ≥ 500 | +2.08 (3.8) | +0.08 (0.1) | — / 7% |
| depth ≥ 1000 | +2.57 (4.8) | +0.40 (0.5) | — / 5% |
| depth ≥ 1500 | +2.90 (5.6) | −0.03 (0.0) | — / 4% |
| depth 1000, size 50 | +6.17 (5.1) | +1.47 (0.9) | — / 5% |

Under the pessimistic queue the depth gate is ~zero: joining behind 1,000 contracts only pays if the queue in front of us actually drains. So the whole edge rests on the queue-advancement model, which has never been measured directly. The indirect evidence points the right way: live orders (994, 09-17 04:13–04:45) filled **48%** of the time with time-to-first-fill p50 0.71 s, vs 33% / 0.85 s for the sim's pro-rata model and 16% / 0.60 s pessimistic on the same day under the corrected model — live advances at least as fast as pro-rata, so pessimistic is a floor and pro-rata is not optimistic. But the depth-gated configs are precisely the ones that sit deep in the queue, where the model matters most, and 48% was measured for a chasing quoter that mostly sat at thin, fresh levels.

Decision: the depth gate is the candidate rule, and the queue-advancement rate at thick levels is the number to measure next — from the paper quoter running `-min-depth 1000` (its fill rate vs the sim's on the same markets) and, in a bounded live test, from `GET /portfolio/orders/{id}/queue_position` polled on every resting order. Pro-rata at +2.6/market and pessimistic at +0.4 bracket the truth; live at size 5–20 with the gate cannot lose much either way (worst market −$5 at size 20).

## 2026-09-17 — paper executor vs the corrected sim (`paper_vs_sim.py`)

Paper (price priority + tapered tick, live config size 20 / cap 20 / $100) restarted 07:15 UTC; Kalshi's maintenance window left no markets until 09:00 UTC, and a halt at 10:08 (below) stopped it after five markets. On those five, against the sim's baseline on the same tape:

| | paper | sim |
|---|---|---|
| P&L, 5 markets | −$24.0 | −$32.1 |
| fills | 1,101 | 1,163 |
| contracts | 10,269 | 10,194 |
| sweep (price-priority) fills | 18–24% | 12–20% |

Per market within a few dollars of each other (corr 0.40 on n = 5). After the halt fix, 11 markets by 16:00 UTC: paper −$16.8 vs sim −$28.1, fills 2,285 vs 2,489, contracts 24,502 vs 25,637, per-market corr **0.81**, sweep share paper 18–49% vs sim 8–43% (paper consistently a few points higher). The paper executor now reproduces the corrected sim's volume, sweep share and loss; the old paper on the same day had traded 4x the sim's volume at +$289 where the sim said −$38. Both are still losing at the live baseline configuration — as the sim says they should.

**Bug found by the corrected paper (would have hit live):** halt `position 28.10 beyond limit`. Sequence: YES 20 pending-cancel; a trade that beat the cancel at the engine fills it (reported after the cancel ack); the strategy, seeing the stale position, places a new YES 20 which is swept 8 ms later → +28.1 vs cap 20. Live has the same race: Kalshi's cancel response carries `reduced_by`, and the fill channel reports the pre-cancel fill ~7 ms later. Fix (`8b3654d`): `Cancel` returns `reduced_by`; a cancelled order whose remainder exceeds `reduced_by` stays pending-cancel until those fills land, so the side cannot be re-quoted on a stale position; the paper executor waits out `FeedLag` before answering a cancel so its `reduced_by` is honest.

### Depth 1000 — size sweep and time of day (`--sizes`; 81 markets = 09-16 17:00 → 09-17 16:00 UTC, one continuous stretch)

| size / cap | pro-rata $/mkt (t) | win | pessimistic $/mkt | worst mkt (pro-rata) |
|---|---|---|---|---|
| 5 | +0.50 (3.7) | 72% | +0.01 | −2.9 |
| 10 | +0.92 (3.7) | 72% | −0.00 | −5.1 |
| 20 | +1.65 (3.4) | 67% | −0.29 | −13.7 |
| 50 | +3.90 (3.5) | 72% | +0.07 | −22.3 |
| 100 | +8.98 (4.2) | 74% | −0.89 | −63.7 |
| 200, unlimited capital | +13.69 (3.7) | 72% | +1.22 | −74.9 |
| 500, unlimited capital | +23.47 (2.5) | 64% | −2.96 | −281.9 |
| 50 / cap 100 | +7.33 (2.9) | 72% | +1.03 | −62.5 |
| 100 / cap 200 | +17.12 (3.6) | 75% | +1.34 | −120.5 |

Pro-rata: linear at ~$0.085/market per contract of quote size through 200, sub-linear by 500; the t-stat is size-independent (P&L and noise scale together); the worst market grows faster than the mean. Pessimistic: ≈ 0 at every size. Cap 2× size nearly doubles the edge at the same quote size (and the worst market). No market impact is modelled — above ~100 lots the numbers are optimistic regardless.

Hourly: the whole drag is one 3-hour stretch, 09:00–12:00 UTC on 09-17 (right after Kalshi's maintenance window, market volume half of normal): −$37 over 12 markets (−3.09/mkt), against +$2.29/mkt over the other 44 markets that day and 67–88% winners in every other 4-hour block. The baseline lost there too (−4.87/mkt vs −1.82 elsewhere), so it is a bad stretch for the strategy, not the gate. One occurrence — watch the next post-maintenance hours before making it a rule.

### Paper under `-min-depth 1000` vs the sim (from 16:22 UTC, `paper_vs_sim --config "depth 1000 only"`)

First 6 markets (12:30–13:45 ET): paper +$17.0 vs sim +$5.5; fills 590 vs 542; contracts 7,932 vs 7,907; sweep share 12–34% vs 1–30%. Volume matches to 1% — the gate engages on live books the way the sim says. The P&L gap is one market (13:45: paper +3.6 vs sim −8.1; the market ran to 5¢ and paper's endgame flatten covered 14 lots there) — n = 6, per-market SD ≈ $4. Paper's fill count is pro-rata by construction, so this confirms engagement and sweep share, not queue advancement.

## 2026-09-17 18:46–19:45 UTC — bounded live test of the depth gate (size 10 / cap 10 / min depth 1000)

Stopped after 4 markets: −$0.43, −$1.86, −$4.31, −$3.10 = **−$9.70** (exchange balance $56.07 → $46.48). 237 maker fills / ~2,100 contracts, 61 post-only-cross rejections, 0 errors, no halt; every market flattened at the stop. Tape: `data_aws/quoter/live/raw/2026-09-17/{18,19}.jsonl.gz` (with `queue_pos` events).

What the run was for — the queue-advancement rate behind thick levels — is answered, and not in the gate's favour:

- **Exchange queue positions** (`GET /portfolio/orders/queue_positions`, 1 Hz): orders join behind a median 3,800 contracts; the quantity ahead shrinks at ~770 contracts/s (trades + cancels), i.e. the *pessimistic* sim's rate (~850/s), not pro-rata's (~2,200/s).
- **Fills never come from the queue draining.** For 99 join fills with a reading ≤ 0.4 s before the fill: median 1,800 contracts still ahead, 94% > 500, 1% < 100. The fills are trades through the level (price priority), which is the informed flow the gate was meant to avoid.
- **Markouts** (first 3 markets, 128 fills / 1,126 contracts): half-spread +0.33¢, markout −0.18¢ @1 s, −0.38¢ @10 s, net −0.09¢/contract @30 s; full-sweep fills 29% of contracts at −1.74¢, the rest +0.58¢. Same shape as the baseline live run of 09-17 04:13.
- Order lifetime p50 0.32 s: the touch size oscillates around the 1,000 threshold and the touch moves, so the presence veto churns the order and we are perpetually the newest order at the level.
- 161 of 162 fills were joins; 1 improve.

Conclusion: at REST latency on KXBTC15M, a passive touch-joiner's fills are sweeps whatever the depth gate does; the queue in front of us does not turn over within an order's life. The pro-rata queue model — which every positive sim number depended on — is wrong for thick levels on this venue, and the honest sim estimate for the depth gate is the pessimistic one (≈ $0 to slightly negative). The remaining levers are front-of-queue placement (improves earned +1.81¢ live; the sim shows an edge only at ~2 ms placement, i.e. FIX/Premier) or a different contract/venue where the queue turns over.

## 2026-09-17 — option 1 (latency): the gap by component, and whether anticipation can close it

**Latency sweep under the corrected model** (`--latency2`, 95 markets, size 20 / cap 20, $/market, t):

| event → our order in the engine | config | pooled | 09-16 / 09-17 |
|---|---|---|---|
| 15 ms | REST today 9/5, feed lag 6 | −2.06 (−4.5) | −0.42 / −2.65 |
| 11 ms | FIX-like 5/3 | −1.76 (−3.4) | |
| 9 ms | 3/3 | −1.29 (−2.9) | |
| 8 ms | 2/2 | −1.23…−1.51 | +0.5 / −1.9 |
| 7 ms | 1/1/1 | −0.78 (−1.6) | +0.59 / −1.27 |
| 9 ms | REST 9/5 with feed lag 0 (hypothetical) | −0.66 (−1.5) | |
| **2 ms** | **2/2 with feed lag 0 (hypothetical)** | **+2.93 (7.1), 80% win** | +4.03 / +2.54 |
| 15 / 8 ms | pessimistic queue | −4.48 / −3.59 | |

The "2 ms break-even" of the old frame was measured from the moment we *see* an event; with the physical 6 ms feed lag no order-entry latency makes the touch-joiner positive — the whole 15 → 7 ms range is worth ~$1.3/market and stays negative. The edge (+$3/market, t 7) exists only at ~2 ms *total*, i.e. if we could act before the WS delivers the event.

Components of the 15 ms (measured): Kalshi engine → our WS receipt 6–7 ms (Kalshi-side; network 0.3); our decode/decision/Go scheduling ~1 (p99 7.5); RSA-PSS signing 1.7 ms on the c7g (inside the 9.0 ms probe number; removable — the signature covers `ts+method+path` only, so it can be pre-computed); JSON/HTTP/in-AZ network ~0.5; Kalshi REST gateway → shard engine ~7 (cancel is 5.2, so ~4 is order validation/collateral). We control ~3–4 ms; FIX would attack the ~7 ms gateway (unmeasurable without Premier). Neither reaches the regime that pays.

**Anticipating instead of reading** (`level_lead.py`, 09-16, 8,044 Coinbase moves ≥ $2/1 s): only 51% of moves produce a new, better touch on the favoured side within 2 s; when one forms, 13% form within 16 ms of our spot receipt, p50 308 ms, p75 844 ms. So a bid sent on the spot trigger would be first at the vacated level in ~87% of formations — *if* it could rest there. It can't: the ask it needs to replace is still occupied when the order arrives. Sim (`--sigimp`, 09-16, post-only at the old ask on the trigger, replacing the resting join, 15 ms tape latency): **85% of the 9,150 signal orders are rejected post-only-cross**, the rest rest as lone improves; P&L −2.31/market vs −0.42 baseline at every hold (0.5/2/5 s), threshold ($2/3/5), with or without the join gate, at FIX-like latency (−2.01), and at size 50 (−4.36). The rule gives up queue position on the good side for a ticket that mostly bounces; re-firing until accepted converges on the existing improve-on-vacate rule with a few ms shaved, which the sweep values at ≈ $0.5/market.

Conclusion: option 1 is closed on KXBTC15M. The binding constraint is the 6 ms feed lag, which no order-entry work or Coinbase-triggered anticipation gets around; the +$3/market front-of-queue regime needs a way to see or predict the engine's events ~4 ms sooner than the public WS, which we do not have.

## 2026-09-17 — is the next touch move predictable, and can that buy queue priority? (`vacate.py`)

Target: per side of the active market, sampled every 100 ms, does the opposing touch vacate within H ms. 52 features (Kalshi top-two sizes both sides, touch ages, removals/trades at the opposing touch, spot returns 50 ms–5 s, Coinbase imbalance/microprice, signed flow on 9 venues, cross-venue gaps, BRTI, moneyness, vol). Walk-forward: trained on 09-16 (267k rows), tested on 09-17 (747k rows):

| horizon | base rate | AUC | precision @ top 1% / 5% / 10% | recall @10% | lead p50 among hits |
|---|---|---|---|---|---|
| 50 ms | 2.5% | 0.894 | 38 / 24 / 17% | 67% | 18 ms |
| 100 ms | 4.4% | 0.876 | 52 / 36 / 26% | 60% | 35 ms |
| 250 ms | 9.2% | 0.836 | 69 / 54 / 43% | 47% | 76 ms |
| 500 ms | 15.7% | 0.800 | 80 / 67 / 57% | 36% | 121 ms |
| 1 s | 25.4% | 0.766 | 87 / 78 / 70% | 28% | 178 ms |

The move is predictable — but by the state of the level, not by spot: `opp_size` alone has AUC 0.82 (the model 0.84); removals at the touch over 500 ms 0.68, level age 0.63; the best spot/perp feature is 0.57. It reads "the ask is thin, old and being eaten", not "the price is about to go up".

**Why the prediction cannot be monetised as queue priority** (`/tmp/form_lag.py`, all touch vacates on the active market):

| | 09-16 (23,109 vacates) | 09-17 (63,177) |
|---|---|---|
| a bid forms at the vacated price within 2 s | 67% | 67% |
| formation lag p25 / p50 / p75 | 0 / 2 / 8 ms | 0 / 1 / 7 ms |
| formed within 5 ms | 65% | 67% |
| formed within 16 ms (our WS reaction) | 82% | 85% |

A quarter of the new levels appear at the same tape timestamp as the vacate and half within 2 ms: the bid is placed by the party that pulled the ask, as one action (a maker rolling its quote). Nothing can be ahead of the actor who defines the event; a post-only cannot rest there beforehand (it crosses), and taking the ask on the prediction is a 1-tick trade against a 0.6–1.75¢ fee. The 15–18% of formations slower than 16 ms are the improves the existing rule already captures. This is the same fact as "the queue never drains" from the other side: the book is a few two-sided quoters rolling their quotes; a REST participant is either behind them or swept with them.

## 2026-09-18 — where next: market survey, and the hindsight bound on a learned policy

### Market survey (`survey.py`, 09-17, 568 markets)

| series | markets | spread ¢ | touch size | touch life | refill ≤2 ms / ≤16 ms | contracts/h | sweep % | mo30 ¢ (maker, all touch trades) |
|---|---|---|---|---|---|---|---|---|
| KXBTC15M | 88 | 0.74 | 2,944 | 8 ms | **23% / 41%** | 10.4M | 23% | **+0.01** |
| KXETH15M | 88 | 0.92 | 84 | 19 ms | **3% / 25%** | 421k | 44% | **+0.38** |
| KXBTCD (hourly thresholds) | 392 | 1.36 | 1,254 | 212 ms | 2% / 24% | 30k | 29% | +0.10 |

`refill ≤2 ms` = share of vacated touch levels re-created within 2 ms (the vacator rolling its quote). KXBTC15M is the only series with that signature, and its maker markout over *all* touch trades is zero: the average maker at the average trade earns nothing before queue position. KXETH15M: no rolling quoters, a 35× shorter queue, and +0.38¢/contract for makers net of a 44% sweep share; per market mo30 is positive in 15 of the top 20 (median +0.55¢, worst −0.18¢). KXBTCD are hourly markets (500–800k contracts/h, touch ~900, markouts mixed) — a slower BTC15M, not a patient maker's market.

### Hindsight bound on a learned placement policy (`veto_gen.py`, `sim --veto`, 09-17, 56 markets, size 20)

Presence-only action ("be on this side or not"), the sim's fill model as the environment. Oracle = perfect foresight of every sweep-through trade; learned = the vacate classifier (train 09-16, AUC 0.835 on 09-17) vetoing the resting side for 250 ms when p > threshold.

| policy | $/mkt (t) | contracts | fill mo30 ¢ | sweep fills |
|---|---|---|---|---|
| baseline | −2.24 (−4.9) | 251,602 | −0.05 | 6,408 |
| oracle, 50 ms warning | +2.61 (6.2) | 168,132 | +0.17 | 1,668 |
| oracle, 250 ms warning | +3.59 (8.4) | 145,076 | +0.25 | 1,280 |
| oracle, 1 s warning | +5.35 (12.2) | 102,740 | +0.49 | 529 |
| oracle, adverse sweeps only, 250 ms | +3.28 (8.1) | 179,010 | +0.19 | 2,907 |
| learned p > 0.3 (8.6% of time vetoed) | −0.57 (−1.3) | 180,096 | +0.01 | 3,556 |
| learned p > 0.5 (3.5%) | −1.30 (−2.8) | 218,339 | −0.03 | 4,574 |
| learned p > 0.7 (0.9%) | −1.93 (−4.3) | 240,447 | −0.06 | 5,622 |

The bound is real: a clairvoyant presence policy earns +$2.6–5.4/market at size 20 on the same book where everything else loses — the whole loss is the sweeps, and dodging them with as little as 50 ms warning flips the sign. The learned policy recovers about a third of the gap at p > 0.3 (−2.24 → −0.57; sweep fills 6,408 → 3,556; markout −0.05 → +0.01) and is monotone in coverage, but does not cross zero: at AUC 0.835 the false positives (pulling from levels that survive, losing the +0.58¢ partials) cost about what the dodged sweeps save. To be worth deploying on BTC the classifier would need roughly AUC 0.9+ at the same horizon, or a cheaper action than pulling. On ETH the same machinery starts from a positive baseline (below).

## 2026-09-18 — KXETH15M under the corrected model, and where our fills actually come from

**ETH is worse than BTC for us, despite a better market.** 113 markets (09-16/17), corrected model, size 20:

| config | $/mkt (t) | win | contracts/mkt | fill mo30 |
|---|---|---|---|---|
| touch joiner (greeks cap, signal cancel) | −5.15 (−15.3) | 7% | 1,856 | −0.27¢ |
| no gates | −7.90 (−15.6) | 1% | 2,422 | −0.32¢ |
| depth ≥ 50 / 100 / 200 | ≈ −2.2 (−6) | ~30% | 650–950 | −0.10…−0.22¢ |
| size 5 / size 50 | −1.28 / −10.58 | 8% / 7% | 605 / 3,337 | −0.21 / −0.28¢ |
| pessimistic queue | −4.67 (−14.1) | 7% | 1,599 | −0.30¢ |

Settlement uses `ETHUSD_RTI`; the price grid is the same tapered grid as BTC (checked against `price_ranges`).

**Maker markout by age of the touch price when the trade arrived** (`survey.py`, 09-17, all touch trades — not just ours):

| age of touch | class | ETH share / mo30 | BTC share / mo30 |
|---|---|---|---|
| 0–5 ms | sweep | 41% / +0.27¢ | 20% / −0.28¢ |
| 0–5 ms | partial | 16% / +0.86¢ | 9% / +0.01¢ |
| 5–16 ms | partial | 2% / −0.80¢ | 2% / −0.92¢ |
| 16–50 ms | partial | 2% / +0.52¢ | 3% / −0.65¢ |
| 50–200 ms | partial | 4% / +0.19¢ | 7% / −0.06¢ |
| 200–1000 ms | partial | 9% / +0.46¢ | 20% / +0.13¢ |
| ≥ 1 s | partial | 20% / +0.20¢ | 37% / +0.22¢ |

The toxic window is **5–50 ms after a price becomes the touch**, on both books — exactly where a WS-driven quoter lives (we see a level at +6 ms, land at +15). Trades on prices established ≥ 200 ms are benign everywhere and are 29% of ETH volume, 57% of BTC volume; sweeps rarely reach them.

**Our own fills (sim, ETH baseline, by kind / class):** join-partial 31% at −0.01¢, improve-sweep 30% at −0.22¢, join-sweep 22% at −0.87¢, improve-partial 17% at −0.04¢ — 52% of our volume is sweeps vs 44% market-wide, and our sweep fills are much worse than the market's because price priority fills us at levels a sweep passes *through*, while the market-wide figure counts the maker at the printing level. The fills that pay are rare for us: join-partial on a 200 ms–1 s touch **+0.77¢ (3% of contracts)**, on a 50–200 ms touch **+1.02¢ (1%)**. Improve-only is the extreme: 97% of its fills are sweeps (−0.27¢) — a lone improver is only hit by someone sweeping through it.

Diagnostic variants (09-17): ETH join-only −3.42, improve-only −1.57, pre-position 1 tick −0.45, persistence −6.65; BTC join-only −2.12, improve-only −0.27, pre-position −2.45, persistence −3.64. Nothing positive, but the ranking says volume is the enemy: every variant that trades less loses less.

Open question being tested (`sim --old`): quote **only** prices that have been the touch ≥ 50/200/500/1000 ms and hold while they remain the touch. Every fill would then be in the +0.2…+1.0¢ class, but at an old touch we join the back of a long queue — whether any volume survives is the test.
