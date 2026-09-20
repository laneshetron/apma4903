# Quoter simulation, KXEPLTOTAL, 2026-09-20

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner (baseline) | 23 | -96.73 | 347.48 | -444.21 | -451.70 | 23 | -96.73 | 347.48 | -444.21 | -46.79 | -49.94 | -4.21 | 5.17 | -3.90 | -16.50 | 31,027 | -0.31 | -0.30 | 75.58 | 1.27 | 3,083 | 19.54 | 9.71 | 0.19 |
|  ↳ vetoes: {'priority_fills': 1895} |
| no improve when spread > 2 ticks | 23 | -18.94 | 297.43 | -316.36 | -324.16 | 23 | -18.94 | 297.43 | -316.36 | 30.14 | -49.08 | -0.82 | 4.55 | -0.87 | -9.03 | 27,358 | -0.07 | -0.05 | 44.35 | 1.12 | 2,568 | 19.53 | 9.68 | 0.29 |
|  ↳ vetoes: {'priority_fills': 1059, 'wide_no_improve': 1341128} |
| no improve when spread > 1 tick (join only) | 23 | -24.26 | 311.74 | -335.99 | -315.80 | 23 | -24.26 | 311.74 | -335.99 | 18.45 | -42.71 | -1.05 | 3.54 | -1.43 | -8.70 | 22,445 | -0.11 | -0.03 | 0.00 | 0.92 | 2,234 | 19.69 | 10.85 | 0.20 |
|  ↳ vetoes: {'priority_fills': 695} |
| pull when spread > 3 ticks | 23 | -67.83 | 89.28 | -157.11 | -159.57 | 23 | -67.83 | 89.28 | -157.11 | -31.90 | -35.93 | -2.95 | 4.30 | -3.29 | -12.39 | 24,334 | -0.28 | -0.22 | 63.92 | 1.00 | 2,231 | 19.37 | 7.34 | 0.19 |
|  ↳ vetoes: {'priority_fills': 1085, 'wide_spread': 1090498} |
| pull when spread > 2 ticks | 23 | -48.17 | 76.06 | -124.22 | -121.36 | 23 | -48.17 | 76.06 | -124.22 | -1.63 | -46.53 | -2.09 | 4.27 | -2.35 | -15.13 | 21,568 | -0.22 | -0.12 | 56.97 | 0.89 | 1,922 | 19.20 | 8.72 | 0.34 |
|  ↳ vetoes: {'priority_fills': 791, 'wide_spread': 1341128} |
| pause 10 s after a 5c jump | 23 | -51.74 | 134.75 | -186.49 | -192.22 | 23 | -51.74 | 134.75 | -186.49 | -22.69 | -29.05 | -2.25 | 4.07 | -2.65 | -10.90 | 22,871 | -0.23 | -0.24 | 68.39 | 0.94 | 2,145 | 19.36 | 9.33 | 0.23 |
|  ↳ vetoes: {'priority_fills': 1179, 'post_jump': 917360} |
| pause 30 s after a 5c jump | 23 | -25.52 | 91.24 | -116.76 | -115.64 | 23 | -25.52 | 91.24 | -116.76 | -4.07 | -21.45 | -1.11 | 3.89 | -1.37 | -9.10 | 18,441 | -0.14 | -0.04 | 67.18 | 0.76 | 1,691 | 19.31 | 8.87 | 0.13 |
|  ↳ vetoes: {'priority_fills': 882, 'post_jump': 1372694} |
| join only + pause 10 s | 23 | 5.49 | 147.27 | -141.77 | -138.35 | 23 | 5.49 | 147.27 | -141.77 | 40.82 | -35.33 | 0.24 | 3.60 | 0.32 | -8.41 | 16,603 | 0.03 | -0.03 | 0.00 | 0.68 | 1,596 | 19.65 | 11.82 | 0.28 |
|  ↳ vetoes: {'priority_fills': 465, 'post_jump': 917360} |
| pull > 2 ticks + pause 10 s | 23 | -23.96 | 66.31 | -90.27 | -91.83 | 23 | -23.96 | 66.31 | -90.27 | -5.22 | -18.74 | -1.04 | 4.21 | -1.19 | -10.84 | 18,549 | -0.13 | -0.07 | 57.27 | 0.76 | 1,596 | 19.20 | 8.85 | 0.23 |
|  ↳ vetoes: {'priority_fills': 655, 'wide_spread': 1341128, 'post_jump': 917360} |
| pull > 2 ticks + pause 10 s, size 5 | 23 | -12.54 | 18.94 | -31.47 | -25.73 | 23 | -12.54 | 18.94 | -31.47 | -4.81 | -7.72 | -0.55 | 1.43 | -1.82 | -4.27 | 5,295 | -0.24 | -0.08 | 55.04 | 0.22 | 1,261 | 4.90 | 3.06 | 0.09 |
|  ↳ vetoes: {'priority_fills': 461, 'wide_spread': 1341128, 'post_jump': 917360} |

