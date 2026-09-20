# Quoter simulation, KXLALIGATOTAL, 2026-09-20

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 16 | -16.32 | 68.76 | -85.09 | -247.41 | 16 | -16.32 | 68.76 | -85.09 | -7.99 | -8.34 | -1.02 | 1.66 | -2.45 | -5.98 | 7,083 | -0.23 | -0.45 | 69.15 | 1.51 | 564 | 18.84 | 12.77 | 0.00 |
|  ↳ vetoes: {'priority_fills': 775} |
| touch joiner, size 5 | 16 | -5.24 | 21.23 | -26.48 | -70.03 | 16 | -5.24 | 21.23 | -26.48 | -2.79 | -2.45 | -0.33 | 0.78 | -1.69 | -2.89 | 2,110 | -0.25 | -0.44 | 68.42 | 0.45 | 494 | 4.95 | 3.42 | 0.00 |
|  ↳ vetoes: {'priority_fills': 601} |
| touch joiner, depth >= 50 | 16 | -4.92 | 55.55 | -60.47 | -210.19 | 16 | -4.92 | 55.55 | -60.47 | -1.65 | -3.27 | -0.31 | 1.66 | -0.74 | -4.44 | 5,011 | -0.10 | -0.56 | 78.08 | 1.07 | 365 | 18.47 | 12.26 | 0.00 |
|  ↳ vetoes: {'thin': 134286, 'priority_fills': 692} |
| join only, never improve | 15 | -6.18 | 50.99 | -57.17 | -205.52 | 15 | -6.18 | 50.99 | -57.17 | 2.24 | -8.42 | -0.41 | 2.28 | -0.70 | -7.24 | 4,693 | -0.13 | -0.37 | 0.00 | 1.00 | 399 | 19.43 | 11.63 | 0.00 |
|  ↳ vetoes: {'priority_fills': 295} |
| touch joiner, pessimistic queue | 14 | -21.00 | 62.27 | -83.27 | -249.51 | 14 | -21.00 | 62.27 | -83.27 | -15.22 | -5.78 | -1.50 | 1.95 | -2.88 | -6.83 | 5,870 | -0.36 | -0.62 | 80.87 | 1.26 | 460 | 18.75 | 11.10 | 0.00 |
|  ↳ vetoes: {'priority_fills': 810} |
| touch joiner, carry (no flatten) | 16 | -16.32 | 68.76 | -85.09 | -247.41 | 16 | -16.32 | 68.76 | -85.09 | -7.99 | -8.34 | -1.02 | 1.66 | -2.45 | -5.98 | 7,083 | -0.23 | -0.45 | 69.15 | 1.51 | 564 | 18.84 | 12.77 | 0.00 |
|  ↳ vetoes: {'priority_fills': 775} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 4,144 | 26% | -0.96 |
| improve | partial | 1000-ms | 1000-ms | 2,788 | 18% | +0.10 |
| improve | sweep | 1000-ms | ? | 2,052 | 13% | -0.02 |
| join | partial | 1000-ms | 1000-ms | 1,489 | 9% | +0.21 |
| join | partial | 0-5ms | ? | 1,311 | 8% | +0.38 |
| improve | partial | 0-5ms | ? | 1,072 | 7% | -2.01 |
| join | sweep | 0-5ms | ? | 751 | 5% | -1.69 |
| improve | sweep | 200-1000ms | ? | 565 | 4% | -1.38 |
| join | partial | 1000-ms | ? | 385 | 2% | +0.24 |
| improve | sweep | 50-200ms | ? | 335 | 2% | -1.01 |
| join | sweep | 1000-ms | ? | 284 | 2% | +0.33 |
| improve | partial | 200-1000ms | 200-1000ms | 189 | 1% | +1.73 |
| improve | sweep | 16-50ms | ? | 163 | 1% | -2.23 |
| improve | partial | 50-200ms | 50-200ms | 77 | 0% | +0.39 |
| improve | partial | 5-16ms | 5-16ms | 76 | 0% | +1.05 |
| join | sweep | 200-1000ms | ? | 45 | 0% | -1.04 |
| join | sweep | 50-200ms | ? | 40 | 0% | +0.00 |
| improve | partial | 0-5ms | 0-5ms | 39 | 0% | +0.83 |
| join | partial | 200-1000ms | 200-1000ms | 21 | 0% | -0.69 |
| improve | partial | 0-5ms | 1000-ms | 20 | 0% | +0.50 |
| join | partial | 50-200ms | 50-200ms | 20 | 0% | +0.50 |
| improve | sweep | 1000-ms | 1000-ms | 20 | 0% | -0.87 |
| join | sweep | 1000-ms | 1000-ms | 20 | 0% | -1.00 |
| improve | partial | 16-50ms | 16-50ms | 7 | 0% | +0.43 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 7,279 | 46% | -0.76 |
| improve | partial | — | — | 4,273 | 27% | -0.31 |
| join | partial | — | — | 3,226 | 20% | +0.28 |
| join | sweep | — | — | 1,141 | 7% | -1.09 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 1,079 | 23% | -0.99 |
| improve | partial | 1000-ms | 1000-ms | 805 | 17% | +0.01 |
| improve | sweep | 1000-ms | ? | 681 | 15% | +0.10 |
| join | partial | 0-5ms | ? | 439 | 9% | +0.15 |
| join | partial | 1000-ms | 1000-ms | 425 | 9% | +0.15 |
| improve | partial | 0-5ms | ? | 365 | 8% | -1.71 |
| improve | sweep | 200-1000ms | ? | 182 | 4% | -1.34 |
| join | sweep | 0-5ms | ? | 178 | 4% | -1.49 |
| improve | sweep | 50-200ms | ? | 102 | 2% | -1.49 |
| join | partial | 1000-ms | ? | 100 | 2% | +0.25 |
| join | sweep | 1000-ms | ? | 76 | 2% | +0.55 |
| improve | sweep | 16-50ms | ? | 57 | 1% | -2.50 |
| improve | partial | 200-1000ms | 200-1000ms | 52 | 1% | +1.74 |
| improve | partial | 5-16ms | 5-16ms | 28 | 1% | +0.98 |
| improve | partial | 50-200ms | 50-200ms | 27 | 1% | +0.14 |
| join | sweep | 200-1000ms | ? | 20 | 0% | -0.62 |
| join | sweep | 50-200ms | ? | 15 | 0% | +0.67 |
| improve | partial | 16-50ms | 16-50ms | 7 | 0% | +0.43 |
| join | partial | 200-1000ms | 200-1000ms | 6 | 0% | -1.17 |
| improve | partial | 0-5ms | 5-16ms | 5 | 0% | +11.50 |
| improve | partial | 0-5ms | 1000-ms | 5 | 0% | +0.50 |
| join | partial | 50-200ms | 50-200ms | 5 | 0% | +0.50 |
| improve | partial | 0-5ms | 0-5ms | 5 | 0% | +0.50 |
| join | sweep | 1000-ms | 1000-ms | 5 | 0% | -1.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 2,102 | 45% | -0.73 |
| improve | partial | — | — | 1,299 | 28% | -0.33 |
| join | partial | — | — | 975 | 21% | +0.15 |
| join | sweep | — | — | 294 | 6% | -0.78 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 3,902 | 34% | -1.34 |
| improve | sweep | 1000-ms | ? | 2,088 | 18% | -0.25 |
| improve | partial | 1000-ms | 1000-ms | 1,335 | 12% | +0.34 |
| join | partial | 1000-ms | 1000-ms | 1,183 | 10% | +0.09 |
| join | partial | 0-5ms | ? | 607 | 5% | +0.03 |
| improve | sweep | 200-1000ms | ? | 557 | 5% | -1.28 |
| improve | sweep | 50-200ms | ? | 345 | 3% | -0.80 |
| join | sweep | 0-5ms | ? | 329 | 3% | -1.04 |
| join | partial | 1000-ms | ? | 320 | 3% | +0.19 |
| improve | sweep | 16-50ms | ? | 158 | 1% | -2.37 |
| improve | partial | 0-5ms | ? | 154 | 1% | -0.17 |
| improve | partial | 200-1000ms | 200-1000ms | 148 | 1% | +1.27 |
| join | sweep | 1000-ms | ? | 141 | 1% | +0.05 |
| improve | partial | 50-200ms | 50-200ms | 57 | 0% | +0.70 |
| improve | partial | 5-16ms | 5-16ms | 57 | 0% | +0.43 |
| join | sweep | 50-200ms | ? | 40 | 0% | +2.00 |
| improve | partial | 0-5ms | 0-5ms | 30 | 0% | -2.33 |
| join | sweep | 200-1000ms | ? | 29 | 0% | +0.03 |
| join | partial | 50-200ms | 50-200ms | 20 | 0% | +0.50 |
| join | partial | 200-1000ms | 200-1000ms | 20 | 0% | -0.50 |
| improve | partial | 0-5ms | 5-16ms | 5 | 0% | +11.50 |
| improve | partial | 16-50ms | 16-50ms | 4 | 0% | +0.25 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 7,050 | 61% | -1.01 |
| join | partial | — | — | 2,150 | 19% | +0.09 |
| improve | partial | — | — | 1,790 | 16% | +0.38 |
| join | sweep | — | — | 539 | 5% | -0.47 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 0-5ms | ? | 3,881 | 36% | -0.63 |
| join | partial | 1000-ms | 1000-ms | 3,382 | 31% | +0.52 |
| join | sweep | 0-5ms | ? | 2,829 | 26% | -1.15 |
| join | partial | 1000-ms | ? | 454 | 4% | +0.32 |
| join | sweep | 1000-ms | 1000-ms | 124 | 1% | +1.03 |
| join | partial | 200-1000ms | 200-1000ms | 107 | 1% | -3.00 |
| join | partial | 50-200ms | 50-200ms | 76 | 1% | +1.00 |
| join | sweep | 200-1000ms | 200-1000ms | 30 | 0% | -7.50 |
| join | partial | 0-5ms | 1000-ms | 20 | 0% | +0.50 |
| join | partial | 5-16ms | 5-16ms | 12 | 0% | +4.50 |
| join | partial | 200-1000ms | 1000-ms | 3 | 0% | -3.50 |
| join | sweep | 5-16ms | ? | 1 | 0% | -4.00 |
| join | partial | 16-50ms | 16-50ms | 0 | 0% | +1.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 7,936 | 73% | -0.09 |
| join | sweep | — | — | 2,984 | 27% | -1.12 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 4,159 | 30% | -1.21 |
| improve | partial | 1000-ms | 1000-ms | 2,537 | 18% | +0.08 |
| improve | sweep | 1000-ms | ? | 2,037 | 15% | +0.03 |
| join | sweep | 0-5ms | ? | 1,185 | 8% | -1.36 |
| improve | partial | 0-5ms | ? | 963 | 7% | -2.06 |
| join | partial | 1000-ms | 1000-ms | 689 | 5% | +0.62 |
| improve | sweep | 200-1000ms | ? | 525 | 4% | -1.53 |
| join | partial | 0-5ms | ? | 499 | 4% | +0.66 |
| join | sweep | 1000-ms | ? | 365 | 3% | +0.25 |
| improve | sweep | 50-200ms | ? | 349 | 2% | -0.94 |
| improve | partial | 200-1000ms | 200-1000ms | 169 | 1% | +1.88 |
| improve | sweep | 16-50ms | ? | 158 | 1% | -2.37 |
| improve | partial | 5-16ms | 5-16ms | 81 | 1% | +1.14 |
| improve | partial | 50-200ms | 50-200ms | 79 | 1% | +0.43 |
| join | sweep | 200-1000ms | ? | 62 | 0% | -0.90 |
| join | sweep | 50-200ms | ? | 40 | 0% | +0.00 |
| improve | partial | 0-5ms | 0-5ms | 20 | 0% | -1.75 |
| join | partial | 1000-ms | ? | 20 | 0% | -0.50 |
| improve | partial | 0-5ms | 1000-ms | 20 | 0% | +0.50 |
| join | partial | 50-200ms | 50-200ms | 20 | 0% | +0.50 |
| improve | sweep | 1000-ms | 1000-ms | 20 | 0% | -2.00 |
| join | sweep | 1000-ms | 1000-ms | 20 | 0% | -1.00 |
| improve | partial | 16-50ms | 16-50ms | 7 | 0% | +0.43 |
| improve | partial | 0-5ms | 5-16ms | 5 | 0% | +11.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 7,249 | 52% | -0.90 |
| improve | partial | — | — | 3,881 | 28% | -0.34 |
| join | sweep | — | — | 1,672 | 12% | -0.95 |
| join | partial | — | — | 1,229 | 9% | +0.61 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 4,144 | 26% | -0.96 |
| improve | partial | 1000-ms | 1000-ms | 2,788 | 18% | +0.10 |
| improve | sweep | 1000-ms | ? | 2,052 | 13% | -0.02 |
| join | partial | 1000-ms | 1000-ms | 1,489 | 9% | +0.21 |
| join | partial | 0-5ms | ? | 1,311 | 8% | +0.38 |
| improve | partial | 0-5ms | ? | 1,072 | 7% | -2.01 |
| join | sweep | 0-5ms | ? | 751 | 5% | -1.69 |
| improve | sweep | 200-1000ms | ? | 565 | 4% | -1.38 |
| join | partial | 1000-ms | ? | 385 | 2% | +0.24 |
| improve | sweep | 50-200ms | ? | 335 | 2% | -1.01 |
| join | sweep | 1000-ms | ? | 284 | 2% | +0.33 |
| improve | partial | 200-1000ms | 200-1000ms | 189 | 1% | +1.73 |
| improve | sweep | 16-50ms | ? | 163 | 1% | -2.23 |
| improve | partial | 50-200ms | 50-200ms | 77 | 0% | +0.39 |
| improve | partial | 5-16ms | 5-16ms | 76 | 0% | +1.05 |
| join | sweep | 200-1000ms | ? | 45 | 0% | -1.04 |
| join | sweep | 50-200ms | ? | 40 | 0% | +0.00 |
| improve | partial | 0-5ms | 0-5ms | 39 | 0% | +0.83 |
| join | partial | 200-1000ms | 200-1000ms | 21 | 0% | -0.69 |
| improve | partial | 0-5ms | 1000-ms | 20 | 0% | +0.50 |
| join | partial | 50-200ms | 50-200ms | 20 | 0% | +0.50 |
| improve | sweep | 1000-ms | 1000-ms | 20 | 0% | -0.87 |
| join | sweep | 1000-ms | 1000-ms | 20 | 0% | -1.00 |
| improve | partial | 16-50ms | 16-50ms | 7 | 0% | +0.43 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 7,279 | 46% | -0.76 |
| improve | partial | — | — | 4,273 | 27% | -0.31 |
| join | partial | — | — | 3,226 | 20% | +0.28 |
| join | sweep | — | — | 1,141 | 7% | -1.09 |