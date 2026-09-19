# Settlement-window study, KXETH15M 2026-09-16: 24 markets settled, 3,112 (market, second) rows

Model calibration in the last 60 s (P(YES) bin -> realized):

| p bin | n | realized |
|---|---|---|
| 0.0 | 198 | 0.00 |
| 0.3 | 3 | 1.00 |
| 0.4 | 4 | 1.00 |
| 0.6 | 1 | 1.00 |
| 0.8 | 2 | 1.00 |
| 0.9 | 3 | 1.00 |
| 1.0 | 170 | 1.00 |

Taking rule, one contract per (market, second) where the edge exceeds the threshold (¢ per contract, after taker fee):

| window | threshold | trades | markets | edge/ct ¢ | P&L $ | win % |
|---|---|---|---|---|---|---|
| T-60..T-30 s | 0.02 | 21 | 3 | +8.73 | +1.8 | 90% |
| T-60..T-30 s | 0.05 | 5 | 1 | +13.06 | +0.7 | 60% |
| T-60..T-30 s | 0.10 | 3 | 1 | -3.10 | -0.1 | 33% |
| T-60..T-30 s | 0.20 | 1 | 1 | +48.25 | +0.5 | 100% |
| T-120..T-60 s | 0.02 | 447 | 10 | -6.91 | -30.9 | 82% |
| T-120..T-60 s | 0.05 | 283 | 8 | -5.03 | -14.2 | 81% |
| T-120..T-60 s | 0.10 | 144 | 7 | -9.18 | -13.2 | 73% |
| T-120..T-60 s | 0.20 | 6 | 4 | +6.38 | +0.4 | 83% |
| T-180..T-120 s | 0.02 | 701 | 17 | +2.19 | +15.4 | 87% |
| T-180..T-120 s | 0.05 | 532 | 13 | +2.27 | +12.1 | 85% |
| T-180..T-120 s | 0.10 | 399 | 10 | +0.26 | +1.0 | 81% |
| T-180..T-120 s | 0.20 | 66 | 8 | +22.53 | +14.9 | 98% |

Model vs book mid as predictors (Brier, lower is better), and one trade per market per window at the first signal, size = min(touch depth, 50):

| window | rows | Brier model | Brier book mid | thr | markets traded | contracts | P&L $ | $/mkt | t (markets) | win % |
|---|---|---|---|---|---|---|---|---|---|---|
| T-60..T-30 s | 336 | 0.008 | 0.009 | 0.05 | 1 | — | +15.6 | +15.60 | +nan | 100% |
| T-60..T-30 s | 336 | 0.008 | 0.009 | 0.10 | 1 | — | -21.3 | -21.35 | +nan | 0% |
| T-120..T-60 s | 1,311 | 0.064 | 0.058 | 0.05 | 8 | — | -26.7 | -3.33 | -0.6 | 75% |
| T-120..T-60 s | 1,311 | 0.064 | 0.058 | 0.10 | 7 | — | -30.7 | -4.38 | -0.7 | 71% |
| T-180..T-120 s | 1,439 | 0.056 | 0.054 | 0.05 | 13 | — | +56.2 | +4.32 | +1.0 | 92% |
| T-180..T-120 s | 1,439 | 0.056 | 0.054 | 0.10 | 10 | — | +55.7 | +5.57 | +1.0 | 90% |
