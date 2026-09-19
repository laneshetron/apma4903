# Quoter simulation, KXETH15M, 2026-09-17

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner (baseline, no join tables) | 88 | -471.10 | 460.01 | -921.53 | -905.52 | 88 | -471.10 | 460.01 | -921.53 | -469.53 | -1.57 | -5.35 | 3.40 | -14.79 | -14.09 | 169,128 | -0.28 | -0.27 | 47.17 | 2.04 | 23,991 | 19.79 | 0.00 | 10.43 |
|  ↳ vetoes: {'priority_fills': 12932, 'greeks': 3405626} |
| join only, never improve | 88 | -300.53 | 537.47 | -829.00 | -843.34 | 88 | -300.53 | 537.47 | -829.00 | -287.99 | -12.54 | -3.42 | 3.92 | -8.16 | -12.51 | 129,885 | -0.23 | -0.22 | 0.00 | 1.57 | 18,356 | 19.79 | 0.00 | 9.69 |
|  ↳ vetoes: {'priority_fills': 7199, 'greeks': 3405626} |
| improve only, never join | 88 | -138.47 | 14.83 | -144.22 | -122.87 | 88 | -138.47 | 14.83 | -144.22 | -120.50 | -17.97 | -1.57 | 3.31 | -4.46 | -8.11 | 53,347 | -0.26 | -0.24 | 100.00 | 0.64 | 7,903 | 19.31 | 0.00 | 10.10 |
|  ↳ vetoes: {'join_disallowed': 4176726, 'priority_fills': 7706, 'greeks': 3405626} |
| pre-position 1 tick behind | 88 | -39.33 | 375.40 | -405.79 | -392.98 | 88 | -39.33 | 375.40 | -405.79 | -17.14 | -22.19 | -0.45 | 3.92 | -1.07 | -12.26 | 42,824 | -0.09 | -0.09 | 0.00 | 0.52 | 6,176 | 19.32 | 0.00 | 10.14 |
|  ↳ vetoes: {'priority_fills': 3815, 'greeks': 3405626} |
| persistence: min rest 1 s, reprice >= 2 ticks | 88 | -584.89 | 296.14 | -871.17 | -841.48 | 88 | -584.89 | 296.14 | -871.17 | -576.27 | -8.62 | -6.65 | 3.57 | -17.47 | -16.01 | 164,506 | -0.36 | -0.33 | 50.22 | 1.98 | 23,588 | 19.82 | 0.00 | 10.70 |
|  ↳ vetoes: {'held_young': 1066020, 'priority_fills': 13634, 'greeks': 3405626} |

