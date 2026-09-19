# Quoter simulation, KXBTC15M, 2026-09-17

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline touch joiner | 88 | -213.92 | 794.19 | -998.99 | -942.43 | 88 | -213.92 | 794.19 | -998.99 | -212.49 | -1.43 | -2.43 | 4.44 | -5.13 | -13.53 | 261,421 | -0.08 | -0.06 | 15.06 | 0.13 | 25,564 | 19.90 | 0.00 | 10.49 |
|  ↳ vetoes: {'priority_fills': 6534, 'greeks': 14210722} |
| touch age >= 50 ms | 88 | -187.66 | 763.46 | -941.61 | -884.60 | 88 | -187.66 | 763.46 | -941.61 | -163.05 | -24.60 | -2.13 | 4.44 | -4.50 | -13.83 | 233,112 | -0.08 | -0.06 | 0.00 | 0.11 | 21,792 | 19.85 | 0.00 | 10.90 |
|  ↳ vetoes: {'young_touch': 3594680, 'priority_fills': 4331, 'greeks': 14210722} |
| touch age >= 200 ms | 88 | -190.10 | 694.85 | -875.11 | -815.57 | 88 | -190.10 | 694.85 | -875.11 | -178.74 | -11.36 | -2.16 | 4.51 | -4.49 | -14.82 | 201,389 | -0.09 | -0.07 | 0.00 | 0.10 | 18,843 | 19.88 | 0.00 | 11.57 |
|  ↳ vetoes: {'young_touch': 6066373, 'priority_fills': 3656, 'greeks': 14210722} |
| touch age >= 500 ms | 88 | -180.88 | 598.25 | -769.19 | -714.48 | 88 | -180.88 | 598.25 | -769.19 | -135.95 | -44.93 | -2.06 | 4.23 | -4.56 | -14.75 | 164,239 | -0.11 | -0.06 | 0.00 | 0.08 | 15,352 | 19.87 | 0.00 | 11.43 |
|  ↳ vetoes: {'young_touch': 8503542, 'priority_fills': 2795, 'greeks': 14210722} |
| touch age >= 1000 ms | 88 | -157.33 | 471.90 | -618.99 | -586.99 | 88 | -157.33 | 471.90 | -618.99 | -137.87 | -19.46 | -1.79 | 4.78 | -3.51 | -15.25 | 120,994 | -0.13 | -0.10 | 0.00 | 0.06 | 11,071 | 19.84 | 0.00 | 11.80 |
|  ↳ vetoes: {'young_touch': 11022087, 'priority_fills': 1825, 'greeks': 14210722} |
| touch age >= 200 ms, improves allowed | 88 | -239.80 | 674.85 | -904.31 | -837.74 | 88 | -239.80 | 674.85 | -904.31 | -211.23 | -28.57 | -2.73 | 4.69 | -5.45 | -13.42 | 211,764 | -0.11 | -0.09 | 10.27 | 0.10 | 20,374 | 19.86 | 0.00 | 11.67 |
|  ↳ vetoes: {'young_touch': 5593996, 'priority_fills': 5756, 'greeks': 14210722} |
| touch age >= 200 ms + depth gate | 88 | -46.40 | 584.57 | -621.54 | -568.00 | 88 | -46.40 | 584.57 | -621.54 | -32.86 | -13.55 | -0.53 | 4.13 | -1.20 | -16.72 | 158,496 | -0.03 | 0.00 | 0.00 | 0.08 | 11,733 | 19.84 | 0.00 | 11.01 |
|  ↳ vetoes: {'young_touch': 6209589, 'thin': 458429, 'priority_fills': 1617, 'greeks': 14210722} |
| touch age >= 200 ms, size 5 | 88 | -52.51 | 189.36 | -239.74 | -232.47 | 88 | -52.51 | 189.36 | -239.74 | -52.01 | -0.50 | -0.60 | 1.11 | -5.04 | -3.45 | 54,764 | -0.10 | -0.08 | 0.00 | 0.03 | 15,343 | 4.98 | 0.00 | 2.53 |
|  ↳ vetoes: {'young_touch': 6131074, 'priority_fills': 2745, 'greeks': 14210722} |
| touch age >= 200 ms, pessimistic queue | 88 | -400.39 | 295.04 | -685.54 | -596.68 | 88 | -400.39 | 295.04 | -685.54 | -381.07 | -19.32 | -4.55 | 4.23 | -10.10 | -18.16 | 113,840 | -0.35 | -0.27 | 0.00 | 0.06 | 9,861 | 19.76 | 0.00 | 11.44 |
|  ↳ vetoes: {'young_touch': 6162487, 'priority_fills': 5636, 'greeks': 14210722} |

