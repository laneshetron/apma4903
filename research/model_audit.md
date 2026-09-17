# Model audit — 2026-09-17

Scope: `python/kalshi_data/research/sim.py` (the simulator every P&L estimate came from), the
paper executor that mirrors it, and the strategy rules both encode. Checked against Kalshi's
docs, the API, the collector tape and 598 live fills / 1,023 live orders from 2026-09-17.

## Part 1 — Correctness

Ranked by how much each one moved (or would move) the P&L estimate.

### 1. Fills only came from trades at our own price (fixed today: `price_priority`)
A taker who clears our level and keeps trading at the next level would, under price-time
priority (confirmed: Kalshi documents queue position as "price-time priority"), have taken our
order first. The sim credited us with surviving every multi-level sweep — 33% of volume and the
informed class. With the fix the corrected model reproduces the live loss on the two live markets
(−$14.5 vs −$15.5) and turns every 9 ms configuration from positive to ~zero/negative. **All
prior estimates are void; only the 2 ms rows remain positive.**

### 2. Placement and cancel latencies are 6 ms too optimistic on the AWS tape
Tape time = engine time + ~6 ms (measured engine `ts_ms` → receipt). A decision made at tape
time `rx` reaches the engine `place_lat` later in *real* time, i.e. at tape time
`rx + place_lat + 6 ms`. The AWS-tape configs use 9/5 ms directly; the honest tape-time values
are **15 / 11 ms** (the spot-triggered cancel row was already converted: 11). The laptop-tape
"MEASURED" set had this right. Under the corrected fill model latency is the dominant variable,
so this matters: rerun with 15/11/11.

### 3. Tick size is wrong in the tails
KXBTC15M uses `tapered_deci_cent`: **0.1¢ steps below 10¢ and above 90¢**, 1¢ between. The sim
(and the Go quoter) use a fixed 1¢ tick, so in the tails "improve by one tick" jumps ten levels,
`spread > TICK` mis-fires, and live orders at off-grid prices are rejected (`invalid_order`).
The 23:30 live market traded at 96–98¢ under this bug. Fix: read `price_ranges` per market and
derive the tick at the quoted price; quote in the tails separately or not at all.

### 4. No settlement
Positions at the stop were marked at mid, never resolved. Live carried +80 into a NO settlement
(−$44). `flatten_at_stop` now removes the exposure in both live and sim, but the sim should
still resolve markets (BRTI 60 s average vs strike is on the tape) so that carry policies and the
true cost of flattening are measured, not assumed.

### 5. Queue advancement model is unmeasured
`prorata` assumes cancels ahead of us are spread evenly through the queue; `pessimistic` assumes
none. Live orders filled after a median 44% of the level ahead had traded — advancement is real,
between the two. Kalshi exposes `GET /portfolio/orders/{id}/queue_position` (contracts ahead,
price-time). **Poll it for every live order** and fit the advancement rate directly instead of
inferring it.

### 6. Young-order toxicity is a live-only quantity
Fills on orders < 0.5 s old marked out −0.4 to −0.7¢ live and +1.0¢ in paper on the same
markets. Part is fixed by (1) (deeper trades now reach young orders at fresh levels); the
residual — taker demand beyond displayed liquidity that never rests and never prints — is
invisible to any tape. Calibrate a per-fill toxicity adjustment from live fills by order age /
level age and apply it in the sim.

### 7. Smaller items
- Activation sets `ahead` from the level size *before* a delta at our price but *after* for other
  deltas (two code paths); harmless but inconsistent. Use "after", minus nothing.
- Taker fee: Kalshi rounds up to the cent per order; the sim uses the exact formula. Negligible
  above ~10 lots.
- `flatten_at_stop` / `flatten_above` take at the touch regardless of depth; at size 20 fine,
  at 100+ it walks the book. Model depth-aware unwinds.
- Latencies are point estimates (p50); p90 is 1.3–2× higher. Sample from the measured
  distributions.
- No market impact and no reaction of other participants to our orders. The impact study said
  joins ≤ 100 lots are invisible to the book; anything larger is unmodelled.
- The paper executor shares (1), (3), (5), (6); it must not be used as evidence for a rule the
  tape cannot see.

## Part 2 — Where the profit can be

Ordered by expected value per unit of evidence, all now evaluable under the corrected model.

### A. Stop chasing (quote persistence, join-age / depth gates)
The clearest signal in the live data: fill markouts by order age at fill — < 0.25 s: −0.37¢,
0.25–0.5 s: −0.74¢, 0.5–2 s: ≈ 0, 2–5 s: **+0.44¢**. Median live order lifetime was 0.41 s; the
quoter was perpetually the newest order at a freshly formed level. Rules: don't join a level
younger than ~1 s or thinner than N; reprice only when the touch moves ≥ 2 ticks away or the
order is off-market; minimum resting time. Directly removes the fills that lose money.

### B. Improve inside wide spreads
Live improving fills: +1.81¢ on 548 contracts (n = 35). Now testable in the sim: with price
priority, any trade at the old touch after we improve is a fill for us. The 2¢-spread state
occurs ~15% of the time; the front-of-queue economics there are the best in the data.

### C. Pre-position one tick behind the touch
Be first at a level by resting there before it becomes the touch, rather than racing to join it.
Front-of-queue partial fills earn +0.27¢ in both live and paper; the corrected model can evaluate
it (real historical levels), and it makes placement latency irrelevant.

### D. Inventory by size skew (A–S), cap 40
Already positive in the (old) model: +75% mean for +25% SD vs cap 20. Re-test under the corrected
model; keep flatten-at-stop.

### E. Better gates
Extend the join gate's state (imbalance, microprice, ttx, queue) with level age, level depth and
"last full sweep" recency — the features that separate the live −0.97¢ full-sweep fills from
the +0.27¢ partials.

### F. Latency
FIX (Premier tier) might take 9 → 5 ms. Under the corrected model the value of latency is
large but only realised at ≤ 2 ms placement, which REST cannot reach. Pursue only if A–C don't
produce a positive edge.

### G. Not worth it (evidence so far)
Presence vetoes on spot/α signals; stale-feed vetoes; composite spot signals; taking to flatten
intra-market; carrying inventory; KXBTCD; larger size before the edge is positive.

## Part 3 — What to do before any more live money

1. Fix (2) and (3) in the sim; add settlement (4).
2. Rerun the whole configuration set under `price_priority` with 15/11/11 latencies.
3. Test A, B, C, D on both AWS days.
4. Add queue-position polling and level-age/depth logging to the live quoter (5, 6).
5. If a configuration is positive on both days under the corrected model, run it live at 5 lots
   with the instrumentation on, for ~30 markets, and compare fill-by-fill.
