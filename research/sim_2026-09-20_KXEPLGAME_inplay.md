# Quoter simulation, KXEPLGAME, 2026-09-20

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner (baseline) | 12 | -96.96 | 222.28 | -319.24 | -308.07 | 12 | -96.96 | 222.28 | -319.24 | -66.22 | -30.74 | -8.08 | 6.33 | -4.42 | -18.75 | 51,214 | -0.19 | -0.17 | 46.45 | 0.37 | 4,993 | 19.85 | 10.22 | 0.00 |
|  ↳ vetoes: {'priority_fills': 2323} |
| no improve when spread > 2 ticks | 12 | -75.44 | 224.64 | -300.08 | -292.06 | 12 | -75.44 | 224.64 | -300.08 | -52.22 | -23.21 | -6.29 | 6.16 | -3.53 | -14.00 | 48,964 | -0.15 | -0.13 | 36.62 | 0.35 | 4,678 | 19.92 | 8.29 | 0.00 |
|  ↳ vetoes: {'priority_fills': 1884, 'wide_no_improve': 334562} |
| no improve when spread > 1 tick (join only) | 12 | -43.74 | 261.74 | -305.49 | -319.30 | 12 | -43.74 | 261.74 | -305.49 | -17.84 | -25.90 | -3.65 | 7.08 | -1.78 | -13.80 | 41,824 | -0.10 | -0.13 | 0.00 | 0.30 | 3,963 | 19.97 | 10.49 | 0.00 |
|  ↳ vetoes: {'priority_fills': 1015} |
| pull when spread > 3 ticks | 12 | -110.78 | 187.89 | -298.67 | -286.12 | 12 | -110.78 | 187.89 | -298.67 | -83.59 | -27.20 | -9.23 | 7.23 | -4.42 | -22.19 | 49,735 | -0.22 | -0.19 | 43.94 | 0.36 | 4,793 | 19.91 | 9.90 | 0.00 |
|  ↳ vetoes: {'priority_fills': 2116, 'wide_spread': 160796} |
| pull when spread > 2 ticks | 12 | -117.34 | 174.56 | -291.90 | -275.35 | 12 | -117.34 | 174.56 | -291.90 | -91.41 | -25.93 | -9.78 | 7.24 | -4.68 | -21.41 | 46,943 | -0.25 | -0.21 | 40.39 | 0.34 | 4,454 | 19.87 | 9.26 | 0.00 |
|  ↳ vetoes: {'priority_fills': 1762, 'wide_spread': 334562} |
| pause 10 s after a 5c jump | 12 | -72.54 | 180.66 | -253.20 | -253.40 | 12 | -72.54 | 180.66 | -253.20 | -48.64 | -23.91 | -6.05 | 7.55 | -2.77 | -21.00 | 44,575 | -0.16 | -0.16 | 42.59 | 0.32 | 4,255 | 19.95 | 7.95 | 0.00 |
|  ↳ vetoes: {'priority_fills': 1843, 'post_jump': 332520} |
| pause 30 s after a 5c jump | 12 | -51.82 | 158.33 | -210.15 | -223.16 | 12 | -51.82 | 158.33 | -210.15 | -49.72 | -2.10 | -4.32 | 5.70 | -2.62 | -13.57 | 38,209 | -0.14 | -0.16 | 41.04 | 0.28 | 3,689 | 19.89 | 10.61 | 0.00 |
|  ↳ vetoes: {'priority_fills': 1513, 'post_jump': 548286} |
| join only + pause 10 s | 12 | -35.88 | 212.80 | -248.68 | -255.21 | 12 | -35.88 | 212.80 | -248.68 | -17.55 | -18.33 | -2.99 | 6.56 | -1.58 | -14.39 | 37,060 | -0.10 | -0.10 | 0.00 | 0.27 | 3,486 | 19.69 | 8.34 | 0.00 |
|  ↳ vetoes: {'priority_fills': 820, 'post_jump': 332520} |
| pull > 2 ticks + pause 10 s | 12 | -70.99 | 162.56 | -233.54 | -230.77 | 12 | -70.99 | 162.56 | -233.54 | -51.06 | -19.93 | -5.92 | 6.18 | -3.32 | -16.20 | 42,428 | -0.17 | -0.16 | 38.70 | 0.31 | 3,982 | 19.90 | 6.86 | 0.00 |
|  ↳ vetoes: {'priority_fills': 1547, 'wide_spread': 334562, 'post_jump': 332520} |
| pull > 2 ticks + pause 10 s, size 5 | 12 | -18.69 | 45.08 | -63.77 | -64.00 | 12 | -18.69 | 45.08 | -63.77 | -11.70 | -6.99 | -1.56 | 1.27 | -4.26 | -3.47 | 12,124 | -0.15 | -0.16 | 39.20 | 0.09 | 3,240 | 5.00 | 2.74 | 0.00 |
|  ↳ vetoes: {'priority_fills': 1169, 'wide_spread': 334562, 'post_jump': 332520} |

