# Phase B step 4: quoter simulation — first results (2026-09-14, KXBTC15M)

Data: 46 markets (~11.5h), 45M records. Model: `python/kalshi_data/research/sim.py`.
Tables: `sim_2026-09-14.md`, `sim_2026-09-14_sweep.md`.

## Base configs (100 contracts/side, max position 500)

| config | P&L | realized | unrealized | t (46 mkts) | c/contract | fill share |
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
- Roughly half the P&L is realized round-trip spread; the other half is a
  consistently positive inventory mark, i.e. accumulating against noise flow
  is itself a mean-reversion trade. That half is the more fragile.
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