touch joiner (baseline, no join tables): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 28,487 | 17% | -0.98 |
| join | partial | 0-5ms | ? | 22,883 | 14% | -0.16 |
| improve | sweep | 0-5ms | ? | 20,678 | 12% | -0.19 |
| join | partial | 1000-ms | 1000-ms | 19,244 | 11% | +0.09 |
| improve | sweep | 1000-ms | ? | 12,754 | 8% | -0.26 |
| improve | partial | 0-5ms | ? | 10,902 | 6% | -0.21 |
| improve | sweep | 200-1000ms | ? | 9,778 | 6% | -0.10 |
| improve | partial | 200-1000ms | 200-1000ms | 7,497 | 4% | +0.10 |
| improve | partial | 1000-ms | 1000-ms | 6,431 | 4% | +0.05 |
| join | partial | 200-1000ms | 200-1000ms | 5,079 | 3% | +0.77 |
| improve | sweep | 50-200ms | ? | 4,959 | 3% | -0.24 |
| improve | partial | 50-200ms | 50-200ms | 2,363 | 1% | -0.41 |
| join | sweep | 200-1000ms | ? | 2,118 | 1% | +0.97 |
| join | partial | 1000-ms | ? | 1,939 | 1% | -0.78 |
| join | sweep | 50-200ms | ? | 1,612 | 1% | -0.24 |
| join | sweep | 5-16ms | ? | 1,541 | 1% | -1.31 |
| improve | sweep | 16-50ms | ? | 1,511 | 1% | -0.07 |
| join | partial | 200-1000ms | 1000-ms | 1,349 | 1% | -0.56 |
| join | sweep | 1000-ms | 1000-ms | 1,008 | 1% | -2.26 |
| join | partial | 50-200ms | 50-200ms | 850 | 1% | +1.02 |
| join | sweep | 1000-ms | ? | 704 | 0% | -1.86 |
| improve | partial | 16-50ms | 16-50ms | 649 | 0% | -0.93 |
| improve | partial | 5-16ms | 5-16ms | 648 | 0% | +1.49 |
| join | sweep | 16-50ms | ? | 645 | 0% | +0.58 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 52,164 | 31% | -0.01 |
| improve | sweep | — | — | 50,834 | 30% | -0.22 |
| join | sweep | — | — | 37,335 | 22% | -0.87 |
| improve | partial | — | — | 28,795 | 17% | -0.04 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 43,395 | 33% | -0.54 |
| join | partial | 0-5ms | ? | 35,908 | 28% | -0.06 |
| join | partial | 1000-ms | 1000-ms | 30,831 | 24% | +0.23 |
| join | partial | 200-1000ms | 200-1000ms | 7,385 | 6% | +0.18 |
| join | partial | 1000-ms | ? | 2,502 | 2% | -0.85 |
| join | partial | 200-1000ms | 1000-ms | 1,967 | 2% | -0.78 |
| join | sweep | 200-1000ms | 200-1000ms | 1,597 | 1% | -0.44 |
| join | sweep | 1000-ms | 1000-ms | 1,266 | 1% | -2.58 |
| join | sweep | 5-16ms | ? | 1,162 | 1% | -1.35 |
| join | sweep | 50-200ms | 50-200ms | 841 | 1% | -0.04 |
| join | partial | 50-200ms | 50-200ms | 795 | 1% | -0.06 |
| join | partial | 200-1000ms | ? | 487 | 0% | -0.25 |
| join | sweep | 200-1000ms | 1000-ms | 275 | 0% | -5.26 |
| join | sweep | 50-200ms | 1000-ms | 196 | 0% | +1.74 |
| join | sweep | 1000-ms | ? | 195 | 0% | -3.78 |
| join | sweep | 200-1000ms | ? | 117 | 0% | +0.83 |
| join | partial | 50-200ms | 200-1000ms | 113 | 0% | +3.40 |
| join | sweep | 50-200ms | 200-1000ms | 106 | 0% | -0.83 |
| join | partial | 50-200ms | 1000-ms | 102 | 0% | +1.23 |
| join | sweep | 16-50ms | 1000-ms | 88 | 0% | -1.64 |
| join | partial | 16-50ms | 16-50ms | 82 | 0% | -2.97 |
| join | sweep | 0-5ms | 0-5ms | 63 | 0% | +6.20 |
| join | partial | 0-5ms | 1000-ms | 57 | 0% | +3.92 |
| join | sweep | 16-50ms | 16-50ms | 41 | 0% | -5.18 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 80,437 | 62% | +0.02 |
| join | sweep | — | — | 49,448 | 38% | -0.62 |

improve only, never join: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 17,397 | 33% | -0.35 |
| improve | sweep | 200-1000ms | ? | 12,722 | 24% | +0.05 |
| improve | sweep | 1000-ms | ? | 11,371 | 21% | -0.49 |
| improve | sweep | 50-200ms | ? | 7,757 | 15% | -0.09 |
| improve | sweep | 16-50ms | ? | 2,227 | 4% | -0.75 |
| improve | partial | 5-16ms | 5-16ms | 621 | 1% | +1.08 |
| improve | partial | 0-5ms | ? | 491 | 1% | +0.38 |
| improve | partial | 0-5ms | 0-5ms | 438 | 1% | +0.61 |
| improve | sweep | 5-16ms | ? | 257 | 0% | -2.78 |
| improve | sweep | 0-5ms | 0-5ms | 35 | 0% | -1.01 |
| improve | sweep | 5-16ms | 5-16ms | 14 | 0% | -1.97 |
| improve | partial | 0-5ms | 5-16ms | 8 | 0% | +2.70 |
| improve | sweep | 0-5ms | 5-16ms | 3 | 0% | +2.70 |
| improve | partial | 200-1000ms | ? | 3 | 0% | +5.50 |
| improve | partial | 50-200ms | ? | 2 | 0% | +0.15 |
| improve | partial | 5-16ms | ? | 1 | 0% | -2.90 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 51,783 | 97% | -0.27 |
| improve | partial | — | — | 1,564 | 3% | +0.74 |