touch joiner (baseline): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 12,858 | 25% | +0.36 |
| join | partial | 0-5ms | ? | 8,096 | 16% | -0.56 |
| improve | sweep | 0-5ms | ? | 5,245 | 10% | -1.12 |
| improve | sweep | 1000-ms | ? | 4,739 | 9% | -0.18 |
| join | sweep | 0-5ms | ? | 4,510 | 9% | -0.40 |
| improve | partial | 0-5ms | ? | 2,842 | 6% | -0.86 |
| improve | sweep | 200-1000ms | ? | 2,826 | 6% | -0.42 |
| improve | partial | 1000-ms | 1000-ms | 2,478 | 5% | +0.17 |
| improve | partial | 200-1000ms | 200-1000ms | 1,360 | 3% | +0.60 |
| improve | sweep | 50-200ms | ? | 1,333 | 3% | +0.53 |
| join | partial | 1000-ms | ? | 1,283 | 3% | +0.33 |
| join | partial | 200-1000ms | 200-1000ms | 581 | 1% | -0.04 |
| improve | sweep | 16-50ms | ? | 479 | 1% | +2.32 |
| improve | partial | 50-200ms | 50-200ms | 460 | 1% | -0.21 |
| improve | partial | 16-50ms | 16-50ms | 275 | 1% | -2.02 |
| join | partial | 50-200ms | 50-200ms | 233 | 0% | -0.10 |
| join | sweep | 5-16ms | ? | 184 | 0% | +1.02 |
| join | sweep | 1000-ms | 1000-ms | 179 | 0% | -0.44 |
| join | sweep | 1000-ms | ? | 176 | 0% | -1.15 |
| join | sweep | 200-1000ms | ? | 124 | 0% | +6.84 |
| improve | partial | 5-16ms | 5-16ms | 97 | 0% | +0.65 |
| join | sweep | 16-50ms | ? | 83 | 0% | -0.31 |
| join | sweep | 50-200ms | ? | 83 | 0% | -1.80 |
| join | partial | 200-1000ms | 1000-ms | 50 | 0% | -0.89 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 23,169 | 46% | +0.02 |
| improve | sweep | — | — | 14,714 | 29% | -0.41 |
| improve | partial | — | — | 7,538 | 15% | -0.23 |
| join | sweep | — | — | 5,400 | 11% | -0.21 |

no improve when spread > 2 ticks: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 13,017 | 27% | +0.42 |
| join | partial | 0-5ms | ? | 8,899 | 18% | -0.49 |
| join | sweep | 0-5ms | ? | 5,409 | 11% | -0.30 |
| improve | sweep | 1000-ms | ? | 4,126 | 8% | -0.27 |
| improve | sweep | 0-5ms | ? | 3,508 | 7% | -0.96 |
| improve | partial | 0-5ms | ? | 2,883 | 6% | -0.48 |
| improve | partial | 1000-ms | 1000-ms | 2,387 | 5% | +0.21 |
| improve | sweep | 200-1000ms | ? | 1,800 | 4% | -1.21 |
| improve | partial | 200-1000ms | 200-1000ms | 1,339 | 3% | +0.71 |
| join | partial | 1000-ms | ? | 1,238 | 3% | +0.37 |
| join | partial | 200-1000ms | 200-1000ms | 776 | 2% | -0.91 |
| improve | sweep | 50-200ms | ? | 598 | 1% | -0.01 |
| improve | partial | 50-200ms | 50-200ms | 433 | 1% | +0.14 |
| improve | partial | 16-50ms | 16-50ms | 347 | 1% | +0.42 |
| join | partial | 50-200ms | 50-200ms | 322 | 1% | -0.44 |
| join | sweep | 5-16ms | ? | 229 | 0% | +0.13 |
| join | sweep | 1000-ms | 1000-ms | 219 | 0% | +4.29 |
| improve | sweep | 16-50ms | ? | 166 | 0% | -1.55 |
| join | sweep | 1000-ms | ? | 156 | 0% | -0.98 |
| join | partial | 200-1000ms | 1000-ms | 90 | 0% | +0.60 |
| improve | partial | 5-16ms | 5-16ms | 89 | 0% | +0.85 |
| join | sweep | 50-200ms | ? | 84 | 0% | -1.80 |
| join | sweep | 16-50ms | ? | 83 | 0% | -0.31 |
| join | sweep | 200-1000ms | 200-1000ms | 78 | 0% | -0.97 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 24,416 | 50% | +0.04 |
| improve | sweep | — | — | 10,296 | 21% | -0.67 |
| improve | partial | — | — | 7,490 | 15% | +0.05 |
| join | sweep | — | — | 6,387 | 13% | -0.15 |

