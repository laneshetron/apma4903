# Monte Carlo survivability, 20,000 paths x 365 days, block-bootstrapped from 10 real days

Capital $10,000; leverage sets participation so peak inventory = capital x leverage. Maintenance margin 1.25% of gross notional; maker fee 1.50 bp on filled notional. No exit slippage or funding charged.

Source days: P&L per day at 1% participation ranges $-6,110 to $8,261 (median $442).

`ruin` is literal liquidation (equity <= maintenance margin). On a perp that is a very low bar -- at 1.25% maintenance you are only dead after losing ~99% -- so `P(-50%)` is the more useful column.

| leverage | participation | peak inv | **ruin %** | **P(-50%)** | P(lose) | median /yr | p5 | p95 | median maxDD | p99 maxDD |
|---|---|---|---|---|---|---|---|---|---|---|
| 1x | 0.0057% | $10,000 | **0.0%** | **0.0%** | 0.0% | +19% | +13% | +26% | 1% | 3% |
| 2x | 0.0114% | $20,000 | **0.0%** | **0.0%** | 0.0% | +38% | +26% | +51% | 2% | 5% |
| 3x | 0.0172% | $30,000 | **0.0%** | **0.0%** | 0.0% | +57% | +38% | +77% | 3% | 7% |
| 5x | 0.0286% | $50,000 | **0.0%** | **0.0%** | 0.0% | +96% | +65% | +127% | 5% | 12% |
| 8x | 0.0458% | $80,000 | **0.0%** | **0.0%** | 0.0% | +154% | +103% | +203% | 7% | 17% |
| 10x | 0.0572% | $100,000 | **0.0%** | **0.0%** | 0.0% | +191% | +128% | +256% | 8% | 21% |