touch joiner (baseline): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 8,200 | 27% | -0.96 |
| improve | partial | 1000-ms | 1000-ms | 5,080 | 16% | +0.38 |
| improve | sweep | 1000-ms | ? | 4,686 | 15% | +0.31 |
| join | partial | 1000-ms | 1000-ms | 3,065 | 10% | +0.07 |
| join | partial | 0-5ms | ? | 2,752 | 9% | +0.14 |
| improve | partial | 0-5ms | ? | 1,745 | 6% | -0.63 |
| join | sweep | 0-5ms | ? | 1,676 | 5% | -0.04 |
| improve | sweep | 200-1000ms | ? | 1,298 | 4% | -1.81 |
| join | sweep | 1000-ms | ? | 485 | 2% | +1.27 |
| improve | sweep | 50-200ms | ? | 471 | 2% | -2.27 |
| improve | partial | 200-1000ms | 200-1000ms | 409 | 1% | -1.59 |
| join | partial | 1000-ms | ? | 378 | 1% | +0.64 |
| improve | sweep | 16-50ms | ? | 151 | 0% | -1.26 |
| improve | partial | 50-200ms | 50-200ms | 125 | 0% | -1.54 |
| join | sweep | 1000-ms | 1000-ms | 108 | 0% | -0.24 |
| join | partial | 200-1000ms | 200-1000ms | 60 | 0% | -1.17 |
| improve | partial | 16-50ms | 16-50ms | 34 | 0% | +0.02 |
| improve | partial | 0-5ms | 0-5ms | 29 | 0% | -1.91 |
| join | sweep | 200-1000ms | ? | 28 | 0% | -9.83 |
| improve | partial | 5-16ms | 5-16ms | 25 | 0% | +0.28 |
| join | sweep | 5-16ms | ? | 20 | 0% | -0.50 |
| join | sweep | 200-1000ms | 1000-ms | 20 | 0% | +0.00 |
| improve | sweep | 5-16ms | ? | 10 | 0% | -3.50 |
| join | sweep | 50-200ms | ? | 3 | 0% | +3.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 14,818 | 48% | -0.68 |
| improve | partial | — | — | 7,446 | 24% | -0.01 |
| join | partial | — | — | 6,255 | 20% | +0.12 |
| join | sweep | — | — | 2,340 | 8% | +0.11 |

no improve when spread > 2 ticks: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 0-5ms | ? | 5,234 | 19% | -0.04 |
| improve | partial | 1000-ms | 1000-ms | 4,562 | 17% | +0.34 |
| join | sweep | 0-5ms | ? | 4,159 | 15% | +0.25 |
| join | partial | 1000-ms | 1000-ms | 3,863 | 14% | +0.23 |
| improve | sweep | 1000-ms | ? | 2,965 | 11% | +0.43 |
| improve | sweep | 0-5ms | ? | 2,104 | 8% | -1.32 |
| improve | partial | 0-5ms | ? | 1,606 | 6% | -0.87 |
| join | sweep | 1000-ms | ? | 456 | 2% | +1.22 |
| improve | partial | 200-1000ms | 200-1000ms | 392 | 1% | -1.70 |
| join | partial | 1000-ms | ? | 379 | 1% | +0.63 |
| improve | sweep | 200-1000ms | ? | 368 | 1% | -0.49 |
| join | partial | 200-1000ms | 200-1000ms | 326 | 1% | -2.01 |
| improve | partial | 50-200ms | 50-200ms | 125 | 0% | -1.54 |
| join | sweep | 1000-ms | 1000-ms | 106 | 0% | -1.01 |
| improve | sweep | 50-200ms | ? | 105 | 0% | -1.57 |
| join | sweep | 200-1000ms | 200-1000ms | 78 | 0% | -2.29 |
| join | partial | 50-200ms | 50-200ms | 68 | 0% | -3.90 |
| improve | partial | 16-50ms | 16-50ms | 35 | 0% | +0.56 |
| improve | partial | 5-16ms | 5-16ms | 35 | 0% | -0.64 |
| join | sweep | 200-1000ms | 1000-ms | 32 | 0% | -8.06 |
| join | sweep | 200-1000ms | ? | 29 | 0% | -9.75 |
| join | sweep | 5-16ms | ? | 27 | 0% | -2.06 |
| improve | sweep | 16-50ms | ? | 25 | 0% | -0.56 |
| improve | partial | 0-5ms | 0-5ms | 20 | 0% | +1.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 9,890 | 36% | +0.04 |
| improve | partial | — | — | 6,775 | 25% | -0.10 |
| improve | sweep | — | — | 5,569 | 21% | -0.34 |
| join | sweep | — | — | 4,905 | 18% | +0.16 |