pre-position 1 tick behind: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 19,305 | 45% | -0.35 |
| join | partial | 0-5ms | ? | 11,239 | 26% | -0.04 |
| join | partial | 0-5ms | 1000-ms | 6,166 | 14% | +0.92 |
| join | partial | 1000-ms | 1000-ms | 1,001 | 2% | +1.19 |
| join | partial | 0-5ms | 200-1000ms | 708 | 2% | +0.28 |
| join | sweep | 5-16ms | ? | 396 | 1% | -1.74 |
| join | sweep | 200-1000ms | 1000-ms | 394 | 1% | -1.54 |
| join | sweep | 200-1000ms | 200-1000ms | 363 | 1% | -1.03 |
| join | sweep | 200-1000ms | ? | 349 | 1% | +0.92 |
| join | sweep | 1000-ms | ? | 278 | 1% | +0.48 |
| join | partial | 5-16ms | 1000-ms | 241 | 1% | -1.43 |
| join | sweep | 1000-ms | 1000-ms | 229 | 1% | -1.69 |
| join | partial | 1000-ms | ? | 222 | 1% | -5.89 |
| join | sweep | 50-200ms | 1000-ms | 174 | 0% | +1.51 |
| join | sweep | 50-200ms | 200-1000ms | 171 | 0% | -0.73 |
| join | sweep | 50-200ms | 50-200ms | 165 | 0% | +4.80 |
| join | sweep | 50-200ms | ? | 157 | 0% | +0.04 |
| join | sweep | 5-16ms | 1000-ms | 132 | 0% | -4.40 |
| join | partial | 200-1000ms | 1000-ms | 131 | 0% | +2.26 |
| join | partial | 0-5ms | 50-200ms | 119 | 0% | +1.20 |
| join | partial | 200-1000ms | 200-1000ms | 114 | 0% | -0.71 |
| join | sweep | 0-5ms | 1000-ms | 107 | 0% | -4.11 |
| join | sweep | 0-5ms | 200-1000ms | 70 | 0% | +2.22 |
| join | sweep | 16-50ms | 200-1000ms | 60 | 0% | +1.80 |
| **by kind/class** | | | | | | |
| join | sweep | — | — | 22,502 | 53% | -0.38 |
| join | partial | — | — | 20,322 | 47% | +0.24 |

persistence: min rest 1 s, reprice >= 2 ticks: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 21,908 | 13% | -0.65 |
| join | sweep | 0-5ms | ? | 21,277 | 13% | -0.62 |
| join | partial | 0-5ms | ? | 17,915 | 11% | -0.08 |
| improve | sweep | 1000-ms | ? | 14,897 | 9% | -0.65 |
| join | partial | 1000-ms | 1000-ms | 14,250 | 9% | +0.56 |
| improve | partial | 0-5ms | ? | 11,934 | 7% | -0.26 |
| improve | sweep | 200-1000ms | ? | 8,715 | 5% | -0.56 |
| improve | partial | 1000-ms | 1000-ms | 6,448 | 4% | +0.57 |
| join | sweep | 200-1000ms | ? | 6,111 | 4% | -1.13 |
| improve | partial | 200-1000ms | 200-1000ms | 5,884 | 4% | +0.35 |
| join | sweep | 1000-ms | ? | 5,606 | 3% | -2.14 |
| improve | sweep | 50-200ms | ? | 3,695 | 2% | -0.03 |
| join | partial | 200-1000ms | 200-1000ms | 3,282 | 2% | +0.63 |
| join | sweep | 50-200ms | ? | 2,648 | 2% | -0.06 |
| join | partial | 0-5ms | 1000-ms | 2,231 | 1% | +0.18 |
| improve | partial | 50-200ms | 50-200ms | 1,772 | 1% | +0.30 |
| join | partial | 200-1000ms | 1000-ms | 1,767 | 1% | +0.72 |
| join | partial | 1000-ms | ? | 1,419 | 1% | -0.62 |
| improve | sweep | 16-50ms | ? | 1,179 | 1% | -0.82 |
| join | sweep | 16-50ms | ? | 1,066 | 1% | -1.43 |
| join | sweep | 5-16ms | ? | 914 | 1% | -0.69 |
| improve | partial | 0-5ms | 1000-ms | 868 | 1% | +1.06 |
| join | sweep | 1000-ms | 1000-ms | 809 | 0% | -1.22 |
| improve | partial | 200-1000ms | 1000-ms | 778 | 0% | +2.08 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 51,845 | 32% | -0.63 |
| join | partial | — | — | 43,286 | 26% | +0.18 |
| join | sweep | — | — | 39,098 | 24% | -0.93 |
| improve | partial | — | — | 30,277 | 18% | +0.25 |