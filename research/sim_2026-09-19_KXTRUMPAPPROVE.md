# Quoter simulation, KXTRUMPAPPROVE, 2026-09-19

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 5 | 8.58 | 10.79 | -2.22 | -1.25 | 5 | 8.58 | 10.79 | -2.22 | 8.48 | 0.09 | 1.72 | 2.76 | 1.39 | -0.10 | 424 | 2.02 | 2.26 | 87.06 | 6.46 | 85 | 15.75 | 9.99 | 0.00 |
|  ↳ vetoes: {'priority_fills': 77} |
| touch joiner, size 5 | 5 | 3.33 | 4.02 | -0.69 | -0.41 | 5 | 3.33 | 4.02 | -0.69 | 3.31 | 0.02 | 0.67 | 1.16 | 1.29 | -0.03 | 148 | 2.25 | 2.42 | 81.43 | 2.25 | 70 | 4.67 | 3.33 | 0.00 |
|  ↳ vetoes: {'priority_fills': 62} |
| touch joiner, depth >= 50 | 5 | 9.52 | 11.13 | -1.61 | -0.46 | 5 | 9.52 | 11.13 | -1.61 | 9.06 | 0.46 | 1.90 | 2.73 | 1.56 | -0.07 | 422 | 2.26 | 2.54 | 94.05 | 6.42 | 84 | 13.37 | 9.48 | 0.00 |
|  ↳ vetoes: {'priority_fills': 76, 'thin': 424} |
| join only, never improve | 5 | 2.08 | 2.82 | -0.74 | -0.89 | 5 | 2.08 | 2.82 | -0.74 | 1.93 | 0.14 | 0.42 | 0.40 | 2.35 | 0.05 | 181 | 1.14 | 1.08 | 0.00 | 2.76 | 31 | 15.54 | 11.21 | 0.00 |
|  ↳ vetoes: {'priority_fills': 13} |
| touch joiner, pessimistic queue | 4 | 8.33 | 10.54 | -2.22 | -1.31 | 4 | 8.33 | 10.54 | -2.22 | 8.44 | -0.11 | 2.08 | 2.99 | 1.39 | -0.30 | 374 | 2.23 | 2.50 | 92.21 | 5.76 | 77 | 17.11 | 9.90 | 0.00 |
|  ↳ vetoes: {'priority_fills': 77} |
| touch joiner, carry (no flatten) | 5 | 8.58 | 10.79 | -2.22 | -1.25 | 5 | 8.58 | 10.79 | -2.22 | 8.48 | 0.09 | 1.72 | 2.76 | 1.39 | -0.10 | 424 | 2.02 | 2.26 | 87.06 | 6.46 | 85 | 15.75 | 9.99 | 0.00 |
|  ↳ vetoes: {'priority_fills': 77} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 238 | 56% | +3.18 |
| improve | sweep | 0-5ms | ? | 76 | 18% | +2.05 |
| join | sweep | 0-5ms | ? | 30 | 7% | -2.03 |
| join | partial | 1000-ms | ? | 30 | 7% | +0.50 |
| join | sweep | 1000-ms | ? | 20 | 5% | -0.50 |
| improve | partial | 1000-ms | 1000-ms | 20 | 5% | +0.50 |
| improve | sweep | 200-1000ms | ? | 9 | 2% | +11.00 |
| join | sweep | 1000-ms | 1000-ms | 1 | 0% | -1.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 322 | 76% | +3.12 |
| join | sweep | — | — | 52 | 12% | -1.42 |
| join | partial | — | — | 30 | 7% | +0.50 |
| improve | partial | — | — | 20 | 5% | +0.50 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 88 | 60% | +2.83 |
| improve | sweep | 0-5ms | ? | 24 | 16% | +3.19 |
| join | sweep | 0-5ms | ? | 10 | 7% | -2.50 |
| join | partial | 1000-ms | ? | 10 | 7% | +0.50 |
| improve | sweep | 200-1000ms | ? | 5 | 3% | +11.00 |
| join | sweep | 1000-ms | ? | 5 | 3% | -0.50 |
| improve | partial | 1000-ms | 1000-ms | 5 | 3% | +0.50 |
| join | sweep | 1000-ms | 1000-ms | 1 | 1% | -1.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 117 | 79% | +3.25 |
| join | sweep | — | — | 16 | 11% | -1.81 |
| join | partial | — | — | 10 | 7% | +0.50 |
| improve | partial | — | — | 5 | 3% | +0.50 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 287 | 68% | +2.77 |
| improve | sweep | 0-5ms | ? | 76 | 18% | +2.05 |
| join | partial | 1000-ms | ? | 30 | 7% | +0.50 |
| improve | partial | 1000-ms | 1000-ms | 20 | 5% | +0.50 |
| improve | sweep | 200-1000ms | ? | 9 | 2% | +11.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 371 | 88% | +2.82 |
| join | partial | — | — | 30 | 7% | +0.50 |
| improve | partial | — | — | 20 | 5% | +0.50 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 71 | 39% | -0.52 |
| join | partial | 1000-ms | 1000-ms | 48 | 27% | +2.56 |
| join | partial | 1000-ms | ? | 44 | 24% | +1.91 |
| join | partial | 0-5ms | ? | 17 | 9% | +1.53 |
| join | sweep | 1000-ms | 1000-ms | 1 | 1% | -1.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 110 | 60% | +2.14 |
| join | sweep | — | — | 72 | 40% | -0.54 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 238 | 64% | +3.18 |
| improve | sweep | 0-5ms | ? | 76 | 20% | +2.05 |
| join | sweep | 0-5ms | ? | 30 | 8% | -2.03 |
| join | sweep | 1000-ms | ? | 20 | 5% | -0.50 |
| improve | sweep | 200-1000ms | ? | 9 | 2% | +11.00 |
| join | sweep | 1000-ms | 1000-ms | 1 | 0% | -1.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 322 | 86% | +3.12 |
| join | sweep | — | — | 52 | 14% | -1.42 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 238 | 56% | +3.18 |
| improve | sweep | 0-5ms | ? | 76 | 18% | +2.05 |
| join | sweep | 0-5ms | ? | 30 | 7% | -2.03 |
| join | partial | 1000-ms | ? | 30 | 7% | +0.50 |
| join | sweep | 1000-ms | ? | 20 | 5% | -0.50 |
| improve | partial | 1000-ms | 1000-ms | 20 | 5% | +0.50 |
| improve | sweep | 200-1000ms | ? | 9 | 2% | +11.00 |
| join | sweep | 1000-ms | 1000-ms | 1 | 0% | -1.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 322 | 76% | +3.12 |
| join | sweep | — | — | 52 | 12% | -1.42 |
| join | partial | — | — | 30 | 7% | +0.50 |
| improve | partial | — | — | 20 | 5% | +0.50 |