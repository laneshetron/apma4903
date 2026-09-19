# Market survey, 2026-09-17: 88 markets with >= 1 min two-sided

| group | markets | two-sided h | spread_c | touch_size | touch_life_ms | vac/h | refill<=2ms | refill<=16ms | refill<=2s | taker/h | sweep% | mo10_c | mo30_c |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KXETH15M | 88 | 19.7 | 0.92 | 84 | 19 | 10870 | 3% | 25% | 50% | 421,089 | 44% | +0.39 | +0.38 |
| KXETH15M mid (10-90c) | 63 | 14.2 | 1.03 | 100 | 18 | 11095 | 3% | 26% | 51% | 446,121 | 45% | +0.41 | +0.39 |
| KXETH15M tails (<10c or >90c) | 25 | 5.5 | 0.63 | 51 | 23 | 10281 | 2% | 19% | 47% | 355,678 | 41% | +0.34 | +0.34 |

KXETH15M: maker markout at 30 s by age of the hit touch level when the trade arrived (a REST joiner is on levels >= ~15 ms old)

| age of level | class | contracts | share | mo30 ¢ |
|---|---|---|---|---|
| 0-5ms | partial | 1,218,289 | 16% | +0.86 |
| 0-5ms | sweep | 3,189,508 | 41% | +0.27 |
| 5-16ms | partial | 156,934 | 2% | -0.80 |
| 5-16ms | sweep | 49,011 | 1% | +2.25 |
| 16-50ms | partial | 152,044 | 2% | +0.52 |
| 16-50ms | sweep | 26,896 | 0% | +0.66 |
| 50-200ms | partial | 320,382 | 4% | +0.19 |
| 50-200ms | sweep | 68,088 | 1% | +1.44 |
| 200-1000ms | partial | 730,224 | 9% | +0.46 |
| 200-1000ms | sweep | 111,626 | 1% | +1.23 |
| 1000-ms | partial | 1,578,410 | 20% | +0.20 |
| 1000-ms | sweep | 143,833 | 2% | +0.12 |
