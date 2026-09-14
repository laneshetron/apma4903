# Phase A findings: is market making on Kalshi viable?

Date: 2026-09-14. Data: Kalshi public REST history, markets settled in the 24h
to 2026-09-14 03:52 UTC. Full tables: `phase_a.md`; method:
`python/kalshi_data/research/phase_a.py`.

## Summary

|                                  | KXBTC15M            | KXETH15M        | KXBTCD (hourly)            |
|----------------------------------|---------------------|-----------------|----------------------------|
| Volume / day                     | 174M contracts      | 10.6M           | 32M (522 of 4,404 strikes) |
| Typical spread                   | 1c (0.74c vol-wtd)  | 1c              | 1c                         |
| Median trade                     | 9 contracts         | 10              | 20                         |
| Maker markout @10s / 30s / 60s   | +0.24 / +0.30 / +0.36c | +0.28 / +0.17 / +0.51c | +0.32 / -0.08 / -0.39c |
| Maker markout to settlement      | +0.30c              | +0.17c          | +1.19c (noisy)             |
| Implied adverse selection @60s   | ~0.0c               | ~0.0c           | ~0.9c                      |
| Maker fee                        | none (`quadratic`)  | none            | none                       |
| Sample                           | 321k trades, 19.8M contracts | 53k, 1.4M | 16k, 1.3M                |

Markout = P&L per contract for the passive side of a trade, unwound at the
reference price h seconds later (VWAP of trades in [t+h, t+h+5s]). Because
the reference sits near the mid, the markout already nets the half-spread
captured at the touch; a market with zero information in its flow shows
~+half-spread.

## Findings

1. **KXBTC15M flow is close to uninformed at short horizons.** A maker filled
   at the touch keeps ~+0.3c/contract at 10-60s, i.e. essentially the whole
   half-spread. With 174M contracts/day and no maker fee, capturing 0.1% of
   flow is ~$500/day gross; 1% is ~$5k/day. Scale is the whole game; the
   per-contract prize is tiny.
2. **KXETH15M** behaves similarly but is 16x smaller and noisier per market.
3. **KXBTCD (hourly strikes)** shows negative markouts beyond 10s: fewer,
   more informed participants. Not a candidate.
4. **Do not quote the last ~2 minutes.** Markouts at 0-1 min to expiry are
   ~0 or negative, prices sit near 0/1 with sub-penny ticks, and gamma is
   extreme. That is 38% of KXBTC15M volume we would forgo.
5. Time of day matters little for BTC (volume is spread across the day);
   ETH and BTCD concentrate in 22:00-03:00 UTC.

## What Phase A cannot answer (=> Phase B)

- **Fill-conditioned adverse selection.** Markouts above average over all
  trades. A resting order is filled disproportionately when its whole level
  is swept, which is when the taker is most likely informed. The number that
  matters is the markout of the trades that *would have filled us*, which
  needs order-book depth and queue position.
- **True mid.** The trade-VWAP reference carries +/-0.1c of bid-ask-bounce
  noise. Our own order-book recording provides real mids.
- **Achievable flow share.** Best levels carry thousands of contracts (e.g.
  3,700 at the best bid in one live check). Positive markouts mean the
  incumbents are profitable, so the queue is competitive. Share depends on
  queue position, quote refresh speed and how often levels turn over.
- **Inventory / hedging.** Settlement markouts are ~+0.3c on average but the
  per-market distribution is dominated by the binary outcome. A quoter needs
  either inventory skewing or a BTC hedge; neither is costed here.
- **Exchange rules not in the API**: per-market position limits and the
  market-maker program terms.

## Verdict

Not hopeless; plausibly viable; decided by Phase B. Rough odds: ~50-60% that
Phase B shows a positive, tradeable edge for a well-positioned quoter on
KXBTC15M; ~30% that a first simple implementation from a home connection
captures enough of it to matter. The gap is execution, not economics.

What would move the odds up: level-sweep markouts >= +0.1c at 30s; queue
turnover fast enough that a fresh order reaches the front within a market's
life. Down: level-sweep markouts <= -0.3c; or queues so deep that a new order
spends most of the 15 minutes at the back.

## Phase B plan

Data: the collector is recording KXBTC15M, KXETH15M and KXBTCD order books
and trades (`data/raw/`), validated live against REST. Target 3-5 days.

1. **Fair value feed.** Record BTC/USD spot (Coinbase or Binance public
   WebSocket) alongside, with local receive timestamps, so every Kalshi
   event can be paired with the contemporaneous spot price.
2. **Sweep-conditioned markouts.** From the book replay, classify each trade
   by how much of the touch it consumed (partial / full level / multi-level)
   and compute markouts against the true mid at 1s, 10s, 30s, 60s. The
   full-level bucket is the fill-conditioned adverse selection estimate.
3. **Queue dynamics.** Per market: depth at the touch over time, level
   lifetime, time for a new order at the back to reach the front (from
   cancels + fills), how often the spread is 1 tick vs wider.
4. **Fair-value model.** Binary option price from spot, strike, time to
   expiry and short-horizon realized vol; measure how far Kalshi's mid lags
   or leads fair value after spot moves. Tells us whether speed or pricing
   is the edge.
5. **Simulation.** Replay with a simple quoter (quote +/-k around fair value,
   size s, skew by inventory, no quoting in last 2 minutes), fills modelled
   by queue position against recorded trades and cancels. Output: P&L per
   contract, fill share of flow, inventory distribution, drawdown.

Go/no-go after step 5, before any order-placement code.