no improve when spread > 1 tick (join only): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 7,830 | 35% | +0.26 |
| join | partial | 0-5ms | ? | 7,505 | 34% | -0.08 |
| join | sweep | 0-5ms | ? | 5,549 | 25% | -0.19 |
| join | partial | 1000-ms | ? | 540 | 2% | +0.23 |
| join | partial | 200-1000ms | 200-1000ms | 387 | 2% | -3.56 |
| join | sweep | 1000-ms | 1000-ms | 155 | 1% | -0.34 |
| join | sweep | 200-1000ms | 200-1000ms | 155 | 1% | -0.14 |
| join | partial | 50-200ms | 50-200ms | 88 | 0% | -3.35 |
| join | partial | 0-5ms | 1000-ms | 33 | 0% | +13.23 |
| join | partial | 200-1000ms | 1000-ms | 22 | 0% | -1.61 |
| join | sweep | 200-1000ms | 1000-ms | 22 | 0% | -12.41 |
| join | sweep | 1000-ms | ? | 20 | 0% | +17.00 |
| join | sweep | 50-200ms | 50-200ms | 15 | 0% | +4.47 |
| join | sweep | 5-16ms | ? | 7 | 0% | -6.50 |
| join | partial | 200-1000ms | ? | 0 | 0% | +0.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 16,405 | 73% | +0.02 |
| join | sweep | — | — | 5,922 | 27% | -0.18 |

pull when spread > 3 ticks: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | partial | 1000-ms | 1000-ms | 4,406 | 18% | +0.26 |
| improve | sweep | 0-5ms | ? | 3,841 | 16% | -0.96 |
| improve | sweep | 1000-ms | ? | 3,634 | 15% | -0.00 |
| join | partial | 1000-ms | 1000-ms | 3,288 | 14% | +0.16 |
| join | partial | 0-5ms | ? | 3,056 | 13% | +0.25 |
| join | sweep | 0-5ms | ? | 1,927 | 8% | -0.14 |
| improve | partial | 0-5ms | ? | 1,464 | 6% | -1.28 |
| improve | sweep | 200-1000ms | ? | 563 | 2% | -1.33 |
| join | sweep | 1000-ms | ? | 534 | 2% | +0.51 |
| improve | partial | 200-1000ms | 200-1000ms | 399 | 2% | -1.62 |
| join | partial | 1000-ms | ? | 383 | 2% | +0.63 |
| improve | sweep | 50-200ms | ? | 141 | 1% | -1.91 |
| improve | partial | 50-200ms | 50-200ms | 125 | 1% | -1.54 |
| join | sweep | 1000-ms | 1000-ms | 94 | 0% | +1.13 |
| join | partial | 200-1000ms | 200-1000ms | 80 | 0% | -0.75 |
| improve | sweep | 16-50ms | ? | 53 | 0% | -7.85 |
| improve | partial | 16-50ms | 16-50ms | 34 | 0% | -0.09 |
| improve | partial | 5-16ms | 5-16ms | 32 | 0% | -0.78 |
| join | sweep | 200-1000ms | ? | 28 | 0% | -9.83 |
| join | sweep | 5-16ms | ? | 20 | 0% | -0.50 |
| improve | partial | 0-5ms | 0-5ms | 20 | 0% | +1.50 |
| join | sweep | 200-1000ms | 1000-ms | 20 | 0% | -1.50 |
| improve | sweep | 5-16ms | ? | 10 | 0% | -3.50 |
| join | sweep | 50-200ms | ? | 3 | 0% | +3.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 8,244 | 34% | -0.63 |
| join | partial | — | — | 6,808 | 28% | +0.22 |
| improve | partial | — | — | 6,480 | 27% | -0.24 |
| join | sweep | — | — | 2,625 | 11% | -0.07 |