baseline touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 98,483 | 38% | +0.13 |
| join | partial | 200-1000ms | 200-1000ms | 35,435 | 14% | +0.16 |
| join | sweep | 0-5ms | ? | 31,010 | 12% | -0.51 |
| join | partial | 0-5ms | ? | 27,371 | 10% | -0.19 |
| join | partial | 1000-ms | ? | 12,953 | 5% | -0.11 |
| improve | sweep | 200-1000ms | ? | 7,479 | 3% | -0.05 |
| improve | partial | 200-1000ms | 200-1000ms | 5,788 | 2% | +0.33 |
| join | partial | 200-1000ms | 1000-ms | 4,615 | 2% | -0.16 |
| improve | sweep | 0-5ms | ? | 4,545 | 2% | -0.28 |
| improve | partial | 50-200ms | 50-200ms | 3,587 | 1% | +0.23 |
| join | partial | 50-200ms | 50-200ms | 3,201 | 1% | +0.23 |
| improve | sweep | 50-200ms | ? | 3,190 | 1% | +0.29 |
| join | sweep | 5-16ms | ? | 2,929 | 1% | -2.12 |
| improve | partial | 1000-ms | 1000-ms | 2,683 | 1% | -0.47 |
| improve | sweep | 1000-ms | ? | 2,666 | 1% | -0.11 |
| improve | partial | 0-5ms | ? | 2,230 | 1% | +0.38 |
| join | partial | 200-1000ms | ? | 1,689 | 1% | +0.69 |
| improve | partial | 16-50ms | 16-50ms | 1,440 | 1% | -0.34 |
| join | sweep | 1000-ms | 1000-ms | 1,409 | 1% | -0.63 |
| join | sweep | 200-1000ms | 200-1000ms | 1,353 | 1% | -1.12 |
| join | sweep | 50-200ms | 50-200ms | 797 | 0% | -2.96 |
| improve | sweep | 16-50ms | ? | 697 | 0% | +0.39 |
| join | partial | 16-50ms | 16-50ms | 682 | 0% | -0.63 |
| join | partial | 0-5ms | 0-5ms | 598 | 0% | -1.49 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 186,117 | 71% | +0.06 |
| join | sweep | — | — | 39,673 | 15% | -0.73 |
| improve | sweep | — | — | 19,008 | 7% | -0.03 |
| improve | partial | — | — | 16,624 | 6% | +0.11 |

touch age >= 50 ms: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 103,663 | 44% | +0.12 |
| join | partial | 200-1000ms | 200-1000ms | 36,287 | 16% | +0.02 |
| join | sweep | 0-5ms | ? | 33,732 | 14% | -0.41 |
| join | partial | 0-5ms | ? | 29,420 | 13% | -0.07 |
| join | partial | 1000-ms | ? | 13,061 | 6% | -0.04 |
| join | partial | 200-1000ms | 1000-ms | 4,236 | 2% | -0.30 |
| join | partial | 50-200ms | 50-200ms | 2,384 | 1% | -0.22 |
| join | sweep | 5-16ms | ? | 2,218 | 1% | -1.87 |
| join | sweep | 200-1000ms | 200-1000ms | 1,672 | 1% | -0.69 |
| join | partial | 200-1000ms | ? | 1,491 | 1% | +0.97 |
| join | sweep | 1000-ms | 1000-ms | 1,329 | 1% | -1.23 |
| join | sweep | 50-200ms | 50-200ms | 967 | 0% | -1.35 |
| join | partial | 0-5ms | 0-5ms | 570 | 0% | -0.67 |
| join | sweep | 0-5ms | 0-5ms | 512 | 0% | -0.45 |
| join | sweep | 200-1000ms | 1000-ms | 272 | 0% | -1.74 |
| join | partial | 50-200ms | 200-1000ms | 253 | 0% | -1.03 |
| join | partial | 50-200ms | 1000-ms | 176 | 0% | -1.28 |
| join | sweep | 1000-ms | ? | 164 | 0% | -1.95 |
| join | sweep | 50-200ms | 200-1000ms | 141 | 0% | +1.17 |
| join | sweep | 50-200ms | 1000-ms | 123 | 0% | -1.57 |
| join | partial | 0-5ms | 1000-ms | 96 | 0% | +2.21 |
| join | partial | 5-16ms | 5-16ms | 69 | 0% | -4.33 |
| join | partial | 50-200ms | ? | 54 | 0% | -1.39 |
| join | sweep | 50-200ms | ? | 50 | 0% | -5.76 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 191,869 | 82% | +0.05 |
| join | sweep | — | — | 41,243 | 18% | -0.57 |

