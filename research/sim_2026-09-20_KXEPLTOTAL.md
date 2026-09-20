# Quoter simulation, KXEPLTOTAL, 2026-09-20

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 23 | -96.73 | 347.48 | -444.21 | -451.70 | 23 | -96.73 | 347.48 | -444.21 | -46.79 | -49.94 | -4.21 | 5.17 | -3.90 | -16.50 | 31,027 | -0.31 | -0.30 | 75.58 | 1.27 | 3,083 | 19.54 | 9.71 | 0.19 |
|  ↳ vetoes: {'priority_fills': 1895} |
| touch joiner, size 5 | 23 | -22.48 | 102.17 | -124.65 | -115.08 | 23 | -22.48 | 102.17 | -124.65 | -7.23 | -15.25 | -0.98 | 1.35 | -3.48 | -4.12 | 8,857 | -0.25 | -0.14 | 71.15 | 0.36 | 2,170 | 4.96 | 3.24 | 0.08 |
|  ↳ vetoes: {'priority_fills': 1196} |
| touch joiner, depth >= 50 | 23 | -63.64 | 303.94 | -367.58 | -360.59 | 23 | -63.64 | 303.94 | -367.58 | -14.06 | -49.58 | -2.77 | 4.40 | -3.02 | -15.01 | 23,936 | -0.27 | -0.18 | 79.64 | 0.98 | 2,264 | 19.72 | 10.62 | 0.24 |
|  ↳ vetoes: {'thin': 203839, 'priority_fills': 1638} |
| join only, never improve | 23 | -24.26 | 311.74 | -335.99 | -315.80 | 23 | -24.26 | 311.74 | -335.99 | 18.45 | -42.71 | -1.05 | 3.54 | -1.43 | -8.70 | 22,445 | -0.11 | -0.03 | 0.00 | 0.92 | 2,234 | 19.69 | 10.85 | 0.20 |
|  ↳ vetoes: {'priority_fills': 695} |
| touch joiner, pessimistic queue | 23 | -88.20 | 327.71 | -415.91 | -414.13 | 23 | -88.20 | 327.71 | -415.91 | -61.76 | -26.44 | -3.83 | 4.57 | -4.02 | -14.05 | 26,813 | -0.33 | -0.27 | 83.22 | 1.10 | 2,694 | 19.45 | 8.76 | 0.26 |
|  ↳ vetoes: {'priority_fills': 1938} |
| touch joiner, carry (no flatten) | 23 | -96.73 | 347.48 | -444.21 | -451.70 | 23 | -96.73 | 347.48 | -444.21 | -46.79 | -49.94 | -4.21 | 5.17 | -3.90 | -16.50 | 31,027 | -0.31 | -0.30 | 75.58 | 1.27 | 3,083 | 19.54 | 9.71 | 0.19 |
|  ↳ vetoes: {'priority_fills': 1895} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 8,200 | 27% | -0.96 |
| improve | partial | 1000-ms | 1000-ms | 5,080 | 16% | +0.38 |
| improve | sweep | 1000-ms | ? | 4,686 | 15% | +0.31 |
| join | partial | 1000-ms | 1000-ms | 3,065 | 10% | +0.07 |
| join | partial | 0-5ms | ? | 2,752 | 9% | +0.14 |
| improve | partial | 0-5ms | ? | 1,745 | 6% | -0.63 |
| join | sweep | 0-5ms | ? | 1,676 | 5% | -0.04 |
| improve | sweep | 200-1000ms | ? | 1,298 | 4% | -1.81 |
| join | sweep | 1000-ms | ? | 485 | 2% | +1.27 |
| improve | sweep | 50-200ms | ? | 471 | 2% | -2.27 |
| improve | partial | 200-1000ms | 200-1000ms | 409 | 1% | -1.59 |
| join | partial | 1000-ms | ? | 378 | 1% | +0.64 |
| improve | sweep | 16-50ms | ? | 151 | 0% | -1.26 |
| improve | partial | 50-200ms | 50-200ms | 125 | 0% | -1.54 |
| join | sweep | 1000-ms | 1000-ms | 108 | 0% | -0.24 |
| join | partial | 200-1000ms | 200-1000ms | 60 | 0% | -1.17 |
| improve | partial | 16-50ms | 16-50ms | 34 | 0% | +0.02 |
| improve | partial | 0-5ms | 0-5ms | 29 | 0% | -1.91 |
| join | sweep | 200-1000ms | ? | 28 | 0% | -9.83 |
| improve | partial | 5-16ms | 5-16ms | 25 | 0% | +0.28 |
| join | sweep | 5-16ms | ? | 20 | 0% | -0.50 |
| join | sweep | 200-1000ms | 1000-ms | 20 | 0% | +0.00 |
| improve | sweep | 5-16ms | ? | 10 | 0% | -3.50 |
| join | sweep | 50-200ms | ? | 3 | 0% | +3.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 14,818 | 48% | -0.68 |
| improve | partial | — | — | 7,446 | 24% | -0.01 |
| join | partial | — | — | 6,255 | 20% | +0.12 |
| join | sweep | — | — | 2,340 | 8% | +0.11 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 2,080 | 24% | -0.41 |
| improve | sweep | 1000-ms | ? | 1,423 | 16% | +0.21 |
| improve | partial | 1000-ms | 1000-ms | 1,395 | 16% | +0.25 |
| join | partial | 1000-ms | 1000-ms | 906 | 10% | +0.42 |
| join | partial | 0-5ms | ? | 892 | 10% | +0.21 |
| improve | partial | 0-5ms | ? | 505 | 6% | -1.06 |
| join | sweep | 0-5ms | ? | 425 | 5% | -0.52 |
| improve | sweep | 200-1000ms | ? | 401 | 5% | -1.17 |
| improve | sweep | 50-200ms | ? | 188 | 2% | -1.32 |
| join | sweep | 1000-ms | ? | 139 | 2% | +1.40 |
| improve | partial | 200-1000ms | 200-1000ms | 128 | 1% | -0.65 |
| join | partial | 1000-ms | ? | 121 | 1% | +0.56 |
| improve | sweep | 16-50ms | ? | 53 | 1% | -1.76 |
| improve | partial | 50-200ms | 50-200ms | 30 | 0% | -0.83 |
| join | sweep | 1000-ms | 1000-ms | 25 | 0% | -1.20 |
| improve | partial | 16-50ms | 16-50ms | 23 | 0% | -0.15 |
| join | partial | 200-1000ms | 200-1000ms | 15 | 0% | -1.17 |
| improve | partial | 0-5ms | 0-5ms | 11 | 0% | -1.15 |
| join | sweep | 200-1000ms | ? | 10 | 0% | -17.50 |
| improve | partial | 5-16ms | 5-16ms | 10 | 0% | +1.45 |
| improve | sweep | 5-16ms | ? | 5 | 0% | -3.50 |
| join | sweep | 5-16ms | ? | 5 | 0% | -0.50 |
| join | sweep | 200-1000ms | 1000-ms | 5 | 0% | +0.00 |
| join | sweep | 50-200ms | ? | 3 | 0% | +3.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 4,153 | 47% | -0.33 |
| improve | partial | — | — | 2,102 | 24% | -0.14 |
| join | partial | — | — | 1,935 | 22% | +0.32 |
| join | sweep | — | — | 612 | 7% | -0.36 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 7,368 | 31% | -0.74 |
| improve | sweep | 1000-ms | ? | 4,633 | 19% | +0.42 |
| join | partial | 1000-ms | 1000-ms | 3,311 | 14% | +0.13 |
| improve | partial | 1000-ms | 1000-ms | 2,547 | 11% | -0.04 |
| join | partial | 0-5ms | ? | 1,684 | 7% | +0.26 |
| improve | sweep | 200-1000ms | ? | 1,260 | 5% | -1.41 |
| join | sweep | 0-5ms | ? | 600 | 3% | -0.19 |
| improve | sweep | 50-200ms | ? | 544 | 2% | -1.68 |
| improve | partial | 0-5ms | ? | 538 | 2% | +1.00 |
| join | partial | 1000-ms | ? | 335 | 1% | +0.44 |
| improve | partial | 200-1000ms | 200-1000ms | 233 | 1% | -0.16 |
| join | sweep | 1000-ms | ? | 210 | 1% | +1.98 |
| improve | sweep | 16-50ms | ? | 145 | 1% | +0.78 |
| improve | partial | 50-200ms | 50-200ms | 140 | 1% | +0.21 |
| join | partial | 200-1000ms | 200-1000ms | 78 | 0% | -0.04 |
| improve | partial | 5-16ms | 5-16ms | 34 | 0% | +0.60 |
| improve | partial | 0-5ms | 0-5ms | 30 | 0% | -1.82 |
| improve | partial | 16-50ms | 16-50ms | 29 | 0% | +0.97 |
| join | sweep | 200-1000ms | ? | 20 | 0% | -0.50 |
| join | sweep | 5-16ms | ? | 20 | 0% | -0.50 |
| join | sweep | 1000-ms | 1000-ms | 20 | 0% | +6.00 |
| join | sweep | 200-1000ms | 200-1000ms | 18 | 0% | +3.50 |
| improve | sweep | 0-5ms | 0-5ms | 2 | 0% | +2.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 13,952 | 59% | -0.44 |
| join | partial | — | — | 5,408 | 23% | +0.19 |
| improve | partial | — | — | 3,552 | 15% | +0.12 |
| join | sweep | — | — | 888 | 4% | +0.52 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 7,830 | 35% | +0.26 |
| join | partial | 0-5ms | ? | 7,505 | 34% | -0.08 |
| join | sweep | 0-5ms | ? | 5,549 | 25% | -0.19 |
| join | partial | 1000-ms | ? | 540 | 2% | +0.23 |
| join | partial | 200-1000ms | 200-1000ms | 387 | 2% | -3.56 |
| join | sweep | 1000-ms | 1000-ms | 155 | 1% | -0.34 |
| join | sweep | 200-1000ms | 200-1000ms | 155 | 1% | -0.14 |
| join | partial | 50-200ms | 50-200ms | 88 | 0% | -3.35 |
| join | partial | 0-5ms | 1000-ms | 33 | 0% | +13.23 |
| join | partial | 200-1000ms | 1000-ms | 22 | 0% | -1.61 |
| join | sweep | 200-1000ms | 1000-ms | 22 | 0% | -12.41 |
| join | sweep | 1000-ms | ? | 20 | 0% | +17.00 |
| join | sweep | 50-200ms | 50-200ms | 15 | 0% | +4.47 |
| join | sweep | 5-16ms | ? | 7 | 0% | -6.50 |
| join | partial | 200-1000ms | ? | 0 | 0% | +0.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 16,405 | 73% | +0.02 |
| join | sweep | — | — | 5,922 | 27% | -0.18 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 7,988 | 30% | -0.81 |
| improve | sweep | 1000-ms | ? | 4,599 | 17% | +0.39 |
| improve | partial | 1000-ms | 1000-ms | 4,493 | 17% | +0.31 |
| join | sweep | 0-5ms | ? | 2,474 | 9% | +0.15 |
| improve | partial | 0-5ms | ? | 1,622 | 6% | -0.65 |
| improve | sweep | 200-1000ms | ? | 1,365 | 5% | -1.66 |
| join | partial | 1000-ms | 1000-ms | 1,090 | 4% | -0.06 |
| join | partial | 0-5ms | ? | 1,013 | 4% | +0.97 |
| improve | sweep | 50-200ms | ? | 498 | 2% | -2.29 |
| join | sweep | 1000-ms | ? | 471 | 2% | +1.16 |
| improve | partial | 200-1000ms | 200-1000ms | 368 | 1% | -1.73 |
| improve | sweep | 16-50ms | ? | 166 | 1% | +0.52 |
| join | sweep | 1000-ms | 1000-ms | 124 | 0% | -0.98 |
| improve | partial | 50-200ms | 50-200ms | 123 | 0% | -1.26 |
| join | sweep | 200-1000ms | ? | 48 | 0% | -6.33 |
| join | partial | 1000-ms | ? | 40 | 0% | +0.00 |
| join | partial | 200-1000ms | 200-1000ms | 40 | 0% | -1.50 |
| improve | partial | 16-50ms | 16-50ms | 38 | 0% | +0.14 |
| improve | partial | 0-5ms | 0-5ms | 29 | 0% | -1.91 |
| improve | partial | 5-16ms | 5-16ms | 25 | 0% | +0.28 |
| join | sweep | 5-16ms | ? | 20 | 0% | -0.50 |
| join | sweep | 200-1000ms | 1000-ms | 20 | 0% | +0.00 |
| improve | sweep | 5-16ms | ? | 10 | 0% | -3.50 |
| improve | sweep | 0-5ms | 0-5ms | 2 | 0% | +2.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 14,627 | 55% | -0.55 |
| improve | partial | — | — | 6,698 | 25% | -0.08 |
| join | sweep | — | — | 3,157 | 12% | +0.15 |
| join | partial | — | — | 2,183 | 8% | +0.39 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 8,200 | 27% | -0.96 |
| improve | partial | 1000-ms | 1000-ms | 5,080 | 16% | +0.38 |
| improve | sweep | 1000-ms | ? | 4,686 | 15% | +0.31 |
| join | partial | 1000-ms | 1000-ms | 3,065 | 10% | +0.07 |
| join | partial | 0-5ms | ? | 2,752 | 9% | +0.14 |
| improve | partial | 0-5ms | ? | 1,745 | 6% | -0.63 |
| join | sweep | 0-5ms | ? | 1,676 | 5% | -0.04 |
| improve | sweep | 200-1000ms | ? | 1,298 | 4% | -1.81 |
| join | sweep | 1000-ms | ? | 485 | 2% | +1.27 |
| improve | sweep | 50-200ms | ? | 471 | 2% | -2.27 |
| improve | partial | 200-1000ms | 200-1000ms | 409 | 1% | -1.59 |
| join | partial | 1000-ms | ? | 378 | 1% | +0.64 |
| improve | sweep | 16-50ms | ? | 151 | 0% | -1.26 |
| improve | partial | 50-200ms | 50-200ms | 125 | 0% | -1.54 |
| join | sweep | 1000-ms | 1000-ms | 108 | 0% | -0.24 |
| join | partial | 200-1000ms | 200-1000ms | 60 | 0% | -1.17 |
| improve | partial | 16-50ms | 16-50ms | 34 | 0% | +0.02 |
| improve | partial | 0-5ms | 0-5ms | 29 | 0% | -1.91 |
| join | sweep | 200-1000ms | ? | 28 | 0% | -9.83 |
| improve | partial | 5-16ms | 5-16ms | 25 | 0% | +0.28 |
| join | sweep | 5-16ms | ? | 20 | 0% | -0.50 |
| join | sweep | 200-1000ms | 1000-ms | 20 | 0% | +0.00 |
| improve | sweep | 5-16ms | ? | 10 | 0% | -3.50 |
| join | sweep | 50-200ms | ? | 3 | 0% | +3.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 14,818 | 48% | -0.68 |
| improve | partial | — | — | 7,446 | 24% | -0.01 |
| join | partial | — | — | 6,255 | 20% | +0.12 |
| join | sweep | — | — | 2,340 | 8% | +0.11 |