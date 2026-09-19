# Market survey, 2026-09-17: 88 markets with >= 1 min two-sided

| group | markets | two-sided h | spread_c | touch_size | touch_life_ms | vac/h | refill<=2ms | refill<=16ms | refill<=2s | taker/h | sweep% | mo10_c | mo30_c |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KXBTC15M | 88 | 19.7 | 0.74 | 2942 | 8 | 10485 | 23% | 41% | 60% | 10,428,044 | 23% | +0.04 | +0.01 |
| KXBTC15M mid (10-90c) | 74 | 16.7 | 0.79 | 3028 | 8 | 10747 | 23% | 42% | 61% | 10,782,320 | 23% | +0.03 | -0.02 |
| KXBTC15M tails (<10c or >90c) | 14 | 3.0 | 0.47 | 1832 | 8 | 9050 | 18% | 34% | 53% | 8,487,227 | 23% | +0.15 | +0.23 |

KXBTC15M: maker markout at 30 s by age of the hit touch level when the trade arrived (a REST joiner is on levels >= ~15 ms old)

| age of level | class | contracts | share | mo30 ¢ |
|---|---|---|---|---|
| 0-5ms | partial | 17,111,192 | 9% | +0.01 |
| 0-5ms | sweep | 39,642,580 | 20% | -0.28 |
| 5-16ms | partial | 3,347,095 | 2% | -0.92 |
| 5-16ms | sweep | 789,321 | 0% | -0.90 |
| 16-50ms | partial | 4,887,966 | 3% | -0.65 |
| 16-50ms | sweep | 437,535 | 0% | +0.56 |
| 50-200ms | partial | 14,108,707 | 7% | -0.06 |
| 50-200ms | sweep | 1,038,722 | 1% | +0.03 |
| 200-1000ms | partial | 38,817,852 | 20% | +0.13 |
| 200-1000ms | sweep | 1,661,109 | 1% | -0.06 |
| 1000-ms | partial | 70,884,459 | 37% | +0.22 |
| 1000-ms | sweep | 978,976 | 1% | +0.54 |