touch age >= 200 ms: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 102,512 | 51% | +0.10 |
| join | sweep | 0-5ms | ? | 28,397 | 14% | -0.49 |
| join | partial | 0-5ms | ? | 25,447 | 13% | -0.26 |
| join | partial | 200-1000ms | 200-1000ms | 21,933 | 11% | +0.07 |
| join | partial | 1000-ms | ? | 12,137 | 6% | -0.05 |
| join | partial | 200-1000ms | 1000-ms | 2,979 | 1% | +0.11 |
| join | sweep | 200-1000ms | 200-1000ms | 2,022 | 1% | -0.42 |
| join | sweep | 5-16ms | ? | 1,923 | 1% | -1.37 |
| join | sweep | 1000-ms | 1000-ms | 1,308 | 1% | -1.79 |
| join | partial | 200-1000ms | ? | 941 | 0% | +1.17 |
| join | partial | 0-5ms | 0-5ms | 569 | 0% | -0.52 |
| join | sweep | 0-5ms | 0-5ms | 361 | 0% | -0.24 |
| join | sweep | 200-1000ms | 1000-ms | 318 | 0% | -0.28 |
| join | sweep | 1000-ms | ? | 177 | 0% | -0.84 |
| join | partial | 0-5ms | 1000-ms | 94 | 0% | +1.54 |
| join | sweep | 200-1000ms | ? | 76 | 0% | -2.84 |
| join | partial | 5-16ms | 5-16ms | 66 | 0% | -4.51 |
| join | sweep | 5-16ms | 5-16ms | 63 | 0% | -0.19 |
| join | partial | 5-16ms | 1000-ms | 40 | 0% | +1.48 |
| join | partial | 0-5ms | 200-1000ms | 20 | 0% | -4.85 |
| join | partial | 5-16ms | ? | 5 | 0% | +6.43 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 166,744 | 83% | +0.04 |
| join | sweep | — | — | 34,645 | 17% | -0.58 |

touch age >= 500 ms: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 96,705 | 59% | +0.10 |
| join | partial | 0-5ms | ? | 21,178 | 13% | -0.02 |
| join | sweep | 0-5ms | ? | 20,717 | 13% | -0.56 |
| join | partial | 1000-ms | ? | 11,635 | 7% | +0.22 |
| join | partial | 200-1000ms | 200-1000ms | 7,181 | 4% | -0.44 |
| join | sweep | 5-16ms | ? | 1,694 | 1% | -1.43 |
| join | sweep | 1000-ms | 1000-ms | 1,481 | 1% | -1.88 |
| join | sweep | 200-1000ms | 200-1000ms | 1,115 | 1% | -1.31 |
| join | partial | 200-1000ms | 1000-ms | 928 | 1% | +0.99 |
| join | partial | 0-5ms | 0-5ms | 461 | 0% | -1.19 |
| join | sweep | 0-5ms | 0-5ms | 278 | 0% | -0.03 |
| join | partial | 200-1000ms | ? | 252 | 0% | +1.75 |
| join | sweep | 1000-ms | ? | 183 | 0% | -0.84 |
| join | sweep | 200-1000ms | 1000-ms | 143 | 0% | -4.33 |
| join | sweep | 200-1000ms | ? | 80 | 0% | -1.94 |
| join | partial | 5-16ms | 5-16ms | 71 | 0% | -3.17 |
| join | partial | 5-16ms | 1000-ms | 40 | 0% | +1.48 |
| join | sweep | 5-16ms | 5-16ms | 39 | 0% | -0.61 |
| join | partial | 0-5ms | 1000-ms | 34 | 0% | +5.38 |
| join | partial | 0-5ms | 200-1000ms | 20 | 0% | -4.85 |
| join | partial | 5-16ms | ? | 5 | 0% | +6.45 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 138,510 | 84% | +0.07 |
| join | sweep | — | — | 25,729 | 16% | -0.75 |

