# Sweep-conditioned markouts, 2026-09-14 to 2026-09-15

144,905,877 raw records; 639,429 trades; 391,186 sweeps; 7354 markets. Method: `python/kalshi_data/research/markouts.py`.

## KXBTCD

- 391,186 sweeps from 639,429 trades, 52,828,328 contracts; seq gaps in log: 0
- volume by sweep class: partial 54%, multi 32%, full 13%, deep 1%, unknown 0%
- sweep size: median 28, p90 308, p99 1646 contracts

Maker markout vs true mid, cents/contract, volume-weighted. markout_0 = half-spread captured at the touch.

| class | vol share | 0 | 1s | 10s | 30s | 60s |
|---|---|---|---|---|---|---|
| partial | 54% |  +0.56 |  +0.02 |  -0.03 |  -0.13 |  -0.19 |
| full | 13% |  +0.33 |  -1.21 |  -1.12 |  -1.22 |  -1.26 |
| multi | 32% |  +0.55 |  -1.03 |  -0.88 |  -0.76 |  -0.64 |
| deep | 1% | +14.75 | +14.33 | +14.61 | +14.51 | +14.56 |
| unknown | 0% |    n/a |  +0.50 |  +1.77 |  +8.15 | +12.98 |
| **full+multi (fill-conditioned)** | 45% |  +0.48 |  -1.08 |  -0.95 |  -0.89 |  -0.82 |
| all | 100% |  +0.62 |  -0.39 |  -0.35 |  -0.38 |  -0.37 |

Fill-conditioned (full+multi) markout by minutes to expiry:

| min to expiry | vol share | 0 | 1s | 10s | 30s | 60s |
|---|---|---|---|---|---|---|
| 0 | 3% |  +1.26 |  -1.23 |  -2.09 |  +3.45 |    n/a |
| 1 | 3% |  +0.63 |  -1.24 |  -1.94 |  -1.14 |  -0.22 |
| 2 | 3% |  +0.62 |  -1.44 |  -1.40 |  -1.27 |  -1.42 |
| 3 | 3% |  +0.57 |  -1.38 |  -1.16 |  +0.03 |  -0.00 |
| 4 | 3% |  +0.59 |  -1.17 |  -0.86 |  -0.99 |  -0.41 |
| 5 | 3% |  +0.57 |  -1.53 |  -1.14 |  -1.22 |  -0.39 |
| 6 | 3% |  +0.56 |  -0.88 |  -1.27 |  -0.91 |  -0.73 |
| 7 | 3% |  +0.60 |  -0.92 |  -0.64 |  -1.28 |  -0.88 |
| 8 | 3% |  +0.55 |  -1.07 |  -0.64 |  -0.93 |  +0.00 |
| 9 | 3% |  +0.57 |  -1.02 |  -0.89 |  -0.93 |  -0.86 |
| 10-14 | 11% |  +0.51 |  -1.26 |  -0.98 |  -1.03 |  -0.74 |
| 15+ | 61% |  +0.41 |  -1.00 |  -0.84 |  -0.88 |  -0.92 |


Markouts by index-signal context (signal = coinbase BTC mid move >= $8 over 1s). A same-AZ quoter can cancel
before sweeps arriving > 5ms after the tick; earlier ones are unavoidable.

| context | class | vol share | 0 | 1s | 10s | 30s | 60s |
|---|---|---|---|---|---|---|---|
| quiet (no signal in 1s) | all | 75% |  +0.57 |  -0.35 |  -0.28 |  -0.31 |  -0.26 |
| quiet (no signal in 1s) | full+multi | 34% |  +0.50 |  -0.99 |  -0.81 |  -0.79 |  -0.61 |
| quiet (no signal in 1s) | partial | 41% |  +0.56 |  +0.13 |  +0.11 |  +0.02 |  -0.03 |
| post-signal, dodgeable (5-1000ms) | all | 22% |  +0.78 |  -0.44 |  -0.49 |  -0.48 |  -0.61 |
| post-signal, dodgeable (5-1000ms) | full+multi | 10% |  +0.39 |  -1.30 |  -1.30 |  -1.11 |  -1.32 |
| post-signal, dodgeable (5-1000ms) | partial | 12% |  +0.57 |  -0.26 |  -0.38 |  -0.51 |  -0.59 |
| post-signal, unavoidable (<=5ms) | all | 2% |  +0.76 |  -1.35 |  -1.37 |  -1.45 |  -1.60 |
| post-signal, unavoidable (<=5ms) | full+multi | 1% |  +0.64 |  -1.93 |  -2.00 |  -2.11 |  -2.58 |
| post-signal, unavoidable (<=5ms) | partial | 1% |  +0.59 |  -1.16 |  -1.15 |  -1.22 |  -1.10 |

Markouts by SIGNED signal move over the prior 1s (+ = spot already moved in the taker's direction):

| prior-1s move | class | vol share | 0 | 1s | 10s | 30s | 60s |
|---|---|---|---|---|---|---|---|
| < -$8 | all | 5% |  +0.75 |  +0.10 |  -0.12 |  +0.28 |  +0.27 |
| < -$8 | full+multi | 2% |  +0.48 |  -0.62 |  -1.05 |  -0.60 |  -0.84 |
| < -$8 | partial | 3% |  +0.59 |  +0.33 |  +0.30 |  +0.64 |  +0.83 |
| -$8..-$2 | all | 7% |  +0.54 |  -0.27 |  +0.06 |  +0.16 |  +0.23 |
| -$8..-$2 | full+multi | 3% |  +0.29 |  -1.18 |  -0.77 |  -0.67 |  -0.61 |
| -$8..-$2 | partial | 4% |  +0.56 |  +0.34 |  +0.60 |  +0.70 |  +0.79 |
| -$2..+$2 | all | 56% |  +0.56 |  -0.19 |  -0.13 |  -0.14 |  -0.05 |
| -$2..+$2 | full+multi | 25% |  +0.51 |  -0.79 |  -0.67 |  -0.61 |  -0.38 |
| -$2..+$2 | partial | 30% |  +0.56 |  +0.28 |  +0.28 |  +0.21 |  +0.18 |
| +$2..+$8 | all | 11% |  +0.81 |  -0.92 |  -0.97 |  -0.95 |  -1.07 |
| +$2..+$8 | full+multi | 5% |  +0.53 |  -1.84 |  -1.76 |  -1.67 |  -1.95 |
| +$2..+$8 | partial | 6% |  +0.57 |  -0.71 |  -0.87 |  -0.91 |  -0.92 |
| > +$8 | all | 10% |  +0.71 |  -1.12 |  -1.28 |  -1.58 |  -1.77 |
| > +$8 | full+multi | 4% |  +0.48 |  -1.79 |  -1.85 |  -2.05 |  -2.43 |
| > +$8 | partial | 6% |  +0.57 |  -0.97 |  -1.21 |  -1.57 |  -1.65 |

Does the index follow the sweep? Mean signed index move after the sweep, $ (+ = in the taker's direction), volume-weighted:

| class | 1s | 5s | 30s | n |
|---|---|---|---|---|
| partial |  +2.23 |  +2.33 |  +2.54 | 300,514 |
| full+multi |  +2.52 |  +2.73 |  +3.22 | 63,352 |
| all |  +2.36 |  +2.49 |  +2.92 | 366,126 |

Fill-conditioned, excluding the last 2 minutes: 1s -1.07c, 10s -0.90c, 30s -0.91c, 60s -0.83c (half-spread +0.46c)