no improve when spread > 1 tick (join only): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 16,972 | 41% | +0.25 |
| join | partial | 0-5ms | ? | 12,816 | 31% | -0.60 |
| join | sweep | 0-5ms | ? | 7,711 | 19% | -0.29 |
| join | partial | 200-1000ms | 200-1000ms | 1,471 | 4% | -0.42 |
| join | partial | 1000-ms | ? | 1,269 | 3% | +0.29 |
| join | partial | 50-200ms | 50-200ms | 290 | 1% | +0.61 |
| join | sweep | 1000-ms | 1000-ms | 271 | 1% | -0.57 |
| join | partial | 200-1000ms | 1000-ms | 262 | 1% | +0.35 |
| join | sweep | 5-16ms | ? | 152 | 0% | -0.32 |
| join | sweep | 200-1000ms | 200-1000ms | 124 | 0% | -3.81 |
| join | sweep | 50-200ms | 50-200ms | 106 | 0% | +0.61 |
| join | partial | 50-200ms | 1000-ms | 54 | 0% | +6.77 |
| join | sweep | 200-1000ms | 1000-ms | 23 | 0% | +12.64 |
| join | partial | 50-200ms | 200-1000ms | 20 | 0% | +7.50 |
| join | sweep | 16-50ms | 16-50ms | 20 | 0% | +4.50 |
| join | partial | 200-1000ms | ? | 20 | 0% | -1.50 |
| join | partial | 0-5ms | 200-1000ms | 13 | 0% | +1.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 33,188 | 80% | -0.09 |
| join | sweep | — | — | 8,407 | 20% | -0.30 |

pull when spread > 3 ticks: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 12,782 | 26% | +0.40 |
| join | partial | 0-5ms | ? | 8,200 | 17% | -0.54 |
| improve | sweep | 0-5ms | ? | 4,737 | 10% | -1.20 |
| improve | sweep | 1000-ms | ? | 4,641 | 9% | -0.33 |
| join | sweep | 0-5ms | ? | 4,447 | 9% | -0.29 |
| improve | partial | 0-5ms | ? | 2,846 | 6% | -0.53 |
| improve | sweep | 200-1000ms | ? | 2,501 | 5% | -1.09 |
| improve | partial | 1000-ms | 1000-ms | 2,429 | 5% | +0.21 |
| improve | partial | 200-1000ms | 200-1000ms | 1,357 | 3% | +0.49 |
| join | partial | 1000-ms | ? | 1,283 | 3% | +0.33 |
| improve | sweep | 50-200ms | ? | 962 | 2% | +0.05 |
| join | partial | 200-1000ms | 200-1000ms | 580 | 1% | -0.23 |
| improve | partial | 50-200ms | 50-200ms | 485 | 1% | +0.13 |
| improve | sweep | 16-50ms | ? | 336 | 1% | +1.00 |
| improve | partial | 16-50ms | 16-50ms | 288 | 1% | +0.11 |
| join | partial | 50-200ms | 50-200ms | 240 | 0% | -0.08 |
| join | sweep | 1000-ms | 1000-ms | 179 | 0% | -0.44 |
| join | sweep | 1000-ms | ? | 176 | 0% | -1.15 |
| join | sweep | 5-16ms | ? | 164 | 0% | +0.60 |
| join | sweep | 200-1000ms | ? | 162 | 0% | +5.85 |
| improve | partial | 5-16ms | 5-16ms | 92 | 0% | +0.91 |
| join | sweep | 16-50ms | ? | 83 | 0% | -0.31 |
| join | sweep | 50-200ms | ? | 77 | 0% | -1.64 |
| join | partial | 200-1000ms | 1000-ms | 50 | 0% | -0.89 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 23,186 | 47% | +0.04 |
| improve | sweep | — | — | 13,275 | 27% | -0.72 |
| improve | partial | — | — | 7,510 | 15% | -0.02 |
| join | sweep | — | — | 5,350 | 11% | -0.11 |