pull when spread > 2 ticks: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | partial | 1000-ms | 1000-ms | 4,060 | 19% | +0.26 |
| join | partial | 1000-ms | 1000-ms | 3,263 | 15% | +0.29 |
| improve | sweep | 1000-ms | ? | 3,071 | 14% | +0.18 |
| join | partial | 0-5ms | ? | 3,056 | 14% | +0.23 |
| improve | sweep | 0-5ms | ? | 2,182 | 10% | -1.58 |
| join | sweep | 0-5ms | ? | 2,059 | 10% | +0.04 |
| improve | partial | 0-5ms | ? | 1,484 | 7% | -0.87 |
| join | sweep | 1000-ms | ? | 490 | 2% | +0.51 |
| join | partial | 1000-ms | ? | 401 | 2% | +0.57 |
| improve | partial | 200-1000ms | 200-1000ms | 389 | 2% | -2.22 |
| improve | sweep | 200-1000ms | ? | 379 | 2% | -0.18 |
| improve | partial | 50-200ms | 50-200ms | 132 | 1% | -1.52 |
| join | partial | 200-1000ms | 200-1000ms | 100 | 0% | -0.50 |
| join | sweep | 1000-ms | 1000-ms | 94 | 0% | +1.13 |
| improve | sweep | 50-200ms | ? | 79 | 0% | -2.04 |
| improve | partial | 5-16ms | 5-16ms | 37 | 0% | -1.01 |
| improve | partial | 16-50ms | 16-50ms | 37 | 0% | +0.08 |
| join | sweep | 200-1000ms | ? | 28 | 0% | -9.83 |
| join | sweep | 5-16ms | ? | 20 | 0% | -0.50 |
| improve | partial | 0-5ms | 0-5ms | 20 | 0% | +1.50 |
| join | sweep | 200-1000ms | 1000-ms | 20 | 0% | -1.50 |
| improve | sweep | 16-50ms | ? | 20 | 0% | +0.50 |
| join | sweep | 50-200ms | ? | 5 | 0% | +1.81 |
| improve | sweep | 5-16ms | ? | 3 | 0% | -0.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 6,821 | 32% | +0.27 |
| improve | partial | — | — | 6,158 | 29% | -0.21 |
| improve | sweep | — | — | 5,737 | 27% | -0.55 |
| join | sweep | — | — | 2,714 | 13% | +0.05 |

pause 10 s after a 5c jump: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 4,486 | 20% | -1.23 |
| improve | partial | 1000-ms | 1000-ms | 3,828 | 17% | +0.39 |
| improve | sweep | 1000-ms | ? | 3,826 | 17% | +0.22 |
| join | partial | 1000-ms | 1000-ms | 2,992 | 13% | +0.07 |
| join | partial | 0-5ms | ? | 2,520 | 11% | +0.47 |
| join | sweep | 0-5ms | ? | 1,572 | 7% | -0.16 |
| improve | partial | 0-5ms | ? | 1,273 | 6% | -1.82 |
| improve | sweep | 200-1000ms | ? | 519 | 2% | -0.68 |
| join | sweep | 1000-ms | ? | 500 | 2% | +0.91 |
| join | partial | 1000-ms | ? | 380 | 2% | +0.40 |
| improve | partial | 200-1000ms | 200-1000ms | 277 | 1% | -3.39 |
| improve | sweep | 50-200ms | ? | 153 | 1% | -0.32 |
| improve | partial | 50-200ms | 50-200ms | 125 | 1% | -1.54 |
| join | partial | 200-1000ms | 200-1000ms | 80 | 0% | -0.75 |
| join | sweep | 1000-ms | 1000-ms | 59 | 0% | +1.44 |
| improve | partial | 5-16ms | 5-16ms | 25 | 0% | -0.28 |
| improve | partial | 16-50ms | 16-50ms | 23 | 0% | -0.17 |
| improve | sweep | 16-50ms | ? | 21 | 0% | -1.52 |
| join | sweep | 5-16ms | ? | 20 | 0% | -0.50 |
| improve | partial | 0-5ms | 0-5ms | 20 | 0% | +1.50 |
| join | sweep | 200-1000ms | 1000-ms | 20 | 0% | +0.00 |
| join | sweep | 200-1000ms | ? | 8 | 0% | -34.50 |
| improve | sweep | 5-16ms | ? | 3 | 0% | -0.50 |
| improve | sweep | 0-5ms | 0-5ms | 2 | 0% | +2.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 9,010 | 40% | -0.57 |
| join | partial | — | — | 5,971 | 26% | +0.25 |
| improve | partial | — | — | 5,572 | 25% | -0.35 |
| join | sweep | — | — | 2,179 | 10% | +0.01 |

