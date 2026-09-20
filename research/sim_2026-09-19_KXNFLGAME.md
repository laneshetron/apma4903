# Quoter simulation, KXNFLGAME, 2026-09-19

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 33 | 2.26 | 2.86 | -0.60 | -0.19 | 33 | 2.26 | 2.86 | -0.60 | 1.07 | 1.19 | 0.07 | 0.08 | 4.73 | -0.10 | 731 | 0.31 | 0.36 | 51.92 | 0.05 | 104 | 12.27 | 8.07 | 0.00 |
|  ↳ vetoes: {'capital': 116323, 'priority_fills': 42} |
| touch joiner, size 5 | 39 | 0.71 | 1.93 | -1.23 | -0.45 | 39 | 0.71 | 1.93 | -1.23 | 0.35 | 0.36 | 0.02 | 0.05 | 2.40 | -0.17 | 618 | 0.12 | 0.24 | 64.24 | 0.04 | 165 | 4.60 | 3.24 | 0.00 |
|  ↳ vetoes: {'priority_fills': 87} |
| touch joiner, depth >= 50 | 34 | 2.46 | 2.79 | -0.33 | -0.00 | 34 | 2.46 | 2.79 | -0.33 | 1.27 | 1.19 | 0.07 | 0.08 | 5.15 | -0.11 | 669 | 0.37 | 0.41 | 49.41 | 0.05 | 85 | 11.57 | 6.88 | 0.00 |
|  ↳ vetoes: {'capital': 114407, 'thin': 8166, 'priority_fills': 39} |
| join only, never improve | 32 | 3.24 | 3.10 | 0.14 | -0.23 | 32 | 3.24 | 3.10 | 0.14 | 1.69 | 1.55 | 0.10 | 0.08 | 6.97 | -0.03 | 588 | 0.55 | 0.49 | 0.00 | 0.04 | 69 | 12.10 | 8.21 | 0.00 |
|  ↳ vetoes: {'capital': 118844, 'priority_fills': 10} |
| touch joiner, pessimistic queue | 9 | 0.21 | 0.12 | 0.08 | -0.02 | 9 | 0.21 | 0.12 | 0.08 | 0.00 | 0.21 | 0.02 | 0.04 | 1.83 | -0.01 | 108 | 0.19 | 0.01 | 78.57 | 0.04 | 14 | 8.51 | 5.04 | 0.00 |
|  ↳ vetoes: {'capital': 158467, 'priority_fills': 11} |
| touch joiner, carry (no flatten) | 33 | 2.26 | 2.86 | -0.60 | -0.19 | 33 | 2.26 | 2.86 | -0.60 | 1.07 | 1.19 | 0.07 | 0.08 | 4.73 | -0.10 | 731 | 0.31 | 0.36 | 51.92 | 0.05 | 104 | 12.27 | 8.07 | 0.00 |
|  ↳ vetoes: {'capital': 116323, 'priority_fills': 42} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | ? | 453 | 62% | +0.50 |
| improve | sweep | 1000-ms | ? | 193 | 26% | +0.05 |
| improve | partial | 1000-ms | 1000-ms | 46 | 6% | +0.50 |
| join | sweep | 0-5ms | ? | 17 | 2% | -0.06 |
| improve | sweep | 0-5ms | ? | 11 | 2% | +0.00 |
| improve | partial | 0-5ms | ? | 4 | 1% | -0.12 |
| join | partial | 1000-ms | 1000-ms | 3 | 0% | +0.50 |
| join | partial | 0-5ms | ? | 2 | 0% | +0.00 |
| join | sweep | 1000-ms | ? | 1 | 0% | +0.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 458 | 63% | +0.50 |
| improve | sweep | — | — | 204 | 28% | +0.05 |
| improve | partial | — | — | 51 | 7% | +0.45 |
| join | sweep | — | — | 18 | 2% | -0.06 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 284 | 46% | +0.09 |
| join | partial | 1000-ms | ? | 182 | 30% | +0.50 |
| improve | partial | 1000-ms | 1000-ms | 55 | 9% | +0.50 |
| join | partial | 1000-ms | 1000-ms | 34 | 5% | +0.50 |
| improve | sweep | 0-5ms | ? | 27 | 4% | -0.23 |
| improve | partial | 0-5ms | ? | 15 | 2% | -0.25 |
| join | sweep | 0-5ms | ? | 10 | 2% | -0.50 |
| join | sweep | 1000-ms | ? | 10 | 2% | +0.25 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 311 | 50% | +0.06 |
| join | partial | — | — | 216 | 35% | +0.50 |
| improve | partial | — | — | 70 | 11% | +0.34 |
| join | sweep | — | — | 20 | 3% | -0.12 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | ? | 462 | 69% | +0.50 |
| improve | sweep | 1000-ms | ? | 157 | 23% | +0.11 |
| improve | partial | 1000-ms | 1000-ms | 43 | 6% | +0.50 |
| join | sweep | 1000-ms | ? | 3 | 0% | +0.33 |
| improve | sweep | 0-5ms | ? | 2 | 0% | +0.00 |
| join | partial | 1000-ms | 1000-ms | 2 | 0% | +0.50 |
| improve | sweep | 200-1000ms | ? | 0 | 0% | +0.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 464 | 69% | +0.50 |
| improve | sweep | — | — | 159 | 24% | +0.10 |
| improve | partial | — | — | 43 | 6% | +0.50 |
| join | sweep | — | — | 3 | 0% | +0.33 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | ? | 482 | 82% | +0.51 |
| join | partial | 1000-ms | 1000-ms | 66 | 11% | +0.58 |
| join | sweep | 0-5ms | ? | 37 | 6% | +0.07 |
| join | partial | 0-5ms | ? | 3 | 1% | +0.17 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 551 | 94% | +0.52 |
| join | sweep | — | — | 37 | 6% | +0.07 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 64 | 59% | -0.13 |
| join | partial | 1000-ms | ? | 20 | 19% | +0.50 |
| join | sweep | 1000-ms | ? | 20 | 19% | +0.00 |
| improve | partial | 0-5ms | ? | 1 | 1% | +0.00 |
| improve | partial | 1000-ms | 1000-ms | 1 | 1% | +0.50 |
| join | sweep | 0-5ms | ? | 1 | 1% | -0.50 |
| improve | sweep | 0-5ms | ? | 1 | 1% | +0.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 65 | 60% | -0.13 |
| join | sweep | — | — | 21 | 19% | -0.02 |
| join | partial | — | — | 20 | 19% | +0.50 |
| improve | partial | — | — | 2 | 2% | +0.22 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | ? | 453 | 62% | +0.50 |
| improve | sweep | 1000-ms | ? | 193 | 26% | +0.05 |
| improve | partial | 1000-ms | 1000-ms | 46 | 6% | +0.50 |
| join | sweep | 0-5ms | ? | 17 | 2% | -0.06 |
| improve | sweep | 0-5ms | ? | 11 | 2% | +0.00 |
| improve | partial | 0-5ms | ? | 4 | 1% | -0.12 |
| join | partial | 1000-ms | 1000-ms | 3 | 0% | +0.50 |
| join | partial | 0-5ms | ? | 2 | 0% | +0.00 |
| join | sweep | 1000-ms | ? | 1 | 0% | +0.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 458 | 63% | +0.50 |
| improve | sweep | — | — | 204 | 28% | +0.05 |
| improve | partial | — | — | 51 | 7% | +0.45 |
| join | sweep | — | — | 18 | 2% | -0.06 |