pull when spread > 2 ticks: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 12,659 | 27% | +0.40 |
| join | partial | 0-5ms | ? | 8,151 | 17% | -0.56 |
| join | sweep | 0-5ms | ? | 4,444 | 10% | -0.75 |
| improve | sweep | 1000-ms | ? | 4,155 | 9% | -0.26 |
| improve | sweep | 0-5ms | ? | 3,693 | 8% | -1.07 |
| improve | partial | 0-5ms | ? | 2,917 | 6% | -0.47 |
| improve | partial | 1000-ms | 1000-ms | 2,481 | 5% | +0.12 |
| improve | sweep | 200-1000ms | ? | 1,767 | 4% | -1.35 |
| improve | partial | 200-1000ms | 200-1000ms | 1,394 | 3% | +0.54 |
| join | partial | 1000-ms | ? | 1,263 | 3% | +0.36 |
| improve | sweep | 50-200ms | ? | 685 | 1% | -0.18 |
| join | partial | 200-1000ms | 200-1000ms | 544 | 1% | +0.10 |
| improve | partial | 50-200ms | 50-200ms | 448 | 1% | +0.10 |
| improve | partial | 16-50ms | 16-50ms | 310 | 1% | +0.07 |
| improve | sweep | 16-50ms | ? | 245 | 1% | -0.29 |
| join | partial | 50-200ms | 50-200ms | 232 | 0% | -0.21 |
| join | sweep | 1000-ms | 1000-ms | 199 | 0% | +5.17 |
| join | sweep | 5-16ms | ? | 182 | 0% | +0.36 |
| join | sweep | 1000-ms | ? | 175 | 0% | -1.15 |
| improve | partial | 5-16ms | 5-16ms | 109 | 0% | +0.97 |
| join | sweep | 200-1000ms | ? | 104 | 0% | -1.18 |
| join | sweep | 16-50ms | ? | 83 | 0% | -0.31 |
| join | partial | 200-1000ms | 1000-ms | 70 | 0% | -1.06 |
| improve | sweep | 5-16ms | ? | 61 | 0% | -2.97 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 22,988 | 49% | +0.04 |
| improve | sweep | — | — | 10,655 | 23% | -0.73 |
| improve | partial | — | — | 7,673 | 16% | -0.02 |
| join | sweep | — | — | 5,286 | 11% | -0.50 |

pause 10 s after a 5c jump: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 12,031 | 27% | +0.34 |
| join | partial | 0-5ms | ? | 7,677 | 17% | -0.49 |
| improve | sweep | 1000-ms | ? | 4,413 | 10% | -0.37 |
| join | sweep | 0-5ms | ? | 4,010 | 9% | -0.35 |
| improve | sweep | 0-5ms | ? | 3,615 | 8% | -0.37 |
| improve | partial | 0-5ms | ? | 2,553 | 6% | -1.07 |
| improve | partial | 1000-ms | 1000-ms | 2,329 | 5% | +0.18 |
| improve | sweep | 200-1000ms | ? | 2,016 | 5% | -1.33 |
| join | partial | 1000-ms | ? | 1,265 | 3% | +0.36 |
| improve | partial | 200-1000ms | 200-1000ms | 1,098 | 2% | +0.93 |
| improve | sweep | 50-200ms | ? | 873 | 2% | -0.46 |
| join | partial | 200-1000ms | 200-1000ms | 435 | 1% | +0.01 |
| improve | partial | 50-200ms | 50-200ms | 305 | 1% | +0.13 |
| improve | partial | 16-50ms | 16-50ms | 228 | 1% | -0.02 |
| improve | sweep | 16-50ms | ? | 210 | 0% | -0.71 |
| join | sweep | 1000-ms | 1000-ms | 199 | 0% | -0.34 |
| join | partial | 50-200ms | 50-200ms | 168 | 0% | -1.12 |
| join | sweep | 1000-ms | ? | 150 | 0% | -1.33 |
| join | sweep | 5-16ms | ? | 145 | 0% | -0.45 |
| join | sweep | 200-1000ms | ? | 114 | 0% | +7.73 |
| improve | partial | 5-16ms | 5-16ms | 92 | 0% | +1.56 |
| join | sweep | 16-50ms | ? | 69 | 0% | +1.16 |
| join | sweep | 50-200ms | ? | 47 | 0% | +1.43 |
| join | partial | 200-1000ms | 1000-ms | 40 | 0% | -0.99 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 21,665 | 49% | +0.03 |
| improve | sweep | — | — | 11,225 | 25% | -0.55 |
| improve | partial | — | — | 6,621 | 15% | -0.16 |
| join | sweep | — | — | 4,759 | 11% | -0.13 |

