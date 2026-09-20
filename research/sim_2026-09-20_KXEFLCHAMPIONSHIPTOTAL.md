# Quoter simulation, KXEFLCHAMPIONSHIPTOTAL, 2026-09-20

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 2 | -12.81 | 6.35 | -19.16 | -55.96 | 2 | -12.81 | 6.35 | -19.16 | -1.33 | -11.48 | -6.41 | 5.26 | -1.72 | -11.66 | 253 | -5.06 | -0.82 | 60.61 | 4.14 | 33 | 20.00 | 16.11 | 0.00 |
|  ↳ vetoes: {'priority_fills': 127} |
| touch joiner, size 5 | 2 | -3.13 | 2.90 | -6.03 | -15.52 | 2 | -3.13 | 2.90 | -6.03 | 0.09 | -3.22 | -1.57 | 1.64 | -1.35 | -3.21 | 90 | -3.47 | -0.62 | 55.56 | 1.47 | 27 | 5.00 | 5.00 | 0.00 |
|  ↳ vetoes: {'priority_fills': 97} |
| touch joiner, depth >= 50 | 2 | -6.15 | 6.79 | -12.94 | -42.81 | 2 | -6.15 | 6.79 | -12.94 | 3.22 | -9.37 | -3.07 | 1.92 | -2.26 | -5.00 | 211 | -2.92 | -0.63 | 92.31 | 3.44 | 26 | 20.00 | 14.93 | 0.00 |
|  ↳ vetoes: {'thin': 19412, 'priority_fills': 120} |
| join only, never improve | 2 | -3.76 | 3.64 | -7.40 | -45.47 | 2 | -3.76 | 3.64 | -7.40 | -2.88 | -0.88 | -1.88 | 6.42 | -0.41 | -8.30 | 218 | -1.73 | -0.72 | 0.00 | 3.56 | 33 | 20.00 | 3.42 | 0.00 |
|  ↳ vetoes: {'priority_fills': 57} |
| touch joiner, pessimistic queue | 2 | -11.33 | 6.30 | -17.64 | -54.18 | 2 | -11.33 | 6.30 | -17.64 | -2.73 | -8.60 | -5.67 | 4.52 | -1.77 | -10.18 | 248 | -4.58 | -0.64 | 68.97 | 4.04 | 29 | 20.00 | 13.28 | 0.00 |
|  ↳ vetoes: {'priority_fills': 137} |
| touch joiner, carry (no flatten) | 2 | -12.81 | 6.35 | -19.16 | -55.96 | 2 | -12.81 | 6.35 | -19.16 | -1.33 | -11.48 | -6.41 | 5.26 | -1.72 | -11.66 | 253 | -5.06 | -0.82 | 60.61 | 4.14 | 33 | 20.00 | 16.11 | 0.00 |
|  ↳ vetoes: {'priority_fills': 127} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 556 | 26% | -0.27 |
| improve | partial | 1000-ms | 1000-ms | 434 | 20% | -2.67 |
| improve | sweep | 1000-ms | ? | 329 | 15% | +1.28 |
| join | partial | 1000-ms | 1000-ms | 210 | 10% | -0.12 |
| join | partial | 0-5ms | ? | 199 | 9% | -0.55 |
| improve | partial | 0-5ms | ? | 109 | 5% | -2.23 |
| join | partial | 1000-ms | ? | 108 | 5% | +0.31 |
| join | sweep | 0-5ms | ? | 102 | 5% | -2.15 |
| improve | sweep | 200-1000ms | ? | 55 | 3% | -5.53 |
| join | partial | 200-1000ms | 200-1000ms | 20 | 1% | -0.50 |
| improve | partial | 50-200ms | 50-200ms | 20 | 1% | -2.00 |
| improve | sweep | 50-200ms | ? | 9 | 0% | +3.89 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 949 | 44% | +0.00 |
| improve | partial | — | — | 563 | 26% | -2.56 |
| join | partial | — | — | 536 | 25% | -0.21 |
| join | sweep | — | — | 102 | 5% | -2.15 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 165 | 25% | -0.21 |
| improve | sweep | 1000-ms | ? | 130 | 20% | +2.01 |
| improve | partial | 1000-ms | 1000-ms | 127 | 19% | -2.23 |
| join | partial | 0-5ms | ? | 61 | 9% | -1.73 |
| join | partial | 1000-ms | 1000-ms | 59 | 9% | -0.17 |
| join | partial | 1000-ms | ? | 30 | 5% | +0.50 |
| improve | partial | 0-5ms | ? | 30 | 5% | -4.92 |
| join | sweep | 0-5ms | ? | 24 | 4% | -0.03 |
| improve | sweep | 200-1000ms | ? | 20 | 3% | -5.00 |
| join | partial | 200-1000ms | 200-1000ms | 5 | 1% | -0.50 |
| improve | partial | 50-200ms | 50-200ms | 5 | 1% | -2.00 |
| improve | sweep | 50-200ms | ? | 4 | 1% | +0.00 |
| join | sweep | 1000-ms | ? | 2 | 0% | +2.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 319 | 48% | +0.40 |
| improve | partial | — | — | 162 | 24% | -2.72 |
| join | partial | — | — | 155 | 23% | -0.66 |
| join | sweep | — | — | 26 | 4% | +0.16 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 532 | 34% | -0.15 |
| improve | sweep | 1000-ms | ? | 379 | 24% | +1.11 |
| improve | partial | 1000-ms | 1000-ms | 233 | 15% | -3.58 |
| join | partial | 1000-ms | 1000-ms | 150 | 9% | -1.50 |
| join | partial | 1000-ms | ? | 88 | 6% | +0.50 |
| join | sweep | 0-5ms | ? | 69 | 4% | +0.10 |
| improve | sweep | 200-1000ms | ? | 55 | 3% | -5.53 |
| join | partial | 0-5ms | ? | 52 | 3% | -0.36 |
| improve | partial | 50-200ms | 50-200ms | 20 | 1% | -2.00 |
| improve | sweep | 50-200ms | ? | 9 | 1% | +3.89 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 975 | 61% | +0.07 |
| join | partial | — | — | 290 | 18% | -0.69 |
| improve | partial | — | — | 253 | 16% | -3.45 |
| join | sweep | — | — | 69 | 4% | +0.10 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 535 | 33% | -0.57 |
| join | sweep | 0-5ms | ? | 493 | 31% | -2.50 |
| join | partial | 0-5ms | ? | 443 | 27% | +0.98 |
| join | partial | 1000-ms | ? | 124 | 8% | +0.86 |
| join | sweep | 1000-ms | ? | 20 | 1% | -8.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 1,101 | 68% | +0.21 |
| join | sweep | — | — | 513 | 32% | -2.73 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 602 | 34% | +0.58 |
| improve | partial | 1000-ms | 1000-ms | 367 | 21% | -3.25 |
| improve | sweep | 1000-ms | ? | 340 | 19% | +1.58 |
| join | sweep | 0-5ms | ? | 161 | 9% | -1.22 |
| improve | partial | 0-5ms | ? | 89 | 5% | -2.94 |
| join | partial | 1000-ms | 1000-ms | 88 | 5% | -1.01 |
| improve | sweep | 200-1000ms | ? | 55 | 3% | -5.53 |
| join | sweep | 1000-ms | ? | 40 | 2% | +0.75 |
| join | partial | 0-5ms | ? | 20 | 1% | -0.01 |
| improve | partial | 50-200ms | 50-200ms | 20 | 1% | -2.00 |
| improve | sweep | 50-200ms | ? | 5 | 0% | +7.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 1,002 | 56% | +0.61 |
| improve | partial | — | — | 476 | 27% | -3.14 |
| join | sweep | — | — | 201 | 11% | -0.83 |
| join | partial | — | — | 108 | 6% | -0.83 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 556 | 26% | -0.27 |
| improve | partial | 1000-ms | 1000-ms | 434 | 20% | -2.67 |
| improve | sweep | 1000-ms | ? | 329 | 15% | +1.28 |
| join | partial | 1000-ms | 1000-ms | 210 | 10% | -0.12 |
| join | partial | 0-5ms | ? | 199 | 9% | -0.55 |
| improve | partial | 0-5ms | ? | 109 | 5% | -2.23 |
| join | partial | 1000-ms | ? | 108 | 5% | +0.31 |
| join | sweep | 0-5ms | ? | 102 | 5% | -2.15 |
| improve | sweep | 200-1000ms | ? | 55 | 3% | -5.53 |
| join | partial | 200-1000ms | 200-1000ms | 20 | 1% | -0.50 |
| improve | partial | 50-200ms | 50-200ms | 20 | 1% | -2.00 |
| improve | sweep | 50-200ms | ? | 9 | 0% | +3.89 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 949 | 44% | +0.00 |
| improve | partial | — | — | 563 | 26% | -2.56 |
| join | partial | — | — | 536 | 25% | -0.21 |
| join | sweep | — | — | 102 | 5% | -2.15 |