pause 30 s after a 5c jump: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 3,355 | 18% | -0.58 |
| improve | partial | 1000-ms | 1000-ms | 3,314 | 18% | +0.38 |
| improve | sweep | 1000-ms | ? | 3,133 | 17% | +0.61 |
| join | partial | 1000-ms | 1000-ms | 2,559 | 14% | +0.13 |
| join | partial | 0-5ms | ? | 2,152 | 12% | +0.22 |
| join | sweep | 0-5ms | ? | 1,062 | 6% | -0.49 |
| improve | partial | 0-5ms | ? | 952 | 5% | -1.74 |
| join | sweep | 1000-ms | ? | 431 | 2% | +1.19 |
| improve | sweep | 200-1000ms | ? | 366 | 2% | -0.73 |
| join | partial | 1000-ms | ? | 358 | 2% | +0.53 |
| improve | partial | 200-1000ms | 200-1000ms | 191 | 1% | -3.89 |
| improve | partial | 50-200ms | 50-200ms | 103 | 1% | -1.02 |
| improve | sweep | 50-200ms | ? | 97 | 1% | -0.87 |
| join | partial | 200-1000ms | 200-1000ms | 70 | 0% | -0.21 |
| join | sweep | 1000-ms | 1000-ms | 59 | 0% | +1.44 |
| improve | partial | 5-16ms | 5-16ms | 22 | 0% | -0.45 |
| improve | partial | 16-50ms | 16-50ms | 21 | 0% | -0.48 |
| join | sweep | 5-16ms | ? | 20 | 0% | -0.50 |
| improve | partial | 0-5ms | 0-5ms | 20 | 0% | +1.50 |
| join | sweep | 200-1000ms | ? | 8 | 0% | -34.50 |
| join | partial | 50-200ms | 50-200ms | 5 | 0% | +2.50 |
| join | sweep | 50-200ms | ? | 3 | 0% | +3.50 |
| improve | sweep | 0-5ms | 0-5ms | 2 | 0% | +2.50 |
| improve | sweep | 16-50ms | ? | 1 | 0% | +3.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 6,954 | 38% | -0.05 |
| join | partial | — | — | 5,145 | 28% | +0.19 |
| improve | partial | — | — | 4,623 | 25% | -0.27 |
| join | sweep | — | — | 1,582 | 9% | -0.12 |

join only + pause 10 s: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 6,361 | 39% | +0.16 |
| join | partial | 0-5ms | ? | 5,360 | 33% | -0.02 |
| join | sweep | 0-5ms | ? | 3,813 | 23% | -0.23 |
| join | partial | 1000-ms | ? | 521 | 3% | +0.29 |
| join | partial | 200-1000ms | 200-1000ms | 167 | 1% | -5.56 |
| join | sweep | 1000-ms | 1000-ms | 101 | 1% | +0.27 |
| join | sweep | 200-1000ms | 200-1000ms | 58 | 0% | -1.33 |
| join | partial | 200-1000ms | 1000-ms | 39 | 0% | +6.26 |
| join | partial | 50-200ms | 50-200ms | 25 | 0% | -0.70 |
| join | sweep | 50-200ms | 50-200ms | 15 | 0% | +4.47 |
| join | partial | 0-5ms | 1000-ms | 13 | 0% | +0.50 |
| join | sweep | 200-1000ms | 1000-ms | 10 | 0% | -1.50 |
| join | sweep | 5-16ms | ? | 3 | 0% | -0.50 |
| join | partial | 200-1000ms | ? | 0 | 0% | +0.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 12,486 | 76% | +0.03 |
| join | sweep | — | — | 3,999 | 24% | -0.22 |