pause 30 s after a 5c jump: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 10,970 | 29% | +0.32 |
| join | partial | 0-5ms | ? | 6,682 | 18% | -0.53 |
| improve | sweep | 1000-ms | ? | 3,460 | 9% | -0.02 |
| join | sweep | 0-5ms | ? | 3,323 | 9% | -0.20 |
| improve | sweep | 0-5ms | ? | 3,092 | 8% | -0.55 |
| improve | partial | 0-5ms | ? | 2,236 | 6% | -1.30 |
| improve | partial | 1000-ms | 1000-ms | 2,093 | 5% | +0.12 |
| improve | sweep | 200-1000ms | ? | 1,393 | 4% | -2.15 |
| join | partial | 1000-ms | ? | 1,243 | 3% | +0.36 |
| improve | partial | 200-1000ms | 200-1000ms | 984 | 3% | +1.26 |
| improve | sweep | 50-200ms | ? | 689 | 2% | -0.26 |
| join | partial | 200-1000ms | 200-1000ms | 371 | 1% | -0.08 |
| improve | partial | 50-200ms | 50-200ms | 274 | 1% | +0.35 |
| improve | partial | 16-50ms | 16-50ms | 194 | 1% | -0.69 |
| join | sweep | 1000-ms | 1000-ms | 158 | 0% | -0.46 |
| join | partial | 50-200ms | 50-200ms | 148 | 0% | -1.22 |
| improve | sweep | 16-50ms | ? | 140 | 0% | -1.96 |
| join | sweep | 5-16ms | ? | 105 | 0% | -0.62 |
| join | sweep | 1000-ms | ? | 94 | 0% | -1.91 |
| join | sweep | 200-1000ms | ? | 87 | 0% | +10.63 |
| improve | partial | 5-16ms | 5-16ms | 83 | 0% | +1.78 |
| join | partial | 200-1000ms | 1000-ms | 47 | 0% | -0.92 |
| join | partial | 5-16ms | 5-16ms | 39 | 0% | -0.34 |
| join | sweep | 50-200ms | ? | 39 | 0% | +1.45 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 19,533 | 51% | +0.01 |
| improve | sweep | — | — | 8,855 | 23% | -0.58 |
| improve | partial | — | — | 5,871 | 15% | -0.22 |
| join | sweep | — | — | 3,865 | 10% | +0.03 |

join only + pause 10 s: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 16,005 | 43% | +0.24 |
| join | partial | 0-5ms | ? | 11,438 | 31% | -0.52 |
| join | sweep | 0-5ms | ? | 6,144 | 17% | -0.24 |
| join | partial | 1000-ms | ? | 1,303 | 4% | +0.26 |
| join | partial | 200-1000ms | 200-1000ms | 1,092 | 3% | -0.30 |
| join | sweep | 1000-ms | 1000-ms | 267 | 1% | -0.66 |
| join | partial | 200-1000ms | 1000-ms | 192 | 1% | +1.18 |
| join | partial | 50-200ms | 50-200ms | 184 | 0% | +0.72 |
| join | sweep | 5-16ms | ? | 89 | 0% | -0.55 |
| join | sweep | 200-1000ms | 200-1000ms | 84 | 0% | -4.51 |
| join | sweep | 50-200ms | 50-200ms | 66 | 0% | -0.98 |
| join | partial | 50-200ms | 1000-ms | 20 | 0% | +3.41 |
| join | sweep | 16-50ms | 16-50ms | 20 | 0% | +4.50 |
| join | partial | 200-1000ms | ? | 20 | 0% | -1.50 |
| join | partial | 0-5ms | 200-1000ms | 13 | 0% | +1.50 |
| join | sweep | 200-1000ms | 1000-ms | 5 | 0% | +9.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 30,267 | 82% | -0.06 |
| join | sweep | — | — | 6,676 | 18% | -0.30 |