touch age >= 1000 ms: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 79,795 | 66% | +0.04 |
| join | partial | 0-5ms | ? | 14,593 | 12% | -0.04 |
| join | sweep | 0-5ms | ? | 12,272 | 10% | -0.79 |
| join | partial | 1000-ms | ? | 10,082 | 8% | +0.10 |
| join | sweep | 1000-ms | 1000-ms | 2,031 | 2% | -1.46 |
| join | sweep | 5-16ms | ? | 1,144 | 1% | -1.69 |
| join | partial | 0-5ms | 0-5ms | 468 | 0% | -0.87 |
| join | sweep | 1000-ms | ? | 240 | 0% | -0.65 |
| join | sweep | 0-5ms | 0-5ms | 213 | 0% | -2.11 |
| join | sweep | 5-16ms | 5-16ms | 59 | 0% | -1.93 |
| join | partial | 0-5ms | 1000-ms | 40 | 0% | +7.50 |
| join | partial | 5-16ms | 5-16ms | 31 | 0% | -7.18 |
| join | partial | 5-16ms | 1000-ms | 20 | 0% | +2.50 |
| join | partial | 5-16ms | ? | 5 | 0% | +6.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 105,035 | 87% | +0.03 |
| join | sweep | — | — | 15,959 | 13% | -0.96 |

touch age >= 200 ms, improves allowed: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 96,927 | 46% | +0.08 |
| join | sweep | 0-5ms | ? | 28,010 | 13% | -0.54 |
| join | partial | 0-5ms | ? | 24,133 | 11% | -0.24 |
| join | partial | 200-1000ms | 200-1000ms | 20,427 | 10% | +0.08 |
| join | partial | 1000-ms | ? | 11,639 | 5% | -0.06 |
| improve | sweep | 200-1000ms | ? | 7,526 | 4% | +0.01 |
| improve | sweep | 50-200ms | ? | 3,951 | 2% | +0.11 |
| improve | sweep | 0-5ms | ? | 2,642 | 1% | -0.09 |
| improve | sweep | 1000-ms | ? | 2,637 | 1% | -0.01 |
| join | partial | 200-1000ms | 1000-ms | 2,553 | 1% | +0.21 |
| join | sweep | 5-16ms | ? | 2,308 | 1% | -1.77 |
| join | sweep | 200-1000ms | 200-1000ms | 2,055 | 1% | -0.37 |
| improve | sweep | 16-50ms | ? | 1,447 | 1% | +0.05 |
| join | sweep | 1000-ms | 1000-ms | 1,381 | 1% | -1.61 |
| join | partial | 200-1000ms | ? | 936 | 0% | +1.21 |
| join | partial | 0-5ms | 0-5ms | 554 | 0% | -0.90 |
| improve | partial | 0-5ms | 0-5ms | 397 | 0% | -0.18 |
| join | sweep | 0-5ms | 0-5ms | 339 | 0% | -0.35 |
| improve | partial | 0-5ms | ? | 316 | 0% | +0.41 |
| improve | partial | 5-16ms | 5-16ms | 298 | 0% | +0.30 |
| join | sweep | 200-1000ms | 1000-ms | 238 | 0% | -0.61 |
| join | sweep | 16-50ms | ? | 225 | 0% | +1.20 |
| join | sweep | 1000-ms | ? | 177 | 0% | -0.84 |
| join | sweep | 5-16ms | 5-16ms | 98 | 0% | -1.19 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 157,336 | 74% | +0.02 |
| join | sweep | — | — | 35,020 | 17% | -0.64 |
| improve | sweep | — | — | 18,377 | 9% | +0.01 |
| improve | partial | — | — | 1,031 | 0% | +0.20 |

touch age >= 200 ms + depth gate: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 91,055 | 57% | +0.17 |
| join | partial | 0-5ms | ? | 19,500 | 12% | -0.09 |
| join | partial | 200-1000ms | 200-1000ms | 15,373 | 10% | +0.12 |
| join | sweep | 0-5ms | ? | 12,897 | 8% | -0.72 |
| join | partial | 1000-ms | ? | 12,048 | 8% | -0.01 |
| join | partial | 200-1000ms | 1000-ms | 2,651 | 2% | -0.62 |
| join | sweep | 200-1000ms | 200-1000ms | 1,128 | 1% | -0.92 |
| join | sweep | 5-16ms | ? | 965 | 1% | -2.31 |
| join | partial | 200-1000ms | ? | 919 | 1% | +1.41 |
| join | sweep | 1000-ms | 1000-ms | 727 | 0% | -1.21 |
| join | partial | 0-5ms | 0-5ms | 458 | 0% | -0.89 |
| join | sweep | 0-5ms | 0-5ms | 247 | 0% | +0.68 |
| join | sweep | 200-1000ms | 1000-ms | 145 | 0% | -0.12 |
| join | partial | 0-5ms | 1000-ms | 94 | 0% | +1.54 |
| join | sweep | 200-1000ms | ? | 82 | 0% | -2.87 |
| join | sweep | 1000-ms | ? | 81 | 0% | -2.09 |
| join | sweep | 5-16ms | 5-16ms | 59 | 0% | -0.28 |
| join | partial | 5-16ms | 5-16ms | 41 | 0% | +1.52 |
| join | partial | 0-5ms | 200-1000ms | 20 | 0% | -4.85 |
| join | partial | 5-16ms | ? | 5 | 0% | +6.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 142,164 | 90% | +0.10 |
| join | sweep | — | — | 16,332 | 10% | -0.84 |

