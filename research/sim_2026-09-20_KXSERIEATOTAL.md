# Quoter simulation, KXSERIEATOTAL, 2026-09-20

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 2 | 0.31 | 0.31 | 0.00 | -244.89 | 2 | 0.31 | 0.31 | 0.00 | 0.17 | 0.14 | 0.15 | 0.05 | 4.04 | 0.10 | 62 | 0.50 | -0.32 | 0.00 | 0.72 | 4 | 16.23 | 13.77 | 0.00 |
|  ↳ vetoes: {'priority_fills': 951} |
| touch joiner, size 5 | 2 | 0.10 | 0.10 | 0.00 | -75.65 | 2 | 0.10 | 0.10 | 0.00 | 0.05 | 0.05 | 0.05 | 0.02 | 2.89 | 0.02 | 20 | 0.50 | -0.33 | 0.00 | 0.23 | 4 | 4.78 | 4.78 | 0.00 |
|  ↳ vetoes: {'priority_fills': 589} |
| touch joiner, depth >= 50 | 2 | 0.31 | 0.31 | 0.00 | -224.89 | 2 | 0.31 | 0.31 | 0.00 | 0.17 | 0.14 | 0.15 | 0.05 | 4.04 | 0.10 | 62 | 0.50 | -0.32 | 0.00 | 0.72 | 4 | 16.23 | 13.77 | 0.00 |
|  ↳ vetoes: {'thin': 151490, 'priority_fills': 852} |
| join only, never improve | 2 | 0.31 | 0.31 | 0.00 | -189.80 | 2 | 0.31 | 0.31 | 0.00 | 0.17 | 0.14 | 0.15 | 0.05 | 4.04 | 0.10 | 62 | 0.50 | 0.06 | 0.00 | 0.72 | 4 | 16.23 | 13.77 | 0.00 |
|  ↳ vetoes: {'priority_fills': 322} |
| touch joiner, pessimistic queue | 1 | 0.10 | 0.10 | 0.00 | -246.12 | 1 | 0.10 | 0.10 | 0.00 | 0.00 | 0.10 | 0.10 | 0.00 | nan | 0.10 | 20 | 0.50 | -0.40 | 0.00 | 0.30 | 1 | 20.00 | 20.00 | 0.00 |
|  ↳ vetoes: {'priority_fills': 988} |
| touch joiner, carry (no flatten) | 2 | 0.31 | 0.31 | 0.00 | -244.89 | 2 | 0.31 | 0.31 | 0.00 | 0.17 | 0.14 | 0.15 | 0.05 | 4.04 | 0.10 | 62 | 0.50 | -0.32 | 0.00 | 0.72 | 4 | 16.23 | 13.77 | 0.00 |
|  ↳ vetoes: {'priority_fills': 951} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 3,922 | 27% | -0.86 |
| improve | sweep | 1000-ms | ? | 2,332 | 16% | -0.42 |
| improve | partial | 1000-ms | 1000-ms | 2,237 | 15% | -0.05 |
| join | partial | 1000-ms | 1000-ms | 1,658 | 11% | +0.11 |
| join | partial | 0-5ms | ? | 1,198 | 8% | +0.20 |
| improve | partial | 0-5ms | ? | 844 | 6% | -0.50 |
| join | sweep | 0-5ms | ? | 614 | 4% | -1.11 |
| join | partial | 1000-ms | ? | 587 | 4% | +0.48 |
| improve | sweep | 200-1000ms | ? | 236 | 2% | -1.45 |
| join | sweep | 1000-ms | ? | 173 | 1% | +2.51 |
| improve | partial | 200-1000ms | 200-1000ms | 166 | 1% | -0.37 |
| improve | sweep | 50-200ms | ? | 139 | 1% | +2.22 |
| improve | partial | 50-200ms | 50-200ms | 121 | 1% | +1.63 |
| improve | sweep | 16-50ms | ? | 96 | 1% | -0.81 |
| improve | partial | 5-16ms | 5-16ms | 42 | 0% | -1.07 |
| join | sweep | 1000-ms | 1000-ms | 41 | 0% | -10.23 |
| improve | sweep | 1000-ms | 1000-ms | 34 | 0% | +1.82 |
| improve | partial | 16-50ms | 16-50ms | 30 | 0% | +2.02 |
| join | partial | 200-1000ms | 200-1000ms | 23 | 0% | +6.84 |
| join | sweep | 5-16ms | ? | 20 | 0% | -1.50 |
| join | sweep | 200-1000ms | ? | 20 | 0% | +1.50 |
| join | sweep | 50-200ms | ? | 17 | 0% | -1.00 |
| improve | sweep | 5-16ms | ? | 10 | 0% | -9.71 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 6,769 | 46% | -0.67 |
| join | partial | — | — | 3,467 | 24% | +0.25 |
| improve | partial | — | — | 3,441 | 24% | -0.11 |
| join | sweep | — | — | 884 | 6% | -0.78 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 1,112 | 25% | -0.87 |
| improve | sweep | 1000-ms | ? | 683 | 16% | -0.11 |
| improve | partial | 1000-ms | 1000-ms | 666 | 15% | -0.22 |
| join | partial | 1000-ms | 1000-ms | 473 | 11% | +0.08 |
| join | partial | 0-5ms | ? | 408 | 9% | +0.16 |
| improve | partial | 0-5ms | ? | 319 | 7% | -0.73 |
| join | sweep | 0-5ms | ? | 160 | 4% | -1.14 |
| join | partial | 1000-ms | ? | 153 | 3% | +0.52 |
| improve | sweep | 200-1000ms | ? | 103 | 2% | -2.11 |
| improve | sweep | 50-200ms | ? | 70 | 2% | +1.71 |
| improve | sweep | 16-50ms | ? | 51 | 1% | -0.77 |
| join | sweep | 1000-ms | ? | 50 | 1% | +2.20 |
| improve | partial | 200-1000ms | 200-1000ms | 43 | 1% | -0.70 |
| improve | partial | 50-200ms | 50-200ms | 38 | 1% | +1.51 |
| join | partial | 200-1000ms | 200-1000ms | 14 | 0% | +3.74 |
| improve | partial | 16-50ms | 16-50ms | 14 | 0% | +2.61 |
| improve | partial | 5-16ms | 5-16ms | 12 | 0% | -1.25 |
| join | sweep | 1000-ms | 1000-ms | 11 | 0% | -9.48 |
| join | sweep | 200-1000ms | ? | 5 | 0% | +1.50 |
| join | sweep | 50-200ms | ? | 5 | 0% | -1.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 2,019 | 46% | -0.58 |
| improve | partial | — | — | 1,091 | 25% | -0.31 |
| join | partial | — | — | 1,048 | 24% | +0.22 |
| join | sweep | — | — | 231 | 5% | -0.76 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 3,564 | 32% | -0.53 |
| improve | sweep | 1000-ms | ? | 2,238 | 20% | -0.56 |
| join | partial | 1000-ms | 1000-ms | 1,451 | 13% | -0.69 |
| improve | partial | 1000-ms | 1000-ms | 1,170 | 10% | +0.25 |
| join | partial | 0-5ms | ? | 804 | 7% | +0.27 |
| join | partial | 1000-ms | ? | 546 | 5% | +0.28 |
| join | sweep | 0-5ms | ? | 357 | 3% | -1.10 |
| improve | sweep | 200-1000ms | ? | 302 | 3% | +0.29 |
| improve | partial | 0-5ms | ? | 195 | 2% | +0.40 |
| improve | sweep | 50-200ms | ? | 146 | 1% | +2.03 |
| join | sweep | 1000-ms | ? | 120 | 1% | +1.85 |
| improve | sweep | 16-50ms | ? | 94 | 1% | -1.03 |
| join | partial | 200-1000ms | 200-1000ms | 63 | 1% | +3.45 |
| improve | partial | 5-16ms | 5-16ms | 42 | 0% | -1.07 |
| improve | partial | 16-50ms | 16-50ms | 38 | 0% | +1.62 |
| improve | partial | 50-200ms | 50-200ms | 38 | 0% | +0.53 |
| improve | partial | 200-1000ms | 200-1000ms | 38 | 0% | -5.16 |
| improve | partial | 0-5ms | 0-5ms | 20 | 0% | -14.50 |
| join | sweep | 200-1000ms | ? | 18 | 0% | -1.00 |
| join | sweep | 50-200ms | ? | 17 | 0% | -1.00 |
| join | partial | 0-5ms | 1000-ms | 16 | 0% | +0.50 |
| improve | sweep | 1000-ms | 1000-ms | 12 | 0% | +1.50 |
| improve | sweep | 5-16ms | ? | 5 | 0% | -21.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 6,362 | 56% | -0.46 |
| join | partial | — | — | 2,879 | 25% | -0.14 |
| improve | partial | — | — | 1,541 | 14% | -0.05 |
| join | sweep | — | — | 512 | 5% | -0.40 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 4,217 | 37% | +0.10 |
| join | partial | 0-5ms | ? | 3,662 | 32% | +0.61 |
| join | sweep | 0-5ms | ? | 2,547 | 22% | -0.41 |
| join | partial | 1000-ms | ? | 628 | 6% | +0.35 |
| join | sweep | 1000-ms | 1000-ms | 107 | 1% | -0.55 |
| join | partial | 200-1000ms | 200-1000ms | 87 | 1% | +2.02 |
| join | sweep | 200-1000ms | 200-1000ms | 53 | 0% | -5.21 |
| join | sweep | 200-1000ms | ? | 20 | 0% | -27.00 |
| join | sweep | 5-16ms | ? | 14 | 0% | -20.00 |
| join | sweep | 16-50ms | 16-50ms | 6 | 0% | -20.00 |
| join | partial | 50-200ms | 50-200ms | 2 | 0% | -4.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 8,596 | 76% | +0.36 |
| join | sweep | — | — | 2,748 | 24% | -0.85 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 4,155 | 32% | -1.10 |
| improve | partial | 1000-ms | 1000-ms | 2,251 | 17% | -0.05 |
| improve | sweep | 1000-ms | ? | 2,199 | 17% | -0.18 |
| join | sweep | 0-5ms | ? | 1,043 | 8% | -0.42 |
| improve | partial | 0-5ms | ? | 792 | 6% | -0.47 |
| join | partial | 1000-ms | 1000-ms | 699 | 5% | -0.32 |
| join | partial | 0-5ms | ? | 480 | 4% | +0.15 |
| improve | sweep | 200-1000ms | ? | 291 | 2% | -0.59 |
| join | sweep | 1000-ms | ? | 212 | 2% | +3.79 |
| improve | sweep | 50-200ms | ? | 147 | 1% | +1.94 |
| improve | partial | 200-1000ms | 200-1000ms | 146 | 1% | -0.62 |
| improve | partial | 50-200ms | 50-200ms | 119 | 1% | +1.50 |
| join | partial | 1000-ms | ? | 82 | 1% | +1.47 |
| improve | sweep | 16-50ms | ? | 74 | 1% | -2.21 |
| improve | sweep | 1000-ms | 1000-ms | 54 | 0% | -1.63 |
| improve | partial | 5-16ms | 5-16ms | 42 | 0% | -1.07 |
| join | partial | 200-1000ms | 200-1000ms | 36 | 0% | +1.67 |
| improve | partial | 16-50ms | 16-50ms | 30 | 0% | +2.02 |
| join | sweep | 1000-ms | 1000-ms | 21 | 0% | -0.50 |
| join | sweep | 200-1000ms | ? | 20 | 0% | +1.50 |
| join | sweep | 5-16ms | ? | 20 | 0% | -1.50 |
| join | sweep | 50-200ms | ? | 17 | 0% | -1.00 |
| improve | sweep | 5-16ms | ? | 10 | 0% | -9.71 |
| improve | partial | 0-5ms | 1000-ms | 10 | 0% | +0.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 6,930 | 54% | -0.75 |
| improve | partial | — | — | 3,390 | 26% | -0.11 |
| join | sweep | — | — | 1,333 | 10% | +0.26 |
| join | partial | — | — | 1,297 | 10% | +0.03 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 3,922 | 27% | -0.86 |
| improve | sweep | 1000-ms | ? | 2,332 | 16% | -0.42 |
| improve | partial | 1000-ms | 1000-ms | 2,237 | 15% | -0.05 |
| join | partial | 1000-ms | 1000-ms | 1,658 | 11% | +0.11 |
| join | partial | 0-5ms | ? | 1,198 | 8% | +0.20 |
| improve | partial | 0-5ms | ? | 844 | 6% | -0.50 |
| join | sweep | 0-5ms | ? | 614 | 4% | -1.11 |
| join | partial | 1000-ms | ? | 587 | 4% | +0.48 |
| improve | sweep | 200-1000ms | ? | 236 | 2% | -1.45 |
| join | sweep | 1000-ms | ? | 173 | 1% | +2.51 |
| improve | partial | 200-1000ms | 200-1000ms | 166 | 1% | -0.37 |
| improve | sweep | 50-200ms | ? | 139 | 1% | +2.22 |
| improve | partial | 50-200ms | 50-200ms | 121 | 1% | +1.63 |
| improve | sweep | 16-50ms | ? | 96 | 1% | -0.81 |
| improve | partial | 5-16ms | 5-16ms | 42 | 0% | -1.07 |
| join | sweep | 1000-ms | 1000-ms | 41 | 0% | -10.23 |
| improve | sweep | 1000-ms | 1000-ms | 34 | 0% | +1.82 |
| improve | partial | 16-50ms | 16-50ms | 30 | 0% | +2.02 |
| join | partial | 200-1000ms | 200-1000ms | 23 | 0% | +6.84 |
| join | sweep | 5-16ms | ? | 20 | 0% | -1.50 |
| join | sweep | 200-1000ms | ? | 20 | 0% | +1.50 |
| join | sweep | 50-200ms | ? | 17 | 0% | -1.00 |
| improve | sweep | 5-16ms | ? | 10 | 0% | -9.71 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 6,769 | 46% | -0.67 |
| join | partial | — | — | 3,467 | 24% | +0.25 |
| improve | partial | — | — | 3,441 | 24% | -0.11 |
| join | sweep | — | — | 884 | 6% | -0.78 |