# Settlement-window study, KXBTC15M 2026-09-16: 24 markets settled, 3,236 (market, second) rows

Model calibration in the last 60 s (P(YES) bin -> realized):

| p bin | n | realized |
|---|---|---|
| 0.0 | 234 | 0.00 |
| 0.2 | 1 | 1.00 |
| 0.3 | 2 | 1.00 |
| 0.4 | 4 | 1.00 |
| 0.5 | 1 | 1.00 |
| 0.7 | 2 | 1.00 |
| 0.9 | 7 | 1.00 |
| 1.0 | 256 | 1.00 |

Taking rule, one contract per (market, second) where the edge exceeds the threshold (¢ per contract, after taker fee):

| window | threshold | trades | markets | edge/ct ¢ | P&L $ | win % |
|---|---|---|---|---|---|---|
| T-30..T-15 s | 0.02 | 2 | 1 | +2.52 | +0.1 | 100% |
| T-60..T-30 s | 0.02 | 33 | 4 | +15.59 | +5.1 | 94% |
| T-60..T-30 s | 0.05 | 13 | 2 | +29.88 | +3.9 | 92% |
| T-60..T-30 s | 0.10 | 3 | 1 | +34.53 | +1.0 | 100% |
| T-60..T-30 s | 0.20 | 1 | 1 | +54.28 | +0.5 | 100% |
| T-120..T-60 s | 0.02 | 366 | 13 | -3.95 | -14.5 | 85% |
| T-120..T-60 s | 0.05 | 174 | 9 | -5.97 | -10.4 | 79% |
| T-120..T-60 s | 0.10 | 41 | 4 | -37.78 | -15.5 | 41% |
| T-120..T-60 s | 0.20 | 1 | 1 | +33.41 | +0.3 | 100% |
| T-180..T-120 s | 0.02 | 810 | 19 | +3.94 | +31.9 | 90% |
| T-180..T-120 s | 0.05 | 524 | 14 | +4.40 | +23.0 | 85% |
| T-180..T-120 s | 0.10 | 262 | 10 | +0.53 | +1.4 | 76% |
| T-180..T-120 s | 0.20 | 20 | 3 | -25.83 | -5.2 | 45% |

Model vs book mid as predictors (Brier, lower is better), and one trade per market per window at the first signal, size = min(touch depth, 50):

| window | rows | Brier model | Brier book mid | thr | markets traded | contracts | P&L $ | $/mkt | t (markets) | win % |
|---|---|---|---|---|---|---|---|---|---|---|
| T-60..T-30 s | 401 | 0.007 | 0.009 | 0.05 | 2 | — | +40.5 | +20.24 | +nan | 100% |
| T-60..T-30 s | 401 | 0.007 | 0.009 | 0.10 | 1 | — | +27.1 | +27.14 | +nan | 100% |
| T-120..T-60 s | 1,306 | 0.047 | 0.043 | 0.05 | 9 | — | +5.5 | +0.61 | +0.1 | 78% |
| T-120..T-60 s | 1,306 | 0.047 | 0.043 | 0.10 | 4 | — | +1.9 | +0.46 | +0.0 | 75% |
| T-180..T-120 s | 1,440 | 0.045 | 0.043 | 0.05 | 14 | — | +33.1 | +2.36 | +0.5 | 86% |
| T-180..T-120 s | 1,440 | 0.045 | 0.043 | 0.10 | 10 | — | +23.7 | +2.37 | +0.3 | 80% |
