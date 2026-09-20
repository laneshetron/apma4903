# Quoter simulation, KXJLEAGUETOTAL, 2026-09-19

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 4 | -2.42 | 41.93 | -44.35 | -250.34 | 4 | -2.42 | 41.93 | -44.35 | 4.30 | -6.72 | -0.60 | 2.67 | -0.45 | -3.49 | 879 | -0.28 | 0.08 | 80.00 | 2.86 | 100 | 20.00 | 15.41 | 0.00 |
|  ↳ vetoes: {'priority_fills': 723, 'capital': 6350} |
| touch joiner, size 5 | 4 | 1.10 | 11.50 | -10.40 | -57.60 | 4 | 1.10 | 11.50 | -10.40 | 2.19 | -1.10 | 0.27 | 0.89 | 0.62 | -0.86 | 250 | 0.44 | 0.65 | 75.71 | 0.81 | 70 | 5.00 | 2.89 | 0.00 |
|  ↳ vetoes: {'priority_fills': 592} |
| touch joiner, depth >= 50 | 4 | -2.52 | 39.06 | -41.58 | -209.07 | 4 | -2.52 | 39.06 | -41.58 | 5.25 | -7.77 | -0.63 | 2.40 | -0.52 | -4.29 | 718 | -0.35 | 0.50 | 89.47 | 2.33 | 76 | 20.00 | 16.86 | 0.00 |
|  ↳ vetoes: {'thin': 69449, 'priority_fills': 642, 'capital': 2634} |
| join only, never improve | 4 | 11.24 | 22.77 | -11.54 | -187.01 | 4 | 11.24 | 22.77 | -11.54 | 16.19 | -4.95 | 2.81 | 4.78 | 1.18 | -3.08 | 628 | 1.79 | -0.22 | 0.00 | 2.04 | 77 | 15.46 | 10.31 | 0.00 |
|  ↳ vetoes: {'priority_fills': 243, 'capital': 7885} |
| touch joiner, pessimistic queue | 4 | -2.02 | 40.88 | -42.90 | -236.89 | 4 | -2.02 | 40.88 | -42.90 | 6.16 | -8.18 | -0.51 | 3.01 | -0.34 | -3.49 | 771 | -0.26 | 0.40 | 85.39 | 2.51 | 89 | 20.00 | 17.58 | 0.00 |
|  ↳ vetoes: {'priority_fills': 742, 'capital': 8102} |
| touch joiner, carry (no flatten) | 4 | -2.42 | 41.93 | -44.35 | -250.34 | 4 | -2.42 | 41.93 | -44.35 | 4.30 | -6.72 | -0.60 | 2.67 | -0.45 | -3.49 | 879 | -0.28 | 0.08 | 80.00 | 2.86 | 100 | 20.00 | 15.41 | 0.00 |
|  ↳ vetoes: {'priority_fills': 723, 'capital': 6350} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 3,080 | 30% | -1.07 |
| improve | sweep | 1000-ms | ? | 2,902 | 28% | +1.62 |
| improve | partial | 1000-ms | 1000-ms | 1,370 | 13% | -1.13 |
| join | partial | 1000-ms | 1000-ms | 754 | 7% | -0.14 |
| join | partial | 0-5ms | ? | 622 | 6% | -0.52 |
| join | sweep | 0-5ms | ? | 507 | 5% | -0.54 |
| improve | partial | 0-5ms | ? | 389 | 4% | -0.43 |
| join | sweep | 1000-ms | ? | 276 | 3% | +3.09 |
| join | partial | 1000-ms | ? | 136 | 1% | +0.24 |
| improve | sweep | 200-1000ms | ? | 124 | 1% | -0.34 |
| join | sweep | 200-1000ms | ? | 40 | 0% | +0.00 |
| improve | sweep | 50-200ms | ? | 38 | 0% | +2.47 |
| improve | sweep | 16-50ms | ? | 20 | 0% | +19.23 |
| improve | partial | 50-200ms | 50-200ms | 20 | 0% | +0.50 |
| join | sweep | 1000-ms | 1000-ms | 20 | 0% | +26.50 |
| improve | partial | 200-1000ms | 200-1000ms | 11 | 0% | +0.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 6,164 | 60% | +0.30 |
| improve | partial | — | — | 1,789 | 17% | -0.95 |
| join | partial | — | — | 1,512 | 15% | -0.26 |
| join | sweep | — | — | 843 | 8% | +1.31 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 910 | 30% | -0.03 |
| improve | sweep | 1000-ms | ? | 885 | 29% | +2.06 |
| improve | partial | 1000-ms | 1000-ms | 374 | 12% | -0.93 |
| join | partial | 1000-ms | 1000-ms | 201 | 7% | -0.08 |
| join | partial | 0-5ms | ? | 189 | 6% | -0.65 |
| join | sweep | 0-5ms | ? | 125 | 4% | -0.04 |
| improve | partial | 0-5ms | ? | 117 | 4% | -1.13 |
| join | sweep | 1000-ms | ? | 96 | 3% | +2.87 |
| improve | sweep | 200-1000ms | ? | 50 | 2% | +2.74 |
| join | partial | 1000-ms | ? | 35 | 1% | +0.21 |
| improve | sweep | 50-200ms | ? | 26 | 1% | +4.35 |
| improve | partial | 200-1000ms | 200-1000ms | 10 | 0% | +0.50 |
| join | sweep | 200-1000ms | ? | 10 | 0% | +0.00 |
| improve | sweep | 16-50ms | ? | 7 | 0% | +16.21 |
| improve | partial | 50-200ms | 50-200ms | 5 | 0% | +0.50 |
| join | sweep | 1000-ms | 1000-ms | 5 | 0% | +26.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 1,878 | 62% | +1.15 |
| improve | partial | — | — | 506 | 17% | -0.93 |
| join | partial | — | — | 425 | 14% | -0.31 |
| join | sweep | — | — | 236 | 8% | +1.71 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 2,901 | 35% | +1.96 |
| improve | sweep | 0-5ms | ? | 2,829 | 34% | -0.38 |
| improve | partial | 1000-ms | 1000-ms | 919 | 11% | -0.19 |
| join | partial | 1000-ms | 1000-ms | 526 | 6% | -0.70 |
| join | partial | 0-5ms | ? | 300 | 4% | -3.28 |
| join | sweep | 0-5ms | ? | 222 | 3% | +2.05 |
| join | partial | 1000-ms | ? | 136 | 2% | +1.41 |
| join | sweep | 1000-ms | ? | 134 | 2% | +2.61 |
| improve | partial | 0-5ms | ? | 121 | 1% | -2.48 |
| improve | sweep | 200-1000ms | ? | 115 | 1% | -0.83 |
| improve | sweep | 50-200ms | ? | 38 | 0% | +2.47 |
| join | sweep | 200-1000ms | ? | 20 | 0% | +0.50 |
| improve | partial | 50-200ms | 50-200ms | 20 | 0% | +0.50 |
| improve | sweep | 16-50ms | ? | 18 | 0% | +21.03 |
| improve | partial | 200-1000ms | 200-1000ms | 11 | 0% | +0.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 5,901 | 71% | +0.85 |
| improve | partial | — | — | 1,071 | 13% | -0.43 |
| join | partial | — | — | 961 | 12% | -1.20 |
| join | sweep | — | — | 376 | 5% | +2.17 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 2,213 | 33% | -0.16 |
| join | partial | 0-5ms | ? | 2,065 | 31% | +0.88 |
| join | sweep | 0-5ms | ? | 2,063 | 31% | -1.74 |
| join | partial | 1000-ms | ? | 326 | 5% | +2.51 |
| join | sweep | 1000-ms | ? | 21 | 0% | -23.26 |
| join | partial | 200-1000ms | 200-1000ms | 20 | 0% | +0.50 |
| join | sweep | 1000-ms | 1000-ms | 20 | 0% | +26.50 |
| join | sweep | 5-16ms | ? | 19 | 0% | -10.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 4,623 | 69% | +0.50 |
| join | sweep | — | — | 2,123 | 31% | -1.77 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 3,161 | 32% | -0.47 |
| improve | sweep | 1000-ms | ? | 2,980 | 30% | +2.02 |
| improve | partial | 1000-ms | 1000-ms | 1,240 | 13% | -1.21 |
| join | sweep | 0-5ms | ? | 690 | 7% | -0.53 |
| join | partial | 1000-ms | 1000-ms | 496 | 5% | -0.60 |
| improve | partial | 0-5ms | ? | 347 | 4% | -0.90 |
| join | sweep | 1000-ms | ? | 266 | 3% | +2.06 |
| join | partial | 0-5ms | ? | 202 | 2% | -0.46 |
| improve | sweep | 200-1000ms | ? | 176 | 2% | +1.33 |
| join | partial | 1000-ms | ? | 76 | 1% | +2.27 |
| join | sweep | 200-1000ms | ? | 40 | 0% | +0.00 |
| improve | sweep | 50-200ms | ? | 38 | 0% | +2.46 |
| improve | partial | 200-1000ms | 200-1000ms | 31 | 0% | +0.50 |
| improve | sweep | 16-50ms | ? | 20 | 0% | +19.23 |
| improve | partial | 50-200ms | 50-200ms | 20 | 0% | +0.50 |
| join | sweep | 1000-ms | 1000-ms | 20 | 0% | +26.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 6,376 | 65% | +0.82 |
| improve | partial | — | — | 1,638 | 17% | -1.09 |
| join | sweep | — | — | 1,016 | 10% | +0.70 |
| join | partial | — | — | 774 | 8% | -0.28 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 3,080 | 30% | -1.07 |
| improve | sweep | 1000-ms | ? | 2,902 | 28% | +1.62 |
| improve | partial | 1000-ms | 1000-ms | 1,370 | 13% | -1.13 |
| join | partial | 1000-ms | 1000-ms | 754 | 7% | -0.14 |
| join | partial | 0-5ms | ? | 622 | 6% | -0.52 |
| join | sweep | 0-5ms | ? | 507 | 5% | -0.54 |
| improve | partial | 0-5ms | ? | 389 | 4% | -0.43 |
| join | sweep | 1000-ms | ? | 276 | 3% | +3.09 |
| join | partial | 1000-ms | ? | 136 | 1% | +0.24 |
| improve | sweep | 200-1000ms | ? | 124 | 1% | -0.34 |
| join | sweep | 200-1000ms | ? | 40 | 0% | +0.00 |
| improve | sweep | 50-200ms | ? | 38 | 0% | +2.47 |
| improve | sweep | 16-50ms | ? | 20 | 0% | +19.23 |
| improve | partial | 50-200ms | 50-200ms | 20 | 0% | +0.50 |
| join | sweep | 1000-ms | 1000-ms | 20 | 0% | +26.50 |
| improve | partial | 200-1000ms | 200-1000ms | 11 | 0% | +0.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 6,164 | 60% | +0.30 |
| improve | partial | — | — | 1,789 | 17% | -0.95 |
| join | partial | — | — | 1,512 | 15% | -0.26 |
| join | sweep | — | — | 843 | 8% | +1.31 |