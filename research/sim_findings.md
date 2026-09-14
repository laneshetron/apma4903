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
