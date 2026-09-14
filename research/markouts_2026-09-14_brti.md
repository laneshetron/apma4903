# Sweep-conditioned markouts, 2026-09-14

40,616,691 raw records; 1,181,692 trades; 523,542 sweeps; 44 markets. Method: `python/kalshi_data/research/markouts.py`.

## KXBTC15M

- 523,542 sweeps from 1,181,692 trades, 71,386,492 contracts; seq gaps in log: 0
- volume by sweep class: partial 61%, multi 33%, full 6%, deep 0%, unknown 0%
- sweep size: median 18, p90 240, p99 2016 contracts

Maker markout vs true mid, cents/contract, volume-weighted. markout_0 = half-spread captured at the touch.

| class | vol share | 0 | 1s | 10s | 30s | 60s |
|---|---|---|---|---|---|---|
| partial | 61% |  +0.37 |  +0.22 |  +0.17 |  +0.23 |  +0.29 |
| full | 6% |  +0.32 |  -0.89 |  -0.92 |  -0.76 |  -0.43 |
| multi | 33% |  +0.32 |  -0.52 |  -0.82 |  -1.00 |  -0.68 |
| deep | 0% |  +6.68 |  +2.24 |  +4.19 |  +4.98 |  +2.11 |
| unknown | 0% |    n/a |  +0.43 |  +1.32 |  -4.86 |  +4.61 |
| **full+multi (fill-conditioned)** | 39% |  +0.32 |  -0.56 |  -0.83 |  -0.97 |  -0.65 |
| all | 100% |  +0.38 |  -0.09 |  -0.22 |  -0.23 |  -0.07 |

Fill-conditioned (full+multi) markout by minutes to expiry:

| min to expiry | vol share | 0 | 1s | 10s | 30s | 60s |
|---|---|---|---|---|---|---|
| 0 | 18% |  +0.41 |  -0.26 |  -0.80 |  +0.05 |    n/a |
| 1 | 17% |  +0.26 |  -0.68 |  -1.20 |  -1.63 |  +0.24 |
| 2 | 12% |  +0.17 |  -0.54 |  -0.46 |  -0.64 |  -0.67 |
| 3 | 9% |  +0.24 |  -0.62 |  -1.46 |  -1.97 |  -1.08 |
| 4 | 6% |  +0.25 |  -0.56 |  -0.65 |  -0.84 |  -0.67 |
| 5 | 5% |  +0.26 |  -0.59 |  -1.00 |  -1.59 |  -1.77 |
| 6 | 4% |  +0.28 |  -0.52 |  -0.50 |  -0.59 |  -0.58 |
| 7 | 4% |  +0.36 |  -0.75 |  -0.69 |  -0.39 |  -0.27 |
| 8 | 4% |  +0.41 |  -0.84 |  -0.97 |  -1.29 |  -2.04 |
| 9 | 3% |  +0.36 |  -0.72 |  -0.64 |  -0.77 |  -0.85 |
| 10-14 | 17% |  +0.47 |  -0.60 |  -0.57 |  -0.34 |  -0.25 |


Markouts by index-signal context (signal = BRTI move >= $8 over 1s). A same-AZ quoter can cancel
before sweeps arriving > 5ms after the tick; earlier ones are unavoidable.

| context | class | vol share | 0 | 1s | 10s | 30s | 60s |
|---|---|---|---|---|---|---|---|
| quiet (no signal in 1s) | all | 87% |  +0.39 |  -0.07 |  -0.22 |  -0.29 |  -0.04 |
| quiet (no signal in 1s) | full+multi | 33% |  +0.32 |  -0.54 |  -0.85 |  -1.08 |  -0.63 |
| quiet (no signal in 1s) | partial | 53% |  +0.38 |  +0.23 |  +0.19 |  +0.20 |  +0.33 |
| post-signal, dodgeable (5-1000ms) | all | 13% |  +0.34 |  -0.20 |  -0.24 |  +0.13 |  -0.25 |
| post-signal, dodgeable (5-1000ms) | full+multi | 5% |  +0.29 |  -0.70 |  -0.73 |  -0.31 |  -0.72 |
| post-signal, dodgeable (5-1000ms) | partial | 8% |  +0.37 |  +0.15 |  +0.09 |  +0.42 |  +0.04 |
| post-signal, unavoidable (<=5ms) | all | 0% |  +0.30 |  -0.12 |  +0.05 |  -0.73 |  -1.37 |
| post-signal, unavoidable (<=5ms) | full+multi | 0% |  +0.19 |  -0.64 |  -1.09 |  -3.05 |  -2.85 |
| post-signal, unavoidable (<=5ms) | partial | 0% |  +0.34 |  +0.05 |  +0.46 |  +0.12 |  -0.80 |

Does the index follow the sweep? Mean signed index move after the sweep, $ (+ = in the taker's direction), volume-weighted:

| class | 1s | 5s | 30s | n |
|---|---|---|---|---|
| partial |  +0.60 |  +0.65 |  -0.09 | 355,166 |
| full+multi |  +1.53 |  +1.40 |  +1.51 | 49,107 |
| all |  +0.96 |  +0.94 |  +0.53 | 405,205 |

Fill-conditioned, excluding the last 2 minutes: 1s -0.61c, 10s -0.75c, 30s -0.87c, 60s -0.76c (half-spread +0.31c)
