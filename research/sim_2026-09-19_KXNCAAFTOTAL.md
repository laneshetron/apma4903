# Quoter simulation, KXNCAAFTOTAL, 2026-09-19

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 535 | -42.56 | 86.05 | -109.09 | -131.33 | 535 | -42.56 | 86.05 | -109.09 | 34.25 | -76.80 | -0.08 | 0.51 | -3.63 | -4.05 | 6,829 | -0.62 | -0.27 | 63.89 | 0.05 | 4,987 | 3.32 | 0.85 | 6.14 |
|  ↳ vetoes: {'capital': 15175639, 'priority_fills': 4026} |
| touch joiner, size 5 | 547 | -60.49 | 107.46 | -154.35 | -154.77 | 547 | -60.49 | 107.46 | -154.35 | 17.87 | -78.36 | -0.11 | 0.41 | -6.26 | -2.23 | 8,898 | -0.68 | -0.19 | 65.29 | 0.07 | 6,059 | 2.85 | 0.80 | 4.95 |
|  ↳ vetoes: {'priority_fills': 4701, 'capital': 11007175} |
| touch joiner, depth >= 50 | 537 | -32.39 | 81.97 | -98.89 | -116.71 | 537 | -32.39 | 81.97 | -98.89 | 33.54 | -65.93 | -0.06 | 0.49 | -2.85 | -3.25 | 5,670 | -0.57 | -0.21 | 79.96 | 0.04 | 3,902 | 3.33 | 0.97 | 5.05 |
|  ↳ vetoes: {'thin': 3320054, 'capital': 14005694, 'priority_fills': 3614} |
| join only, never improve | 508 | -20.40 | 68.93 | -75.64 | -93.38 | 508 | -20.40 | 68.93 | -75.64 | 43.34 | -63.74 | -0.04 | 0.55 | -1.64 | -3.65 | 5,040 | -0.40 | 0.05 | 0.00 | 0.04 | 3,860 | 2.96 | 0.94 | 4.82 |
|  ↳ vetoes: {'capital': 14284621, 'priority_fills': 1564} |
| touch joiner, pessimistic queue | 525 | -31.24 | 67.51 | -81.14 | -100.70 | 525 | -31.24 | 67.51 | -81.14 | 40.60 | -71.84 | -0.06 | 0.52 | -2.61 | -4.24 | 4,904 | -0.64 | -0.28 | 75.30 | 0.04 | 3,854 | 2.80 | 0.90 | 4.37 |
|  ↳ vetoes: {'capital': 17170358, 'priority_fills': 3753} |
| touch joiner, carry (no flatten) | 528 | -9.52 | 73.56 | -82.86 | -98.94 | 528 | -9.52 | 73.56 | -82.86 | 45.45 | -54.97 | -0.02 | 0.43 | -0.95 | -3.10 | 5,788 | -0.16 | -0.14 | 63.09 | 0.05 | 4,432 | 2.89 | 1.47 | 5.54 |
|  ↳ vetoes: {'capital': 16534188, 'priority_fills': 3446} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 1,845 | 22% | +0.05 |
| improve | sweep | 0-5ms | ? | 1,602 | 19% | -0.73 |
| join | partial | 1000-ms | 1000-ms | 957 | 12% | +0.16 |
| join | partial | 0-5ms | ? | 837 | 10% | -0.68 |
| join | partial | 1000-ms | ? | 695 | 8% | +0.45 |
| improve | partial | 1000-ms | 1000-ms | 616 | 7% | +0.25 |
| join | sweep | 0-5ms | ? | 595 | 7% | -1.38 |
| improve | partial | 0-5ms | ? | 336 | 4% | -0.55 |
| join | sweep | 1000-ms | ? | 162 | 2% | -1.75 |
| improve | sweep | 200-1000ms | ? | 151 | 2% | +0.14 |
| improve | sweep | 50-200ms | ? | 145 | 2% | +1.09 |
| improve | partial | 50-200ms | 50-200ms | 63 | 1% | +0.52 |
| improve | sweep | 16-50ms | ? | 52 | 1% | -0.86 |
| join | sweep | 1000-ms | 1000-ms | 50 | 1% | -1.38 |
| improve | partial | 200-1000ms | 200-1000ms | 44 | 1% | -0.09 |
| join | sweep | 200-1000ms | ? | 19 | 0% | +1.89 |
| improve | partial | 16-50ms | 16-50ms | 18 | 0% | +1.31 |
| join | sweep | 50-200ms | ? | 14 | 0% | -0.86 |
| join | partial | 200-1000ms | 200-1000ms | 14 | 0% | -1.14 |
| join | sweep | 16-50ms | ? | 13 | 0% | -0.46 |
| join | sweep | 5-16ms | ? | 10 | 0% | -1.81 |
| join | partial | 50-200ms | 50-200ms | 7 | 0% | -0.57 |
| improve | partial | 5-16ms | 5-16ms | 7 | 0% | +0.71 |
| improve | sweep | 5-16ms | ? | 5 | 0% | -0.31 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 3,801 | 46% | -0.25 |
| join | partial | — | — | 2,512 | 30% | -0.06 |
| improve | partial | — | — | 1,085 | 13% | +0.03 |
| join | sweep | — | — | 869 | 11% | -1.37 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 2,756 | 26% | +0.31 |
| improve | sweep | 0-5ms | ? | 2,118 | 20% | -0.90 |
| join | partial | 1000-ms | 1000-ms | 1,168 | 11% | +0.13 |
| join | partial | 0-5ms | ? | 996 | 9% | -0.65 |
| improve | partial | 1000-ms | 1000-ms | 748 | 7% | +0.30 |
| join | sweep | 0-5ms | ? | 645 | 6% | -1.03 |
| join | partial | 1000-ms | ? | 626 | 6% | +0.41 |
| improve | partial | 0-5ms | ? | 475 | 4% | -0.38 |
| improve | sweep | 200-1000ms | ? | 215 | 2% | +0.59 |
| join | sweep | 1000-ms | ? | 205 | 2% | -0.74 |
| improve | sweep | 50-200ms | ? | 183 | 2% | +0.11 |
| improve | sweep | 16-50ms | ? | 95 | 1% | -1.58 |
| improve | partial | 200-1000ms | 200-1000ms | 84 | 1% | -0.49 |
| improve | partial | 50-200ms | 50-200ms | 70 | 1% | +1.31 |
| join | sweep | 1000-ms | 1000-ms | 42 | 0% | -0.77 |
| improve | partial | 16-50ms | 16-50ms | 34 | 0% | +0.46 |
| join | partial | 200-1000ms | 200-1000ms | 16 | 0% | -0.56 |
| join | sweep | 5-16ms | ? | 15 | 0% | -1.90 |
| join | sweep | 50-200ms | ? | 15 | 0% | -0.07 |
| improve | partial | 5-16ms | 5-16ms | 14 | 0% | -0.29 |
| join | sweep | 200-1000ms | ? | 13 | 0% | +0.31 |
| join | partial | 50-200ms | 50-200ms | 13 | 0% | +1.27 |
| join | sweep | 16-50ms | ? | 13 | 0% | -0.85 |
| improve | partial | 0-5ms | 0-5ms | 6 | 0% | +5.42 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 5,372 | 51% | -0.20 |
| join | partial | — | — | 2,828 | 27% | -0.08 |
| improve | partial | — | — | 1,430 | 14% | +0.09 |
| join | sweep | — | — | 950 | 9% | -0.94 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 1,922 | 29% | +0.09 |
| improve | sweep | 0-5ms | ? | 1,764 | 26% | -0.92 |
| join | partial | 1000-ms | ? | 693 | 10% | +0.46 |
| join | partial | 1000-ms | 1000-ms | 618 | 9% | +0.21 |
| join | partial | 0-5ms | ? | 438 | 7% | -0.75 |
| improve | partial | 1000-ms | 1000-ms | 386 | 6% | +0.26 |
| improve | sweep | 200-1000ms | ? | 209 | 3% | +0.45 |
| join | sweep | 0-5ms | ? | 165 | 2% | -1.25 |
| improve | sweep | 50-200ms | ? | 159 | 2% | -0.02 |
| join | sweep | 1000-ms | ? | 86 | 1% | -0.12 |
| improve | sweep | 16-50ms | ? | 65 | 1% | +0.70 |
| improve | partial | 0-5ms | ? | 48 | 1% | -0.24 |
| improve | partial | 200-1000ms | 200-1000ms | 27 | 0% | +0.26 |
| improve | partial | 50-200ms | 50-200ms | 21 | 0% | +0.36 |
| improve | sweep | 0-5ms | 1000-ms | 20 | 0% | -3.50 |
| join | partial | 200-1000ms | 200-1000ms | 14 | 0% | -0.22 |
| improve | partial | 16-50ms | 16-50ms | 10 | 0% | +0.55 |
| join | sweep | 1000-ms | 1000-ms | 7 | 0% | -3.86 |
| improve | partial | 5-16ms | 5-16ms | 5 | 0% | +2.60 |
| join | sweep | 200-1000ms | ? | 4 | 0% | +0.12 |
| join | sweep | 5-16ms | ? | 4 | 0% | -1.25 |
| improve | sweep | 5-16ms | ? | 2 | 0% | +1.46 |
| improve | sweep | 200-1000ms | 200-1000ms | 2 | 0% | -3.50 |
| join | partial | 50-200ms | ? | 1 | 0% | -1.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 4,143 | 62% | -0.33 |
| join | partial | — | — | 1,766 | 26% | +0.06 |
| improve | partial | — | — | 498 | 7% | +0.26 |
| join | sweep | — | — | 268 | 4% | -0.93 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 0-5ms | ? | 2,105 | 34% | -0.14 |
| join | partial | 1000-ms | 1000-ms | 1,861 | 30% | +0.18 |
| join | sweep | 0-5ms | ? | 1,152 | 18% | -0.32 |
| join | partial | 1000-ms | ? | 978 | 16% | +0.60 |
| join | sweep | 1000-ms | 1000-ms | 100 | 2% | -0.17 |
| join | partial | 200-1000ms | 200-1000ms | 24 | 0% | +1.56 |
| join | sweep | 5-16ms | ? | 14 | 0% | -0.17 |
| join | sweep | 1000-ms | ? | 13 | 0% | -1.80 |
| join | partial | 200-1000ms | ? | 13 | 0% | +4.64 |
| join | partial | 200-1000ms | 1000-ms | 4 | 0% | +2.62 |
| join | sweep | 200-1000ms | 1000-ms | 4 | 0% | -3.88 |
| join | sweep | 200-1000ms | 200-1000ms | 4 | 0% | +2.08 |
| join | sweep | 50-200ms | 50-200ms | 2 | 0% | -3.50 |
| join | partial | 5-16ms | ? | 1 | 0% | -3.44 |
| join | partial | 50-200ms | 50-200ms | 1 | 0% | -3.50 |
| join | sweep | 16-50ms | 16-50ms | 1 | 0% | +5.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 4,987 | 79% | +0.15 |
| join | sweep | — | — | 1,291 | 21% | -0.33 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 1,725 | 29% | +0.30 |
| improve | sweep | 0-5ms | ? | 1,520 | 26% | -1.22 |
| join | sweep | 0-5ms | ? | 638 | 11% | -0.81 |
| improve | partial | 1000-ms | 1000-ms | 464 | 8% | +0.40 |
| join | partial | 1000-ms | 1000-ms | 336 | 6% | +0.20 |
| improve | partial | 0-5ms | ? | 259 | 4% | -0.48 |
| join | partial | 0-5ms | ? | 246 | 4% | -0.44 |
| join | sweep | 1000-ms | ? | 160 | 3% | -0.57 |
| improve | sweep | 200-1000ms | ? | 115 | 2% | +1.63 |
| join | partial | 1000-ms | ? | 96 | 2% | +0.36 |
| improve | sweep | 50-200ms | ? | 87 | 1% | +0.40 |
| improve | partial | 200-1000ms | 200-1000ms | 47 | 1% | -0.39 |
| join | sweep | 1000-ms | 1000-ms | 44 | 1% | +0.60 |
| improve | partial | 50-200ms | 50-200ms | 38 | 1% | +1.22 |
| improve | sweep | 16-50ms | ? | 37 | 1% | +0.19 |
| join | sweep | 200-1000ms | ? | 16 | 0% | +1.12 |
| join | sweep | 5-16ms | ? | 8 | 0% | -2.06 |
| join | sweep | 50-200ms | ? | 7 | 0% | -0.36 |
| improve | partial | 5-16ms | 5-16ms | 6 | 0% | +0.33 |
| improve | partial | 16-50ms | 16-50ms | 5 | 0% | +1.80 |
| join | partial | 200-1000ms | 200-1000ms | 5 | 0% | -1.70 |
| join | sweep | 16-50ms | ? | 5 | 0% | -0.70 |
| join | sweep | 16-50ms | 16-50ms | 3 | 0% | +0.83 |
| join | partial | 50-200ms | 50-200ms | 3 | 0% | +0.17 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 3,488 | 59% | -0.32 |
| join | sweep | — | — | 883 | 15% | -0.67 |
| improve | partial | — | — | 821 | 14% | +0.14 |
| join | partial | — | — | 690 | 12% | -0.04 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 1,435 | 20% | +0.23 |
| improve | sweep | 0-5ms | ? | 1,339 | 19% | -0.57 |
| join | partial | 1000-ms | 1000-ms | 907 | 13% | +0.15 |
| join | partial | 0-5ms | ? | 800 | 11% | -0.75 |
| join | partial | 1000-ms | ? | 696 | 10% | +0.42 |
| improve | partial | 1000-ms | 1000-ms | 557 | 8% | +0.44 |
| join | sweep | 0-5ms | ? | 440 | 6% | -1.15 |
| improve | partial | 0-5ms | ? | 283 | 4% | -0.38 |
| join | sweep | 1000-ms | ? | 136 | 2% | -0.54 |
| improve | sweep | 200-1000ms | ? | 120 | 2% | +1.04 |
| improve | sweep | 50-200ms | ? | 107 | 2% | -0.59 |
| improve | partial | 50-200ms | 50-200ms | 59 | 1% | +0.14 |
| improve | partial | 200-1000ms | 200-1000ms | 49 | 1% | -0.50 |
| improve | sweep | 16-50ms | ? | 39 | 1% | +0.19 |
| join | sweep | 1000-ms | 1000-ms | 33 | 0% | -1.22 |
| improve | partial | 16-50ms | 16-50ms | 18 | 0% | +1.58 |
| join | partial | 200-1000ms | 200-1000ms | 13 | 0% | -0.46 |
| join | sweep | 200-1000ms | ? | 11 | 0% | +2.36 |
| join | sweep | 5-16ms | ? | 8 | 0% | -2.51 |
| join | sweep | 16-50ms | ? | 5 | 0% | -0.30 |
| join | sweep | 50-200ms | ? | 4 | 0% | +1.62 |
| join | partial | 50-200ms | 50-200ms | 4 | 0% | -0.38 |
| improve | partial | 5-16ms | 5-16ms | 4 | 0% | -0.50 |
| join | sweep | 200-1000ms | 200-1000ms | 3 | 0% | -5.17 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 3,046 | 43% | -0.12 |
| join | partial | — | — | 2,424 | 34% | -0.07 |
| improve | partial | — | — | 971 | 14% | +0.16 |
| join | sweep | — | — | 641 | 9% | -0.98 |