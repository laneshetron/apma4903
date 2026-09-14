# Sweep-conditioned markouts, 2026-09-14

41,084,476 raw records; 1,189,053 trades; 527,491 sweeps; 45 markets. Method: `python/kalshi_data/research/markouts.py`.

## KXBTC15M

- 527,491 sweeps from 1,189,053 trades, 71,811,424 contracts; seq gaps in log: 0
- volume by sweep class: partial 61%, multi 33%, full 6%, deep 0%, unknown 0%
- sweep size: median 18, p90 240, p99 2011 contracts

Maker markout vs true mid, cents/contract, volume-weighted. markout_0 = half-spread captured at the touch.

| class | vol share | 0 | 1s | 10s | 30s | 60s |
|---|---|---|---|---|---|---|
| partial | 61% |  +0.38 |  +0.22 |  +0.17 |  +0.24 |  +0.30 |
| full | 6% |  +0.32 |  -0.89 |  -0.92 |  -0.76 |  -0.42 |
| multi | 33% |  +0.32 |  -0.51 |  -0.82 |  -1.02 |  -0.69 |
| deep | 0% |  +6.68 |  +2.24 |  +4.19 |  +4.98 |  +2.11 |
| unknown | 0% |    n/a |  +0.43 |  +1.32 |  -4.86 |  +4.61 |
| **full+multi (fill-conditioned)** | 39% |  +0.32 |  -0.56 |  -0.83 |  -0.99 |  -0.65 |
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
| 10-14 | 17% |  +0.47 |  -0.57 |  -0.57 |  -0.44 |  -0.30 |


Markouts by index-signal context (signal = coinbase BTC mid move >= $8 over 1s). A same-AZ quoter can cancel
before sweeps arriving > 5ms after the tick; earlier ones are unavoidable.

| context | class | vol share | 0 | 1s | 10s | 30s | 60s |
|---|---|---|---|---|---|---|---|
| quiet (no signal in 1s) | all | 89% |  +0.38 |  -0.06 |  -0.19 |  -0.26 |  -0.01 |
| quiet (no signal in 1s) | full+multi | 34% |  +0.32 |  -0.52 |  -0.81 |  -1.04 |  -0.55 |
| quiet (no signal in 1s) | partial | 54% |  +0.38 |  +0.24 |  +0.20 |  +0.22 |  +0.32 |
| post-signal, dodgeable (5-1000ms) | all | 11% |  +0.34 |  -0.26 |  -0.34 |  +0.07 |  -0.39 |
| post-signal, dodgeable (5-1000ms) | full+multi | 4% |  +0.30 |  -0.77 |  -0.89 |  -0.45 |  -1.25 |
| post-signal, dodgeable (5-1000ms) | partial | 6% |  +0.37 |  +0.10 |  +0.04 |  +0.43 |  +0.19 |
| post-signal, unavoidable (<=5ms) | all | 0% |  +0.47 |  -1.54 |  -1.97 |  -2.47 |  -2.47 |
| post-signal, unavoidable (<=5ms) | full+multi | 0% |  +0.46 |  -2.59 |  -2.92 |  -3.43 |  -3.07 |
| post-signal, unavoidable (<=5ms) | partial | 0% |  +0.44 |  -0.55 |  -0.94 |  -1.72 |  -1.96 |

Markouts by SIGNED signal move over the prior 1s (+ = spot already moved in the taker's direction):

| prior-1s move | class | vol share | 0 | 1s | 10s | 30s | 60s |
|---|---|---|---|---|---|---|---|
| < -$8 | all | 3% |  +0.35 |  +0.40 |  +1.44 |  +1.35 |  -0.96 |
| < -$8 | full+multi | 1% |  +0.30 |  +0.25 |  +1.61 |  +0.90 |  -2.47 |
| < -$8 | partial | 2% |  +0.38 |  +0.49 |  +1.34 |  +1.66 |  +0.03 |
| -$8..-$2 | all | 4% |  +0.32 |  +0.11 |  +0.51 |  +0.77 |  +0.61 |
| -$8..-$2 | full+multi | 1% |  +0.27 |  -0.32 |  +0.37 |  +0.17 |  -0.11 |
| -$8..-$2 | partial | 3% |  +0.35 |  +0.34 |  +0.59 |  +1.09 |  +1.00 |
| -$2..+$2 | all | 50% |  +0.30 |  -0.00 |  -0.01 |  +0.04 |  +0.03 |
| -$2..+$2 | full+multi | 18% |  +0.24 |  -0.37 |  -0.31 |  -0.39 |  -0.52 |
| -$2..+$2 | partial | 31% |  +0.33 |  +0.23 |  +0.19 |  +0.33 |  +0.39 |
| +$2..+$8 | all | 5% |  +0.36 |  -0.80 |  -1.04 |  -1.30 |  -0.83 |
| +$2..+$8 | full+multi | 2% |  +0.35 |  -1.44 |  -1.63 |  -1.84 |  -0.82 |
| +$2..+$8 | partial | 3% |  +0.35 |  -0.27 |  -0.51 |  -0.75 |  -0.86 |
| > +$8 | all | 3% |  +0.37 |  -1.38 |  -3.02 |  -1.39 |  -0.59 |
| > +$8 | full+multi | 1% |  +0.32 |  -2.26 |  -4.21 |  -1.78 |  -0.42 |
| > +$8 | partial | 1% |  +0.40 |  -0.59 |  -1.97 |  -1.07 |  -0.75 |

Does the index follow the sweep? Mean signed index move after the sweep, $ (+ = in the taker's direction), volume-weighted:

| class | 1s | 5s | 30s | n |
|---|---|---|---|---|
| partial |  +0.47 |  +0.52 |  -0.41 | 319,439 |
| full+multi |  +1.32 |  +1.25 |  +1.63 | 45,845 |
| all |  +0.80 |  +0.80 |  +0.38 | 366,161 |

Fill-conditioned, excluding the last 2 minutes: 1s -0.60c, 10s -0.74c, 30s -0.89c, 60s -0.77c (half-spread +0.31c)
