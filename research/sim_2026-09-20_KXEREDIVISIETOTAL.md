# Quoter simulation, KXEREDIVISIETOTAL, 2026-09-20

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 4 | 8.70 | 36.34 | -27.64 | -205.41 | 4 | 8.70 | 36.34 | -27.64 | 11.84 | -3.14 | 2.18 | 9.68 | 0.45 | -10.44 | 969 | 0.90 | -0.49 | 83.02 | 3.28 | 106 | 20.00 | 15.22 | 0.00 |
|  ↳ vetoes: {'priority_fills': 424} |
| touch joiner, size 5 | 4 | 1.93 | 11.25 | -9.32 | -56.88 | 4 | 1.93 | 11.25 | -9.32 | 2.16 | -0.23 | 0.48 | 2.44 | 0.40 | -2.77 | 285 | 0.68 | -0.30 | 80.65 | 0.96 | 93 | 5.00 | 3.36 | 0.00 |
|  ↳ vetoes: {'priority_fills': 344} |
| touch joiner, depth >= 50 | 4 | -3.76 | 36.03 | -39.79 | -195.49 | 4 | -3.76 | 36.03 | -39.79 | 3.92 | -7.68 | -0.94 | 5.40 | -0.35 | -9.96 | 835 | -0.45 | -0.41 | 94.12 | 2.83 | 85 | 20.00 | 17.27 | 0.00 |
|  ↳ vetoes: {'thin': 93667, 'priority_fills': 417} |
| join only, never improve | 3 | 10.03 | 35.43 | -25.40 | -163.18 | 3 | 10.03 | 35.43 | -25.40 | 17.87 | -7.84 | 3.34 | 5.40 | 1.07 | -0.93 | 648 | 1.55 | -0.46 | 0.00 | 2.34 | 73 | 20.00 | 14.48 | 0.00 |
|  ↳ vetoes: {'priority_fills': 155} |
| touch joiner, pessimistic queue | 4 | 8.67 | 35.94 | -27.27 | -206.93 | 4 | 8.67 | 35.94 | -27.27 | 11.74 | -3.07 | 2.17 | 9.80 | 0.44 | -10.64 | 889 | 0.98 | -0.39 | 91.40 | 3.01 | 93 | 20.00 | 15.24 | 0.00 |
|  ↳ vetoes: {'priority_fills': 449} |
| touch joiner, carry (no flatten) | 4 | 8.70 | 36.34 | -27.64 | -205.41 | 4 | 8.70 | 36.34 | -27.64 | 11.84 | -3.14 | 2.18 | 9.68 | 0.45 | -10.44 | 969 | 0.90 | -0.49 | 83.02 | 3.28 | 106 | 20.00 | 15.22 | 0.00 |
|  ↳ vetoes: {'priority_fills': 424} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 2,112 | 31% | -1.44 |
| improve | sweep | 1000-ms | ? | 1,306 | 19% | +0.37 |
| improve | partial | 1000-ms | 1000-ms | 1,291 | 19% | -0.62 |
| join | partial | 0-5ms | ? | 571 | 8% | -0.15 |
| join | partial | 1000-ms | 1000-ms | 359 | 5% | +0.89 |
| improve | partial | 0-5ms | ? | 304 | 5% | -1.84 |
| join | sweep | 0-5ms | ? | 292 | 4% | +0.08 |
| improve | sweep | 200-1000ms | ? | 175 | 3% | +2.47 |
| join | partial | 1000-ms | ? | 125 | 2% | +0.02 |
| improve | sweep | 50-200ms | ? | 75 | 1% | -1.16 |
| join | sweep | 1000-ms | ? | 40 | 1% | -1.25 |
| improve | partial | 200-1000ms | 200-1000ms | 37 | 1% | +0.27 |
| improve | partial | 50-200ms | 50-200ms | 21 | 0% | +0.26 |
| join | sweep | 50-200ms | ? | 20 | 0% | +0.50 |
| improve | partial | 0-5ms | 0-5ms | 5 | 0% | +6.00 |
| improve | partial | 16-50ms | 16-50ms | 1 | 0% | -3.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 3,668 | 54% | -0.60 |
| improve | partial | — | — | 1,660 | 25% | -0.79 |
| join | partial | — | — | 1,055 | 16% | +0.22 |
| join | sweep | — | — | 352 | 5% | -0.05 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 614 | 31% | -0.99 |
| improve | sweep | 1000-ms | ? | 390 | 19% | +0.55 |
| improve | partial | 1000-ms | 1000-ms | 388 | 19% | -0.41 |
| join | partial | 0-5ms | ? | 189 | 9% | -0.45 |
| join | partial | 1000-ms | 1000-ms | 118 | 6% | +0.99 |
| improve | partial | 0-5ms | ? | 94 | 5% | -2.08 |
| join | sweep | 0-5ms | ? | 72 | 4% | -0.30 |
| improve | sweep | 200-1000ms | ? | 55 | 3% | +2.20 |
| join | partial | 1000-ms | ? | 35 | 2% | +0.07 |
| improve | sweep | 50-200ms | ? | 31 | 2% | -0.47 |
| improve | partial | 200-1000ms | 200-1000ms | 10 | 0% | +0.25 |
| improve | partial | 50-200ms | 50-200ms | 6 | 0% | -0.30 |
| join | sweep | 1000-ms | ? | 5 | 0% | -0.50 |
| improve | partial | 0-5ms | 0-5ms | 4 | 0% | +6.00 |
| improve | partial | 16-50ms | 16-50ms | 1 | 0% | -3.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 1,091 | 54% | -0.26 |
| improve | partial | — | — | 504 | 25% | -0.66 |
| join | partial | — | — | 341 | 17% | +0.10 |
| join | sweep | — | — | 77 | 4% | -0.31 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 2,173 | 36% | -1.80 |
| improve | sweep | 1000-ms | ? | 1,314 | 22% | +0.35 |
| improve | partial | 1000-ms | 1000-ms | 821 | 14% | -0.72 |
| join | partial | 0-5ms | ? | 416 | 7% | +1.23 |
| join | partial | 1000-ms | 1000-ms | 414 | 7% | +1.52 |
| improve | sweep | 200-1000ms | ? | 197 | 3% | +2.46 |
| join | sweep | 0-5ms | ? | 174 | 3% | +2.44 |
| improve | partial | 0-5ms | ? | 150 | 3% | -2.77 |
| improve | sweep | 50-200ms | ? | 110 | 2% | -0.95 |
| join | partial | 1000-ms | ? | 103 | 2% | +0.11 |
| improve | partial | 200-1000ms | 200-1000ms | 37 | 1% | +0.27 |
| improve | partial | 50-200ms | 50-200ms | 20 | 0% | +0.50 |
| join | sweep | 1000-ms | ? | 20 | 0% | +0.50 |
| improve | partial | 0-5ms | 0-5ms | 5 | 0% | +6.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 3,793 | 64% | -0.81 |
| improve | partial | — | — | 1,034 | 17% | -0.92 |
| join | partial | — | — | 932 | 16% | +1.24 |
| join | sweep | — | — | 194 | 3% | +2.24 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 0-5ms | ? | 1,653 | 35% | -1.07 |
| join | partial | 1000-ms | 1000-ms | 1,517 | 32% | -0.14 |
| join | sweep | 0-5ms | ? | 1,359 | 29% | +0.16 |
| join | partial | 1000-ms | ? | 160 | 3% | +1.82 |
| join | sweep | 1000-ms | 1000-ms | 40 | 1% | -18.25 |
| join | sweep | 5-16ms | ? | 5 | 0% | +0.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 3,330 | 70% | -0.51 |
| join | sweep | — | — | 1,404 | 30% | -0.36 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 2,217 | 36% | -1.23 |
| improve | sweep | 1000-ms | ? | 1,300 | 21% | +0.23 |
| improve | partial | 1000-ms | 1000-ms | 1,142 | 19% | -0.41 |
| join | sweep | 0-5ms | ? | 507 | 8% | -0.19 |
| improve | partial | 0-5ms | ? | 264 | 4% | -2.11 |
| join | partial | 0-5ms | ? | 206 | 3% | +3.67 |
| improve | sweep | 200-1000ms | ? | 175 | 3% | +2.47 |
| join | partial | 1000-ms | 1000-ms | 161 | 3% | +0.08 |
| improve | sweep | 50-200ms | ? | 57 | 1% | -0.88 |
| join | sweep | 1000-ms | ? | 40 | 1% | -1.25 |
| improve | partial | 200-1000ms | 200-1000ms | 37 | 1% | +0.27 |
| join | sweep | 50-200ms | ? | 20 | 0% | +0.50 |
| join | partial | 1000-ms | ? | 5 | 0% | -0.50 |
| improve | partial | 0-5ms | 0-5ms | 5 | 0% | +6.00 |
| improve | partial | 50-200ms | 50-200ms | 1 | 0% | -3.50 |
| improve | partial | 16-50ms | 16-50ms | 1 | 0% | -3.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 3,749 | 61% | -0.55 |
| improve | partial | — | — | 1,451 | 24% | -0.69 |
| join | sweep | — | — | 567 | 9% | -0.24 |
| join | partial | — | — | 372 | 6% | +2.06 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 2,112 | 31% | -1.44 |
| improve | sweep | 1000-ms | ? | 1,306 | 19% | +0.37 |
| improve | partial | 1000-ms | 1000-ms | 1,291 | 19% | -0.62 |
| join | partial | 0-5ms | ? | 571 | 8% | -0.15 |
| join | partial | 1000-ms | 1000-ms | 359 | 5% | +0.89 |
| improve | partial | 0-5ms | ? | 304 | 5% | -1.84 |
| join | sweep | 0-5ms | ? | 292 | 4% | +0.08 |
| improve | sweep | 200-1000ms | ? | 175 | 3% | +2.47 |
| join | partial | 1000-ms | ? | 125 | 2% | +0.02 |
| improve | sweep | 50-200ms | ? | 75 | 1% | -1.16 |
| join | sweep | 1000-ms | ? | 40 | 1% | -1.25 |
| improve | partial | 200-1000ms | 200-1000ms | 37 | 1% | +0.27 |
| improve | partial | 50-200ms | 50-200ms | 21 | 0% | +0.26 |
| join | sweep | 50-200ms | ? | 20 | 0% | +0.50 |
| improve | partial | 0-5ms | 0-5ms | 5 | 0% | +6.00 |
| improve | partial | 16-50ms | 16-50ms | 1 | 0% | -3.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 3,668 | 54% | -0.60 |
| improve | partial | — | — | 1,660 | 25% | -0.79 |
| join | partial | — | — | 1,055 | 16% | +0.22 |
| join | sweep | — | — | 352 | 5% | -0.05 |