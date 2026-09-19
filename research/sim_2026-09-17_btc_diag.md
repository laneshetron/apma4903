# Quoter simulation, KXBTC15M, 2026-09-17

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner (baseline, no join tables) | 88 | -213.92 | 794.19 | -998.99 | -942.43 | 88 | -213.92 | 794.19 | -998.99 | -212.49 | -1.43 | -2.43 | 4.44 | -5.13 | -13.53 | 261,421 | -0.08 | -0.06 | 15.06 | 0.13 | 25,564 | 19.90 | 0.00 | 10.49 |
|  ↳ vetoes: {'priority_fills': 6534, 'greeks': 14210722} |
| join only, never improve | 88 | -186.52 | 804.36 | -982.27 | -927.28 | 88 | -186.52 | 804.36 | -982.27 | -178.86 | -7.66 | -2.12 | 4.33 | -4.59 | -12.99 | 248,873 | -0.07 | -0.07 | 0.00 | 0.12 | 23,364 | 19.91 | 0.00 | 10.15 |
|  ↳ vetoes: {'priority_fills': 4629, 'greeks': 14210722} |
| improve only, never join | 88 | -23.43 | -3.71 | -12.46 | -19.89 | 88 | -23.43 | -3.71 | -12.46 | -19.06 | -4.38 | -0.27 | 3.51 | -0.71 | -9.30 | 22,067 | -0.11 | -0.10 | 100.00 | 0.01 | 2,392 | 12.83 | 0.00 | 8.60 |
|  ↳ vetoes: {'join_disallowed': 25626912, 'priority_fills': 2294, 'greeks': 14210722} |
| pre-position 1 tick behind | 88 | -215.26 | 235.77 | -440.09 | -368.40 | 88 | -215.26 | 235.77 | -440.09 | -147.43 | -67.83 | -2.45 | 5.39 | -4.26 | -20.51 | 40,834 | -0.53 | -0.29 | 0.00 | 0.02 | 3,519 | 19.10 | 0.00 | 12.55 |
|  ↳ vetoes: {'priority_fills': 1667, 'greeks': 14210722} |
| persistence: min rest 1 s, reprice >= 2 ticks | 88 | -320.15 | 570.39 | -879.32 | -788.69 | 88 | -320.15 | 570.39 | -879.32 | -287.03 | -33.12 | -3.64 | 4.39 | -7.77 | -17.20 | 233,600 | -0.14 | -0.10 | 18.79 | 0.11 | 24,160 | 19.80 | 0.00 | 12.90 |
|  ↳ vetoes: {'priority_fills': 9353, 'held_young': 1793302, 'greeks': 14210722} |

touch joiner (baseline, no join tables): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

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

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 105,800 | 43% | +0.10 |
| join | partial | 200-1000ms | 200-1000ms | 43,547 | 17% | +0.21 |
| join | sweep | 0-5ms | ? | 34,854 | 14% | -0.51 |
| join | partial | 0-5ms | ? | 30,662 | 12% | -0.14 |
| join | partial | 1000-ms | ? | 13,360 | 5% | -0.11 |
| join | partial | 200-1000ms | 1000-ms | 4,890 | 2% | -0.22 |
| join | partial | 50-200ms | 50-200ms | 4,267 | 2% | -0.13 |
| join | sweep | 5-16ms | ? | 2,349 | 1% | -1.90 |
| join | partial | 200-1000ms | ? | 1,729 | 1% | +0.90 |
| join | sweep | 200-1000ms | 200-1000ms | 1,514 | 1% | -0.63 |
| join | sweep | 1000-ms | 1000-ms | 1,359 | 1% | -0.58 |
| join | sweep | 50-200ms | 50-200ms | 966 | 0% | -2.35 |
| join | partial | 0-5ms | 0-5ms | 602 | 0% | -1.09 |
| join | partial | 50-200ms | 1000-ms | 461 | 0% | +0.22 |
| join | sweep | 0-5ms | 0-5ms | 408 | 0% | -0.95 |
| join | partial | 16-50ms | 16-50ms | 309 | 0% | -1.10 |
| join | sweep | 200-1000ms | 1000-ms | 257 | 0% | -1.83 |
| join | partial | 50-200ms | 200-1000ms | 240 | 0% | +0.14 |
| join | sweep | 1000-ms | ? | 197 | 0% | -1.59 |
| join | sweep | 16-50ms | 16-50ms | 168 | 0% | +1.22 |
| join | sweep | 50-200ms | 1000-ms | 130 | 0% | -3.12 |
| join | sweep | 50-200ms | 200-1000ms | 121 | 0% | +1.62 |
| join | partial | 0-5ms | 1000-ms | 112 | 0% | +1.84 |
| join | partial | 5-16ms | 5-16ms | 85 | 0% | -2.30 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 206,323 | 83% | +0.06 |
| join | sweep | — | — | 42,550 | 17% | -0.67 |

