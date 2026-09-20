# Quoter simulation, KXEFLCHAMPIONSHIPTOTAL, 2026-09-19

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 12 | 30.96 | 90.84 | -54.51 | -166.94 | 12 | 30.96 | 90.84 | -54.51 | 36.50 | -5.54 | 2.58 | 3.90 | 2.29 | -2.26 | 2,529 | 1.22 | -0.11 | 78.35 | 2.64 | 254 | 17.92 | 5.90 | 0.67 |
|  ↳ vetoes: {'priority_fills': 426, 'capital': 2841} |
| touch joiner, size 5 | 12 | 9.64 | 28.50 | -17.15 | -56.20 | 12 | 9.64 | 28.50 | -17.15 | 9.65 | -0.01 | 0.80 | 1.22 | 2.28 | -0.53 | 734 | 1.31 | -0.18 | 79.90 | 0.77 | 199 | 4.62 | 1.82 | 0.23 |
|  ↳ vetoes: {'priority_fills': 347} |
| touch joiner, depth >= 50 | 12 | 16.86 | 83.59 | -60.31 | -125.01 | 12 | 16.86 | 83.59 | -60.31 | 30.13 | -13.27 | 1.41 | 4.72 | 1.03 | -4.56 | 2,102 | 0.80 | 0.32 | 90.15 | 2.19 | 203 | 17.81 | 7.58 | 0.85 |
|  ↳ vetoes: {'thin': 49485, 'priority_fills': 382, 'capital': 4106} |
| join only, never improve | 12 | 18.58 | 63.69 | -37.16 | -160.16 | 12 | 18.58 | 63.69 | -37.16 | 21.27 | -2.68 | 1.55 | 4.05 | 1.32 | -2.41 | 1,339 | 1.39 | -0.24 | 0.00 | 1.40 | 147 | 17.66 | 5.69 | 1.02 |
|  ↳ vetoes: {'priority_fills': 171, 'capital': 2059} |
| touch joiner, pessimistic queue | 12 | 7.82 | 91.02 | -77.01 | -161.87 | 12 | 7.82 | 91.02 | -77.01 | 21.61 | -13.79 | 0.65 | 5.00 | 0.45 | -9.25 | 2,137 | 0.37 | -0.10 | 90.32 | 2.23 | 217 | 17.44 | 6.49 | 0.79 |
|  ↳ vetoes: {'priority_fills': 441, 'capital': 4195} |
| touch joiner, carry (no flatten) | 12 | 37.46 | 90.89 | -53.43 | -169.37 | 12 | 37.46 | 90.89 | -53.43 | 36.72 | 0.74 | 3.12 | 4.08 | 2.65 | -0.33 | 2,527 | 1.48 | -0.13 | 78.26 | 2.64 | 253 | 18.08 | 9.53 | 0.67 |
|  ↳ vetoes: {'priority_fills': 428, 'capital': 3013} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 1,881 | 28% | -0.53 |
| improve | sweep | 0-5ms | ? | 1,276 | 19% | +1.29 |
| improve | partial | 1000-ms | 1000-ms | 1,075 | 16% | -1.87 |
| join | partial | 0-5ms | ? | 638 | 10% | +0.87 |
| join | partial | 1000-ms | 1000-ms | 486 | 7% | -0.15 |
| improve | partial | 0-5ms | ? | 338 | 5% | -2.27 |
| join | sweep | 0-5ms | ? | 286 | 4% | -0.47 |
| join | sweep | 1000-ms | ? | 192 | 3% | +3.53 |
| join | partial | 1000-ms | ? | 169 | 3% | -1.53 |
| improve | sweep | 200-1000ms | ? | 116 | 2% | -1.65 |
| improve | sweep | 50-200ms | ? | 83 | 1% | +0.40 |
| improve | partial | 200-1000ms | 200-1000ms | 59 | 1% | +0.50 |
| join | sweep | 200-1000ms | ? | 20 | 0% | +12.00 |
| join | sweep | 1000-ms | 1000-ms | 20 | 0% | +26.50 |
| join | partial | 50-200ms | 50-200ms | 20 | 0% | +0.50 |
| improve | partial | 50-200ms | 50-200ms | 10 | 0% | +1.00 |
| improve | sweep | 5-16ms | ? | 1 | 0% | -17.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 3,358 | 50% | +0.14 |
| improve | partial | — | — | 1,483 | 22% | -1.84 |
| join | partial | — | — | 1,313 | 20% | +0.18 |
| join | sweep | — | — | 518 | 8% | +2.53 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 569 | 28% | -0.12 |
| improve | sweep | 0-5ms | ? | 376 | 19% | -0.00 |
| improve | partial | 1000-ms | 1000-ms | 301 | 15% | -1.82 |
| join | partial | 0-5ms | ? | 200 | 10% | +0.78 |
| join | partial | 1000-ms | 1000-ms | 146 | 7% | +0.87 |
| improve | partial | 0-5ms | ? | 106 | 5% | -1.88 |
| join | sweep | 0-5ms | ? | 85 | 4% | -2.41 |
| join | sweep | 1000-ms | ? | 59 | 3% | +4.13 |
| join | partial | 1000-ms | ? | 53 | 3% | -1.16 |
| improve | sweep | 200-1000ms | ? | 50 | 3% | -0.37 |
| improve | sweep | 50-200ms | ? | 29 | 1% | +0.71 |
| improve | partial | 200-1000ms | 200-1000ms | 11 | 1% | +0.69 |
| improve | partial | 50-200ms | 50-200ms | 10 | 0% | +0.75 |
| join | sweep | 200-1000ms | ? | 5 | 0% | +12.00 |
| join | sweep | 1000-ms | 1000-ms | 5 | 0% | +26.50 |
| improve | sweep | 5-16ms | ? | 1 | 0% | -17.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 1,025 | 51% | -0.08 |
| improve | partial | — | — | 428 | 21% | -1.70 |
| join | partial | — | — | 399 | 20% | +0.56 |
| join | sweep | — | — | 154 | 8% | +1.50 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 1,836 | 32% | -0.54 |
| improve | sweep | 0-5ms | ? | 1,197 | 21% | +1.87 |
| improve | partial | 1000-ms | 1000-ms | 886 | 15% | +0.17 |
| join | partial | 0-5ms | ? | 490 | 9% | +1.94 |
| join | partial | 1000-ms | 1000-ms | 469 | 8% | -1.90 |
| improve | sweep | 200-1000ms | ? | 150 | 3% | +0.29 |
| join | partial | 1000-ms | ? | 146 | 3% | -1.83 |
| improve | partial | 0-5ms | ? | 145 | 3% | -2.23 |
| join | sweep | 1000-ms | ? | 128 | 2% | +5.57 |
| join | sweep | 0-5ms | ? | 97 | 2% | -0.69 |
| improve | sweep | 50-200ms | ? | 87 | 2% | +2.46 |
| improve | partial | 200-1000ms | 200-1000ms | 40 | 1% | +0.50 |
| join | partial | 200-1000ms | 200-1000ms | 20 | 0% | +0.50 |
| join | partial | 50-200ms | 50-200ms | 20 | 0% | +0.50 |
| improve | partial | 50-200ms | 50-200ms | 10 | 0% | +1.00 |
| improve | sweep | 5-16ms | ? | 1 | 0% | -17.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 3,272 | 57% | +0.46 |
| join | partial | — | — | 1,144 | 20% | -0.16 |
| improve | partial | — | — | 1,082 | 19% | -0.13 |
| join | sweep | — | — | 225 | 4% | +2.87 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 1,508 | 34% | +0.32 |
| join | partial | 0-5ms | ? | 1,500 | 34% | +1.54 |
| join | sweep | 0-5ms | ? | 955 | 22% | -2.69 |
| join | partial | 1000-ms | ? | 244 | 6% | -1.01 |
| join | sweep | 1000-ms | 1000-ms | 106 | 2% | -8.46 |
| join | sweep | 1000-ms | ? | 26 | 1% | -10.67 |
| join | partial | 200-1000ms | 200-1000ms | 21 | 0% | +1.62 |
| join | sweep | 16-50ms | ? | 20 | 0% | -3.50 |
| join | sweep | 200-1000ms | 200-1000ms | 19 | 0% | +4.00 |
| join | sweep | 50-200ms | 50-200ms | 18 | 0% | +6.50 |
| join | sweep | 5-16ms | ? | 1 | 0% | -16.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 3,273 | 74% | +0.78 |
| join | sweep | — | — | 1,145 | 26% | -3.18 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 1,839 | 32% | -0.27 |
| improve | sweep | 0-5ms | ? | 1,288 | 23% | +1.35 |
| improve | partial | 1000-ms | 1000-ms | 1,059 | 19% | -1.59 |
| join | sweep | 0-5ms | ? | 376 | 7% | -1.69 |
| improve | partial | 0-5ms | ? | 339 | 6% | -2.22 |
| join | sweep | 1000-ms | ? | 225 | 4% | +2.90 |
| improve | sweep | 200-1000ms | ? | 160 | 3% | -0.41 |
| join | partial | 1000-ms | 1000-ms | 119 | 2% | +0.50 |
| improve | sweep | 50-200ms | ? | 66 | 1% | -2.32 |
| join | partial | 0-5ms | ? | 60 | 1% | +0.00 |
| join | partial | 1000-ms | ? | 60 | 1% | +0.50 |
| join | sweep | 1000-ms | 1000-ms | 40 | 1% | +13.00 |
| join | sweep | 200-1000ms | ? | 20 | 0% | +12.00 |
| improve | partial | 200-1000ms | 200-1000ms | 20 | 0% | +0.50 |
| improve | partial | 50-200ms | 50-200ms | 10 | 0% | +1.00 |
| improve | sweep | 5-16ms | ? | 1 | 0% | -17.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 3,354 | 59% | +0.30 |
| improve | partial | — | — | 1,428 | 25% | -1.69 |
| join | sweep | — | — | 661 | 12% | +1.18 |
| join | partial | — | — | 239 | 4% | +0.38 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 1,878 | 28% | -0.53 |
| improve | sweep | 0-5ms | ? | 1,294 | 19% | +1.19 |
| improve | partial | 1000-ms | 1000-ms | 1,079 | 16% | -1.86 |
| join | partial | 0-5ms | ? | 638 | 10% | +0.87 |
| join | partial | 1000-ms | 1000-ms | 462 | 7% | -0.16 |
| improve | partial | 0-5ms | ? | 338 | 5% | -2.27 |
| join | sweep | 0-5ms | ? | 286 | 4% | -0.47 |
| join | sweep | 1000-ms | ? | 192 | 3% | +3.53 |
| join | partial | 1000-ms | ? | 169 | 3% | -1.53 |
| improve | sweep | 200-1000ms | ? | 106 | 2% | -2.00 |
| improve | sweep | 50-200ms | ? | 83 | 1% | +0.40 |
| improve | partial | 200-1000ms | 200-1000ms | 59 | 1% | +0.50 |
| join | sweep | 200-1000ms | ? | 20 | 0% | +12.00 |
| join | sweep | 1000-ms | 1000-ms | 20 | 0% | +26.50 |
| join | partial | 50-200ms | 50-200ms | 20 | 0% | +0.50 |
| improve | partial | 50-200ms | 50-200ms | 10 | 0% | +1.00 |
| improve | sweep | 5-16ms | ? | 1 | 0% | -17.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 3,363 | 51% | +0.10 |
| improve | partial | — | — | 1,487 | 22% | -1.84 |
| join | partial | — | — | 1,289 | 19% | +0.18 |
| join | sweep | — | — | 518 | 8% | +2.53 |