pull > 2 ticks + pause 10 s: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | partial | 1000-ms | 1000-ms | 3,577 | 19% | +0.41 |
| join | partial | 1000-ms | 1000-ms | 2,972 | 16% | +0.24 |
| improve | sweep | 1000-ms | ? | 2,806 | 15% | +0.21 |
| join | partial | 0-5ms | ? | 2,579 | 14% | +0.47 |
| join | sweep | 0-5ms | ? | 1,733 | 9% | +0.29 |
| improve | sweep | 0-5ms | ? | 1,700 | 9% | -1.48 |
| improve | partial | 0-5ms | ? | 1,231 | 7% | -1.56 |
| join | sweep | 1000-ms | ? | 439 | 2% | +0.58 |
| join | partial | 1000-ms | ? | 380 | 2% | +0.40 |
| improve | partial | 200-1000ms | 200-1000ms | 259 | 1% | -3.78 |
| improve | sweep | 200-1000ms | ? | 219 | 1% | -1.59 |
| improve | partial | 50-200ms | 50-200ms | 131 | 1% | -1.48 |
| join | partial | 200-1000ms | 200-1000ms | 100 | 1% | -0.50 |
| improve | sweep | 50-200ms | ? | 75 | 0% | -1.45 |
| join | sweep | 1000-ms | 1000-ms | 65 | 0% | +3.19 |
| join | sweep | 200-1000ms | ? | 28 | 0% | -9.83 |
| improve | partial | 16-50ms | 16-50ms | 26 | 0% | +0.09 |
| improve | partial | 5-16ms | 5-16ms | 23 | 0% | -0.74 |
| join | sweep | 5-16ms | ? | 20 | 0% | -0.50 |
| improve | partial | 0-5ms | 0-5ms | 20 | 0% | +1.50 |
| join | sweep | 200-1000ms | 1000-ms | 20 | 0% | +0.00 |
| join | partial | 50-200ms | 50-200ms | 5 | 0% | +2.50 |
| improve | sweep | 5-16ms | ? | 3 | 0% | -0.50 |
| join | sweep | 50-200ms | ? | 3 | 0% | +3.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 6,036 | 33% | +0.34 |
| improve | partial | — | — | 5,267 | 29% | -0.30 |
| improve | sweep | — | — | 4,807 | 26% | -0.49 |
| join | sweep | — | — | 2,308 | 13% | +0.30 |

pull > 2 ticks + pause 10 s, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | partial | 1000-ms | 1000-ms | 1,022 | 19% | +0.43 |
| improve | sweep | 1000-ms | ? | 846 | 16% | +0.08 |
| join | partial | 1000-ms | 1000-ms | 836 | 16% | +0.46 |
| join | partial | 0-5ms | ? | 794 | 15% | +0.42 |
| join | sweep | 0-5ms | ? | 428 | 8% | +0.12 |
| improve | sweep | 0-5ms | ? | 403 | 8% | -1.26 |
| improve | partial | 0-5ms | ? | 385 | 7% | -1.86 |
| join | partial | 1000-ms | ? | 127 | 2% | +0.42 |
| join | sweep | 1000-ms | ? | 105 | 2% | +0.89 |
| improve | partial | 200-1000ms | 200-1000ms | 87 | 2% | -2.43 |
| improve | sweep | 200-1000ms | ? | 72 | 1% | -1.40 |
| improve | partial | 50-200ms | 50-200ms | 39 | 1% | -2.41 |
| join | partial | 200-1000ms | 200-1000ms | 25 | 0% | -0.50 |
| improve | sweep | 50-200ms | ? | 20 | 0% | -1.38 |
| join | sweep | 1000-ms | 1000-ms | 20 | 0% | -1.75 |
| improve | partial | 16-50ms | 16-50ms | 13 | 0% | -0.19 |
| join | sweep | 200-1000ms | ? | 10 | 0% | -17.50 |
| improve | partial | 5-16ms | 5-16ms | 8 | 0% | -0.25 |
| join | sweep | 5-16ms | ? | 5 | 0% | -0.50 |
| improve | partial | 0-5ms | 0-5ms | 5 | 0% | +1.50 |
| join | sweep | 200-1000ms | 1000-ms | 5 | 0% | +0.00 |
| join | sweep | 50-200ms | ? | 3 | 0% | +3.50 |
| improve | sweep | 5-16ms | ? | 3 | 0% | -0.50 |
| improve | sweep | 0-5ms | 0-5ms | 2 | 0% | +2.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 1,783 | 34% | +0.43 |
| improve | partial | — | — | 1,560 | 30% | -0.37 |
| improve | sweep | — | — | 1,346 | 26% | -0.42 |
| join | sweep | — | — | 576 | 11% | -0.10 |