improve only, never join: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 200-1000ms | ? | 7,342 | 33% | +0.04 |
| improve | sweep | 50-200ms | ? | 4,657 | 21% | +0.08 |
| improve | sweep | 0-5ms | ? | 3,974 | 18% | -0.45 |
| improve | sweep | 16-50ms | ? | 2,463 | 11% | +0.01 |
| improve | sweep | 1000-ms | ? | 2,082 | 9% | -0.17 |
| improve | partial | 0-5ms | 0-5ms | 494 | 2% | +0.15 |
| improve | sweep | 5-16ms | ? | 335 | 2% | -2.28 |
| improve | partial | 5-16ms | 5-16ms | 325 | 1% | -0.64 |
| improve | partial | 0-5ms | ? | 268 | 1% | +0.30 |
| improve | sweep | 0-5ms | 0-5ms | 95 | 0% | +0.15 |
| improve | partial | 5-16ms | ? | 20 | 0% | +2.85 |
| improve | sweep | 5-16ms | 5-16ms | 12 | 0% | -3.25 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 20,960 | 95% | -0.10 |
| improve | partial | — | — | 1,107 | 5% | +0.00 |

pre-position 1 tick behind: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 12,951 | 32% | -0.65 |
| join | partial | 0-5ms | ? | 9,916 | 24% | -0.55 |
| join | partial | 0-5ms | 1000-ms | 8,070 | 20% | +0.62 |
| join | partial | 1000-ms | 1000-ms | 2,003 | 5% | -0.45 |
| join | partial | 0-5ms | 200-1000ms | 1,651 | 4% | +0.20 |
| join | partial | 0-5ms | 50-200ms | 575 | 1% | -0.07 |
| join | partial | 5-16ms | 1000-ms | 531 | 1% | -1.97 |
| join | partial | 200-1000ms | 1000-ms | 508 | 1% | -1.38 |
| join | partial | 200-1000ms | 200-1000ms | 429 | 1% | -2.21 |
| join | sweep | 5-16ms | ? | 386 | 1% | -0.72 |
| join | sweep | 200-1000ms | 1000-ms | 300 | 1% | -0.81 |
| join | sweep | 200-1000ms | 200-1000ms | 250 | 1% | -0.53 |
| join | partial | 0-5ms | 0-5ms | 246 | 1% | +0.43 |
| join | sweep | 0-5ms | 1000-ms | 223 | 1% | -2.52 |
| join | sweep | 200-1000ms | ? | 220 | 1% | -0.10 |
| join | partial | 1000-ms | ? | 191 | 0% | +1.57 |
| join | sweep | 50-200ms | 1000-ms | 175 | 0% | +1.15 |
| join | sweep | 1000-ms | ? | 175 | 0% | +1.81 |
| join | sweep | 50-200ms | ? | 170 | 0% | -0.67 |
| join | sweep | 50-200ms | 200-1000ms | 164 | 0% | +1.50 |
| join | partial | 0-5ms | 16-50ms | 160 | 0% | -0.47 |
| join | sweep | 50-200ms | 50-200ms | 129 | 0% | +0.64 |
| join | partial | 0-5ms | 5-16ms | 125 | 0% | +1.47 |
| join | sweep | 1000-ms | 1000-ms | 124 | 0% | +0.13 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 24,912 | 61% | -0.13 |
| join | sweep | — | — | 15,921 | 39% | -0.55 |

persistence: min rest 1 s, reprice >= 2 ticks: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 70,665 | 30% | +0.13 |
| join | sweep | 0-5ms | ? | 26,291 | 11% | -0.43 |
| join | partial | 0-5ms | ? | 21,983 | 9% | -0.21 |
| join | partial | 200-1000ms | 200-1000ms | 17,587 | 8% | -0.03 |
| improve | sweep | 200-1000ms | ? | 10,703 | 5% | +0.13 |
| join | partial | 200-1000ms | 1000-ms | 8,340 | 4% | +0.20 |
| join | partial | 1000-ms | ? | 8,294 | 4% | -0.33 |
| join | sweep | 50-200ms | ? | 7,628 | 3% | -0.64 |
| improve | sweep | 1000-ms | ? | 5,681 | 2% | +0.04 |
| join | sweep | 200-1000ms | ? | 5,448 | 2% | -0.11 |
| join | partial | 0-5ms | 1000-ms | 5,184 | 2% | +0.73 |
| improve | sweep | 0-5ms | ? | 4,692 | 2% | -0.23 |
| improve | partial | 200-1000ms | 200-1000ms | 4,120 | 2% | +0.43 |
| join | sweep | 16-50ms | ? | 3,787 | 2% | -0.73 |
| improve | sweep | 50-200ms | ? | 3,447 | 1% | +0.12 |
| improve | partial | 1000-ms | 1000-ms | 2,643 | 1% | -0.56 |
| improve | partial | 0-5ms | ? | 2,502 | 1% | +0.68 |
| join | sweep | 5-16ms | ? | 2,416 | 1% | -1.69 |
| improve | partial | 50-200ms | 50-200ms | 2,412 | 1% | +0.08 |
| join | partial | 50-200ms | 50-200ms | 2,335 | 1% | -0.63 |
| join | partial | 50-200ms | 1000-ms | 2,288 | 1% | -0.91 |
| join | partial | 200-1000ms | ? | 1,520 | 1% | +0.90 |
| join | sweep | 1000-ms | 1000-ms | 1,192 | 1% | -1.07 |
| improve | partial | 16-50ms | 16-50ms | 1,040 | 0% | -0.17 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 142,629 | 61% | +0.01 |
| join | sweep | — | — | 49,440 | 21% | -0.54 |
| improve | sweep | — | — | 25,929 | 11% | +0.01 |
| improve | partial | — | — | 15,601 | 7% | +0.05 |