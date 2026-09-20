# Quoter simulation, KXBUNDESLIGATOTAL, 2026-09-20

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 6 | -3.41 | 12.09 | -15.50 | -133.21 | 6 | -3.41 | 12.09 | -15.50 | -0.24 | -3.18 | -0.57 | 1.92 | -0.73 | -3.54 | 688 | -0.50 | -0.69 | 65.62 | 1.21 | 64 | 18.48 | 13.58 | 0.00 |
|  ↳ vetoes: {'priority_fills': 354} |
| touch joiner, size 5 | 6 | -0.48 | 4.04 | -4.52 | -39.05 | 6 | -0.48 | 4.04 | -4.52 | 0.37 | -0.84 | -0.08 | 0.65 | -0.30 | -0.92 | 240 | -0.20 | -0.57 | 68.57 | 0.42 | 70 | 4.65 | 2.42 | 0.00 |
|  ↳ vetoes: {'priority_fills': 277} |
| touch joiner, depth >= 50 | 6 | -1.93 | 10.74 | -12.66 | -113.51 | 6 | -1.93 | 10.74 | -12.66 | 1.52 | -3.45 | -0.32 | 1.06 | -0.74 | -2.60 | 580 | -0.33 | -0.66 | 68.75 | 1.02 | 48 | 19.50 | 13.52 | 0.00 |
|  ↳ vetoes: {'thin': 67672, 'priority_fills': 323} |
| join only, never improve | 5 | 1.50 | 5.97 | -4.46 | -97.30 | 5 | 1.50 | 5.97 | -4.46 | 0.07 | 1.43 | 0.30 | 1.93 | 0.35 | -1.94 | 513 | 0.29 | -0.45 | 0.00 | 0.91 | 37 | 15.34 | 7.66 | 0.00 |
|  ↳ vetoes: {'priority_fills': 85} |
| touch joiner, pessimistic queue | 6 | -4.94 | 10.32 | -15.26 | -135.13 | 6 | -4.94 | 10.32 | -15.26 | -1.86 | -3.07 | -0.82 | 1.81 | -1.11 | -3.98 | 623 | -0.79 | -0.88 | 83.64 | 1.09 | 55 | 20.00 | 13.66 | 0.00 |
|  ↳ vetoes: {'priority_fills': 372} |
| touch joiner, carry (no flatten) | 6 | -3.41 | 12.09 | -15.50 | -133.21 | 6 | -3.41 | 12.09 | -15.50 | -0.24 | -3.18 | -0.57 | 1.92 | -0.73 | -3.54 | 688 | -0.50 | -0.69 | 65.62 | 1.21 | 64 | 18.48 | 13.58 | 0.00 |
|  ↳ vetoes: {'priority_fills': 354} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | partial | 1000-ms | 1000-ms | 1,412 | 23% | +0.35 |
| improve | sweep | 0-5ms | ? | 1,397 | 23% | -2.18 |
| join | partial | 1000-ms | 1000-ms | 757 | 12% | +0.34 |
| improve | sweep | 1000-ms | ? | 694 | 11% | -0.79 |
| join | partial | 0-5ms | ? | 485 | 8% | -0.86 |
| improve | partial | 0-5ms | ? | 279 | 5% | -1.37 |
| improve | sweep | 200-1000ms | ? | 241 | 4% | -1.96 |
| join | sweep | 0-5ms | ? | 228 | 4% | -1.34 |
| join | partial | 1000-ms | ? | 178 | 3% | +0.25 |
| join | sweep | 1000-ms | ? | 86 | 1% | +0.59 |
| improve | sweep | 50-200ms | ? | 78 | 1% | -1.74 |
| improve | partial | 200-1000ms | 200-1000ms | 65 | 1% | -0.05 |
| improve | partial | 5-16ms | 5-16ms | 60 | 1% | +4.50 |
| improve | partial | 50-200ms | 50-200ms | 38 | 1% | +2.87 |
| improve | sweep | 16-50ms | ? | 34 | 1% | -3.04 |
| join | partial | 200-1000ms | 1000-ms | 20 | 0% | -2.50 |
| join | partial | 5-16ms | 5-16ms | 20 | 0% | -0.50 |
| improve | sweep | 1000-ms | 1000-ms | 16 | 0% | +1.50 |
| join | sweep | 16-50ms | ? | 3 | 0% | +0.50 |
| improve | partial | 16-50ms | 16-50ms | 2 | 0% | +0.50 |
| join | partial | 0-5ms | 1000-ms | 1 | 0% | +0.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 2,460 | 40% | -1.74 |
| improve | partial | — | — | 1,857 | 30% | +0.26 |
| join | partial | — | — | 1,461 | 24% | -0.12 |
| join | sweep | — | — | 318 | 5% | -0.80 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 442 | 23% | -1.72 |
| improve | partial | 1000-ms | 1000-ms | 430 | 23% | +0.34 |
| improve | sweep | 1000-ms | ? | 227 | 12% | -0.61 |
| join | partial | 1000-ms | 1000-ms | 211 | 11% | +0.39 |
| join | partial | 0-5ms | ? | 150 | 8% | -1.09 |
| improve | partial | 0-5ms | ? | 99 | 5% | -1.03 |
| improve | sweep | 200-1000ms | ? | 85 | 4% | -1.56 |
| join | sweep | 0-5ms | ? | 52 | 3% | -1.22 |
| join | partial | 1000-ms | ? | 50 | 3% | +0.27 |
| join | sweep | 1000-ms | ? | 35 | 2% | -0.07 |
| improve | partial | 200-1000ms | 200-1000ms | 25 | 1% | +0.30 |
| improve | sweep | 50-200ms | ? | 25 | 1% | +0.56 |
| improve | sweep | 16-50ms | ? | 20 | 1% | -3.52 |
| improve | partial | 50-200ms | 50-200ms | 16 | 1% | +2.06 |
| improve | partial | 5-16ms | 5-16ms | 15 | 1% | +4.50 |
| join | partial | 200-1000ms | 1000-ms | 5 | 0% | -2.50 |
| join | partial | 5-16ms | 5-16ms | 5 | 0% | -0.50 |
| join | sweep | 16-50ms | ? | 3 | 0% | +0.50 |
| improve | partial | 16-50ms | 16-50ms | 2 | 0% | +0.50 |
| improve | sweep | 1000-ms | 1000-ms | 1 | 0% | +1.50 |
| join | partial | 0-5ms | 1000-ms | 1 | 0% | +0.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 800 | 42% | -1.36 |
| improve | partial | — | — | 587 | 31% | +0.26 |
| join | partial | — | — | 422 | 22% | -0.20 |
| join | sweep | — | — | 90 | 5% | -0.72 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 1,296 | 27% | -1.94 |
| improve | partial | 1000-ms | 1000-ms | 806 | 17% | -0.21 |
| improve | sweep | 1000-ms | ? | 798 | 17% | -0.99 |
| join | partial | 1000-ms | 1000-ms | 746 | 16% | +0.86 |
| improve | sweep | 200-1000ms | ? | 206 | 4% | -1.59 |
| join | sweep | 0-5ms | ? | 199 | 4% | -0.61 |
| join | partial | 0-5ms | ? | 184 | 4% | -0.38 |
| join | partial | 1000-ms | ? | 174 | 4% | +0.23 |
| improve | partial | 5-16ms | 5-16ms | 84 | 2% | +3.43 |
| improve | partial | 0-5ms | ? | 65 | 1% | +0.15 |
| improve | sweep | 50-200ms | ? | 56 | 1% | -0.97 |
| improve | sweep | 16-50ms | ? | 44 | 1% | -3.51 |
| join | sweep | 1000-ms | ? | 40 | 1% | +0.50 |
| improve | partial | 200-1000ms | 200-1000ms | 35 | 1% | -1.08 |
| improve | partial | 50-200ms | 50-200ms | 30 | 1% | +3.50 |
| join | partial | 0-5ms | 1000-ms | 1 | 0% | +0.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 2,400 | 50% | -1.60 |
| join | partial | — | — | 1,104 | 23% | +0.55 |
| improve | partial | — | — | 1,021 | 21% | +0.20 |
| join | sweep | — | — | 239 | 5% | -0.42 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 1,956 | 44% | +0.35 |
| join | partial | 0-5ms | ? | 1,422 | 32% | -0.65 |
| join | sweep | 0-5ms | ? | 575 | 13% | -3.31 |
| join | partial | 1000-ms | ? | 250 | 6% | +0.37 |
| join | partial | 200-1000ms | 200-1000ms | 69 | 2% | +2.17 |
| join | sweep | 1000-ms | 1000-ms | 46 | 1% | -4.98 |
| join | partial | 50-200ms | 50-200ms | 32 | 1% | +4.83 |
| join | partial | 200-1000ms | 1000-ms | 31 | 1% | -2.56 |
| join | sweep | 50-200ms | 50-200ms | 20 | 0% | +3.50 |
| join | sweep | 5-16ms | ? | 4 | 0% | -3.50 |
| join | partial | 0-5ms | 1000-ms | 1 | 0% | +0.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 3,762 | 85% | +0.02 |
| join | sweep | — | — | 645 | 15% | -3.22 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | partial | 1000-ms | 1000-ms | 1,444 | 26% | +0.15 |
| improve | sweep | 0-5ms | ? | 1,420 | 25% | -2.36 |
| improve | sweep | 1000-ms | ? | 701 | 13% | -1.06 |
| join | sweep | 0-5ms | ? | 436 | 8% | -0.99 |
| join | partial | 1000-ms | 1000-ms | 395 | 7% | -0.02 |
| improve | partial | 0-5ms | ? | 312 | 6% | -1.08 |
| improve | sweep | 200-1000ms | ? | 251 | 5% | -1.61 |
| join | partial | 0-5ms | ? | 190 | 3% | -0.34 |
| join | sweep | 1000-ms | ? | 106 | 2% | +0.38 |
| improve | sweep | 50-200ms | ? | 83 | 1% | -0.97 |
| improve | partial | 200-1000ms | 200-1000ms | 65 | 1% | -0.05 |
| improve | partial | 5-16ms | 5-16ms | 60 | 1% | +4.50 |
| improve | partial | 50-200ms | 50-200ms | 38 | 1% | +2.87 |
| improve | sweep | 16-50ms | ? | 33 | 1% | -3.17 |
| improve | sweep | 1000-ms | 1000-ms | 16 | 0% | +1.50 |
| join | partial | 200-1000ms | 1000-ms | 16 | 0% | -2.50 |
| join | sweep | 16-50ms | ? | 3 | 0% | +0.50 |
| improve | partial | 16-50ms | 16-50ms | 2 | 0% | +0.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 2,505 | 45% | -1.86 |
| improve | partial | — | — | 1,922 | 34% | +0.13 |
| join | partial | — | — | 601 | 11% | -0.19 |
| join | sweep | — | — | 545 | 10% | -0.71 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | partial | 1000-ms | 1000-ms | 1,412 | 23% | +0.35 |
| improve | sweep | 0-5ms | ? | 1,397 | 23% | -2.18 |
| join | partial | 1000-ms | 1000-ms | 757 | 12% | +0.34 |
| improve | sweep | 1000-ms | ? | 694 | 11% | -0.79 |
| join | partial | 0-5ms | ? | 485 | 8% | -0.86 |
| improve | partial | 0-5ms | ? | 279 | 5% | -1.37 |
| improve | sweep | 200-1000ms | ? | 241 | 4% | -1.96 |
| join | sweep | 0-5ms | ? | 228 | 4% | -1.34 |
| join | partial | 1000-ms | ? | 178 | 3% | +0.25 |
| join | sweep | 1000-ms | ? | 86 | 1% | +0.59 |
| improve | sweep | 50-200ms | ? | 78 | 1% | -1.74 |
| improve | partial | 200-1000ms | 200-1000ms | 65 | 1% | -0.05 |
| improve | partial | 5-16ms | 5-16ms | 60 | 1% | +4.50 |
| improve | partial | 50-200ms | 50-200ms | 38 | 1% | +2.87 |
| improve | sweep | 16-50ms | ? | 34 | 1% | -3.04 |
| join | partial | 200-1000ms | 1000-ms | 20 | 0% | -2.50 |
| join | partial | 5-16ms | 5-16ms | 20 | 0% | -0.50 |
| improve | sweep | 1000-ms | 1000-ms | 16 | 0% | +1.50 |
| join | sweep | 16-50ms | ? | 3 | 0% | +0.50 |
| improve | partial | 16-50ms | 16-50ms | 2 | 0% | +0.50 |
| join | partial | 0-5ms | 1000-ms | 1 | 0% | +0.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 2,460 | 40% | -1.74 |
| improve | partial | — | — | 1,857 | 30% | +0.26 |
| join | partial | — | — | 1,461 | 24% | -0.12 |
| join | sweep | — | — | 318 | 5% | -0.80 |