pull > 2 ticks + pause 10 s: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 11,924 | 28% | +0.38 |
| join | partial | 0-5ms | ? | 7,698 | 18% | -0.53 |
| join | sweep | 0-5ms | ? | 3,978 | 9% | -0.65 |
| improve | sweep | 1000-ms | ? | 3,960 | 9% | -0.17 |
| improve | sweep | 0-5ms | ? | 2,816 | 7% | -0.78 |
| improve | partial | 0-5ms | ? | 2,587 | 6% | -0.39 |
| improve | partial | 1000-ms | 1000-ms | 2,384 | 6% | +0.24 |
| improve | sweep | 200-1000ms | ? | 1,493 | 4% | -1.95 |
| join | partial | 1000-ms | ? | 1,283 | 3% | +0.34 |
| improve | partial | 200-1000ms | 200-1000ms | 1,134 | 3% | +0.61 |
| improve | sweep | 50-200ms | ? | 479 | 1% | -0.62 |
| join | partial | 200-1000ms | 200-1000ms | 428 | 1% | +0.20 |
| improve | partial | 50-200ms | 50-200ms | 308 | 1% | +0.08 |
| improve | partial | 16-50ms | 16-50ms | 227 | 1% | -0.31 |
| join | sweep | 1000-ms | 1000-ms | 219 | 1% | +4.74 |
| improve | sweep | 16-50ms | ? | 188 | 0% | -0.43 |
| join | partial | 50-200ms | 50-200ms | 173 | 0% | -1.20 |
| join | sweep | 5-16ms | ? | 163 | 0% | -0.59 |
| join | sweep | 1000-ms | ? | 149 | 0% | -1.33 |
| join | sweep | 200-1000ms | ? | 95 | 0% | -1.80 |
| improve | partial | 5-16ms | 5-16ms | 89 | 0% | +1.52 |
| join | partial | 200-1000ms | 1000-ms | 87 | 0% | -1.65 |
| join | sweep | 16-50ms | ? | 69 | 0% | +1.16 |
| improve | sweep | 5-16ms | ? | 39 | 0% | +0.48 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 21,658 | 51% | +0.03 |
| improve | sweep | — | — | 9,022 | 21% | -0.68 |
| improve | partial | — | — | 6,736 | 16% | +0.05 |
| join | sweep | — | — | 4,720 | 11% | -0.39 |

pull > 2 ticks + pause 10 s, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 3,355 | 28% | +0.44 |
| join | partial | 0-5ms | ? | 2,134 | 18% | -0.54 |
| improve | sweep | 1000-ms | ? | 1,296 | 11% | -0.05 |
| join | sweep | 0-5ms | ? | 1,058 | 9% | -0.66 |
| improve | sweep | 0-5ms | ? | 718 | 6% | -0.71 |
| improve | partial | 0-5ms | ? | 713 | 6% | -0.43 |
| improve | partial | 1000-ms | 1000-ms | 709 | 6% | -0.07 |
| improve | sweep | 200-1000ms | ? | 499 | 4% | -1.42 |
| join | partial | 1000-ms | ? | 361 | 3% | +0.41 |
| improve | partial | 200-1000ms | 200-1000ms | 332 | 3% | +0.60 |
| improve | sweep | 50-200ms | ? | 145 | 1% | -0.73 |
| join | partial | 200-1000ms | 200-1000ms | 125 | 1% | +0.23 |
| improve | partial | 50-200ms | 50-200ms | 104 | 1% | +0.06 |
| improve | partial | 16-50ms | 16-50ms | 92 | 1% | -1.78 |
| improve | sweep | 16-50ms | ? | 76 | 1% | -0.54 |
| join | sweep | 1000-ms | 1000-ms | 55 | 0% | +4.84 |
| join | partial | 50-200ms | 50-200ms | 55 | 0% | -1.22 |
| join | sweep | 5-16ms | ? | 48 | 0% | -0.60 |
| join | sweep | 1000-ms | ? | 41 | 0% | -1.11 |
| join | sweep | 200-1000ms | ? | 29 | 0% | -6.29 |
| improve | partial | 5-16ms | 5-16ms | 25 | 0% | +1.30 |
| join | sweep | 16-50ms | ? | 18 | 0% | +0.55 |
| join | partial | 200-1000ms | 1000-ms | 10 | 0% | -1.97 |
| join | sweep | 200-1000ms | 200-1000ms | 7 | 0% | +2.93 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 6,047 | 50% | +0.07 |
| improve | sweep | — | — | 2,746 | 23% | -0.53 |
| improve | partial | — | — | 1,980 | 16% | -0.14 |
| join | sweep | — | — | 1,265 | 11% | -0.51 |