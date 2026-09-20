# Quoter simulation, KXLIGUE1TOTAL, 2026-09-20

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 4 | 0.10 | 0.59 | -0.50 | -81.83 | 4 | 0.10 | 0.59 | -0.50 | 0.00 | 0.10 | 0.02 | 0.18 | 0.27 | -0.20 | 121 | 0.08 | -0.53 | 33.33 | 2.01 | 9 | 15.25 | 10.25 | 0.00 |
|  ↳ vetoes: {'priority_fills': 198} |
| touch joiner, size 5 | 4 | 0.02 | 0.14 | -0.12 | -23.55 | 4 | 0.02 | 0.14 | -0.12 | 0.00 | 0.02 | 0.01 | 0.04 | 0.22 | -0.05 | 31 | 0.06 | -0.46 | 33.33 | 0.52 | 9 | 4.00 | 2.75 | 0.00 |
|  ↳ vetoes: {'priority_fills': 149} |
| touch joiner, depth >= 50 | 3 | 0.10 | 0.59 | -0.49 | -81.01 | 3 | 0.10 | 0.59 | -0.49 | 0.00 | 0.10 | 0.03 | 0.21 | 0.28 | -0.20 | 120 | 0.08 | -0.58 | 37.50 | 3.36 | 8 | 20.00 | 13.33 | 0.00 |
|  ↳ vetoes: {'thin': 24010, 'priority_fills': 193} |
| join only, never improve | 4 | -0.10 | 0.41 | -0.51 | -59.42 | 4 | -0.10 | 0.41 | -0.51 | -0.19 | 0.09 | -0.03 | 0.11 | -0.46 | -0.20 | 82 | -0.12 | -0.82 | 0.00 | 1.36 | 7 | 15.03 | 10.03 | 0.00 |
|  ↳ vetoes: {'priority_fills': 62} |
| touch joiner, pessimistic queue | 1 | 0.01 | 0.09 | -0.08 | -76.98 | 1 | 0.01 | 0.09 | -0.08 | 0.00 | 0.01 | 0.01 | 0.00 | nan | 0.01 | 38 | 0.03 | -0.50 | 100.00 | 2.36 | 4 | 17.89 | 2.11 | 0.00 |
|  ↳ vetoes: {'priority_fills': 214} |
| touch joiner, carry (no flatten) | 4 | 0.10 | 0.59 | -0.50 | -81.83 | 4 | 0.10 | 0.59 | -0.50 | 0.00 | 0.10 | 0.02 | 0.18 | 0.27 | -0.20 | 121 | 0.08 | -0.53 | 33.33 | 2.01 | 9 | 15.25 | 10.25 | 0.00 |
|  ↳ vetoes: {'priority_fills': 198} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 848 | 25% | +0.06 |
| improve | sweep | 1000-ms | ? | 708 | 20% | -1.13 |
| improve | partial | 1000-ms | 1000-ms | 580 | 17% | +0.20 |
| improve | partial | 0-5ms | ? | 342 | 10% | -1.27 |
| join | partial | 1000-ms | 1000-ms | 242 | 7% | -2.07 |
| join | sweep | 0-5ms | ? | 187 | 5% | -2.79 |
| join | partial | 0-5ms | ? | 178 | 5% | +0.67 |
| improve | sweep | 200-1000ms | ? | 97 | 3% | -2.69 |
| join | partial | 1000-ms | ? | 80 | 2% | +0.50 |
| improve | sweep | 50-200ms | ? | 45 | 1% | +6.22 |
| improve | partial | 200-1000ms | 200-1000ms | 40 | 1% | -2.83 |
| join | sweep | 1000-ms | ? | 40 | 1% | +0.50 |
| improve | sweep | 16-50ms | ? | 32 | 1% | +5.84 |
| join | sweep | 200-1000ms | ? | 20 | 1% | -1.00 |
| join | sweep | 200-1000ms | 200-1000ms | 20 | 1% | +0.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 1,730 | 50% | -0.31 |
| improve | partial | — | — | 963 | 28% | -0.45 |
| join | partial | — | — | 501 | 14% | -0.69 |
| join | sweep | — | — | 267 | 8% | -1.95 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 222 | 22% | -0.05 |
| improve | sweep | 1000-ms | ? | 212 | 21% | -1.38 |
| improve | partial | 1000-ms | 1000-ms | 164 | 16% | +0.18 |
| improve | partial | 0-5ms | ? | 108 | 11% | -0.95 |
| join | partial | 1000-ms | 1000-ms | 69 | 7% | -2.30 |
| join | sweep | 0-5ms | ? | 60 | 6% | -2.50 |
| join | partial | 0-5ms | ? | 60 | 6% | +0.84 |
| improve | sweep | 200-1000ms | ? | 30 | 3% | -0.35 |
| improve | sweep | 50-200ms | ? | 24 | 2% | +6.56 |
| join | partial | 1000-ms | ? | 20 | 2% | +0.50 |
| improve | partial | 200-1000ms | 200-1000ms | 11 | 1% | -3.09 |
| join | sweep | 1000-ms | ? | 10 | 1% | +0.50 |
| improve | sweep | 16-50ms | ? | 7 | 1% | +6.00 |
| join | sweep | 200-1000ms | ? | 7 | 1% | +0.86 |
| join | sweep | 200-1000ms | 200-1000ms | 5 | 0% | +0.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 495 | 49% | -0.23 |
| improve | partial | — | — | 283 | 28% | -0.38 |
| join | partial | — | — | 149 | 15% | -0.67 |
| join | sweep | — | — | 82 | 8% | -1.70 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 810 | 29% | +0.38 |
| improve | sweep | 1000-ms | ? | 786 | 28% | -1.50 |
| improve | partial | 1000-ms | 1000-ms | 362 | 13% | -0.05 |
| join | partial | 1000-ms | 1000-ms | 244 | 9% | -0.69 |
| improve | sweep | 200-1000ms | ? | 121 | 4% | -1.89 |
| join | sweep | 0-5ms | ? | 120 | 4% | -3.42 |
| improve | partial | 0-5ms | ? | 83 | 3% | -1.21 |
| join | partial | 1000-ms | ? | 80 | 3% | +0.50 |
| join | partial | 0-5ms | ? | 73 | 3% | -4.94 |
| improve | sweep | 50-200ms | ? | 71 | 3% | +5.39 |
| improve | sweep | 16-50ms | ? | 32 | 1% | +5.84 |
| improve | partial | 200-1000ms | 200-1000ms | 19 | 1% | -4.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 1,820 | 65% | -0.29 |
| improve | partial | — | — | 464 | 17% | -0.42 |
| join | partial | — | — | 397 | 14% | -1.23 |
| join | sweep | — | — | 120 | 4% | -3.42 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 743 | 34% | -0.80 |
| join | partial | 0-5ms | ? | 687 | 32% | -0.46 |
| join | sweep | 0-5ms | ? | 550 | 25% | -1.37 |
| join | partial | 1000-ms | ? | 140 | 6% | -0.73 |
| join | partial | 50-200ms | 50-200ms | 20 | 1% | +1.97 |
| join | sweep | 50-200ms | 50-200ms | 19 | 1% | -2.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 1,589 | 74% | -0.61 |
| join | sweep | — | — | 569 | 26% | -1.39 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 834 | 26% | -0.03 |
| improve | sweep | 1000-ms | ? | 727 | 23% | -1.10 |
| improve | partial | 1000-ms | 1000-ms | 517 | 16% | +0.31 |
| improve | partial | 0-5ms | ? | 353 | 11% | -1.27 |
| join | sweep | 0-5ms | ? | 318 | 10% | -0.21 |
| improve | sweep | 200-1000ms | ? | 97 | 3% | -2.69 |
| join | sweep | 1000-ms | ? | 60 | 2% | -0.67 |
| improve | sweep | 50-200ms | ? | 56 | 2% | +6.53 |
| join | partial | 0-5ms | ? | 40 | 1% | -12.25 |
| join | partial | 1000-ms | 1000-ms | 40 | 1% | -0.25 |
| join | sweep | 200-1000ms | ? | 40 | 1% | -1.25 |
| improve | partial | 200-1000ms | 200-1000ms | 39 | 1% | -2.73 |
| improve | sweep | 16-50ms | ? | 37 | 1% | +4.58 |
| join | sweep | 200-1000ms | 200-1000ms | 20 | 1% | +0.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 1,751 | 55% | -0.31 |
| improve | partial | — | — | 910 | 29% | -0.44 |
| join | sweep | — | — | 438 | 14% | -0.36 |
| join | partial | — | — | 80 | 3% | -6.25 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 848 | 25% | +0.06 |
| improve | sweep | 1000-ms | ? | 708 | 20% | -1.13 |
| improve | partial | 1000-ms | 1000-ms | 580 | 17% | +0.20 |
| improve | partial | 0-5ms | ? | 342 | 10% | -1.27 |
| join | partial | 1000-ms | 1000-ms | 242 | 7% | -2.07 |
| join | sweep | 0-5ms | ? | 187 | 5% | -2.79 |
| join | partial | 0-5ms | ? | 178 | 5% | +0.67 |
| improve | sweep | 200-1000ms | ? | 97 | 3% | -2.69 |
| join | partial | 1000-ms | ? | 80 | 2% | +0.50 |
| improve | sweep | 50-200ms | ? | 45 | 1% | +6.22 |
| improve | partial | 200-1000ms | 200-1000ms | 40 | 1% | -2.83 |
| join | sweep | 1000-ms | ? | 40 | 1% | +0.50 |
| improve | sweep | 16-50ms | ? | 32 | 1% | +5.84 |
| join | sweep | 200-1000ms | ? | 20 | 1% | -1.00 |
| join | sweep | 200-1000ms | 200-1000ms | 20 | 1% | +0.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 1,730 | 50% | -0.31 |
| improve | partial | — | — | 963 | 28% | -0.45 |
| join | partial | — | — | 501 | 14% | -0.69 |
| join | sweep | — | — | 267 | 8% | -1.95 |