touch age >= 200 ms, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 27,595 | 50% | +0.06 |
| join | sweep | 0-5ms | ? | 7,821 | 14% | -0.54 |
| join | partial | 0-5ms | ? | 6,822 | 12% | -0.22 |
| join | partial | 200-1000ms | 200-1000ms | 6,329 | 12% | +0.21 |
| join | partial | 1000-ms | ? | 3,268 | 6% | -0.13 |
| join | partial | 200-1000ms | 1000-ms | 788 | 1% | +0.05 |
| join | sweep | 200-1000ms | 200-1000ms | 553 | 1% | -0.35 |
| join | sweep | 5-16ms | ? | 484 | 1% | -1.41 |
| join | sweep | 1000-ms | 1000-ms | 347 | 1% | -1.66 |
| join | partial | 200-1000ms | ? | 285 | 1% | +1.23 |
| join | partial | 0-5ms | 0-5ms | 140 | 0% | -0.21 |
| join | sweep | 0-5ms | 0-5ms | 88 | 0% | -0.24 |
| join | sweep | 200-1000ms | 1000-ms | 84 | 0% | -0.65 |
| join | sweep | 1000-ms | ? | 52 | 0% | -1.21 |
| join | partial | 5-16ms | 5-16ms | 26 | 0% | -1.44 |
| join | partial | 0-5ms | 1000-ms | 25 | 0% | +1.94 |
| join | sweep | 200-1000ms | ? | 25 | 0% | -2.14 |
| join | sweep | 5-16ms | 5-16ms | 14 | 0% | -0.49 |
| join | partial | 5-16ms | 1000-ms | 10 | 0% | +1.48 |
| join | partial | 5-16ms | ? | 5 | 0% | +6.43 |
| join | partial | 0-5ms | 200-1000ms | 5 | 0% | -4.85 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 45,298 | 83% | +0.03 |
| join | sweep | — | — | 9,467 | 17% | -0.62 |

touch age >= 200 ms, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 44,785 | 39% | -0.80 |
| join | partial | 1000-ms | 1000-ms | 31,281 | 27% | +0.49 |
| join | partial | 0-5ms | ? | 13,132 | 12% | -0.03 |
| join | partial | 200-1000ms | 200-1000ms | 8,396 | 7% | +0.05 |
| join | partial | 1000-ms | ? | 3,673 | 3% | -0.10 |
| join | sweep | 1000-ms | 1000-ms | 3,285 | 3% | -1.38 |
| join | sweep | 200-1000ms | 200-1000ms | 2,641 | 2% | -0.82 |
| join | sweep | 5-16ms | ? | 2,548 | 2% | -1.22 |
| join | partial | 200-1000ms | 1000-ms | 1,701 | 1% | +0.45 |
| join | sweep | 0-5ms | 0-5ms | 446 | 0% | -0.29 |
| join | sweep | 200-1000ms | 1000-ms | 432 | 0% | -0.68 |
| join | partial | 200-1000ms | ? | 423 | 0% | -0.55 |
| join | sweep | 1000-ms | ? | 362 | 0% | -0.25 |
| join | partial | 0-5ms | 0-5ms | 344 | 0% | +0.79 |
| join | sweep | 200-1000ms | ? | 123 | 0% | -4.65 |
| join | partial | 0-5ms | 1000-ms | 95 | 0% | +3.47 |
| join | sweep | 5-16ms | 5-16ms | 88 | 0% | -2.15 |
| join | partial | 5-16ms | 5-16ms | 45 | 0% | +0.20 |
| join | partial | 0-5ms | 200-1000ms | 20 | 0% | -4.85 |
| join | partial | 5-16ms | 1000-ms | 20 | 0% | +0.45 |
| join | partial | 5-16ms | ? | 0 | 0% | -0.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 59,130 | 52% | +0.27 |
| join | sweep | — | — | 54,709 | 48% | -0.86 |