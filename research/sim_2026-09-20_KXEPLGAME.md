# Quoter simulation, KXEPLGAME, 2026-09-20

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 12 | -96.96 | 222.28 | -319.24 | -308.07 | 12 | -96.96 | 222.28 | -319.24 | -66.22 | -30.74 | -8.08 | 6.33 | -4.42 | -18.75 | 51,214 | -0.19 | -0.17 | 46.45 | 0.37 | 4,993 | 19.85 | 10.22 | 0.00 |
|  ↳ vetoes: {'priority_fills': 2323} |
| touch joiner, size 5 | 12 | -22.26 | 64.49 | -86.74 | -86.91 | 12 | -22.26 | 64.49 | -86.74 | -15.01 | -7.25 | -1.85 | 1.89 | -3.41 | -4.94 | 14,738 | -0.15 | -0.14 | 46.83 | 0.11 | 3,989 | 5.00 | 2.30 | 0.00 |
|  ↳ vetoes: {'priority_fills': 1740} |
| touch joiner, depth >= 50 | 12 | -65.96 | 171.76 | -237.71 | -243.11 | 12 | -65.96 | 171.76 | -237.71 | -32.75 | -33.21 | -5.50 | 5.72 | -3.33 | -13.49 | 39,358 | -0.17 | -0.18 | 53.45 | 0.28 | 3,418 | 19.97 | 11.37 | 0.00 |
|  ↳ vetoes: {'thin': 204892, 'priority_fills': 1789} |
| join only, never improve | 12 | -43.74 | 261.74 | -305.49 | -319.30 | 12 | -43.74 | 261.74 | -305.49 | -17.84 | -25.90 | -3.65 | 7.08 | -1.78 | -13.80 | 41,824 | -0.10 | -0.13 | 0.00 | 0.30 | 3,963 | 19.97 | 10.49 | 0.00 |
|  ↳ vetoes: {'priority_fills': 1015} |
| touch joiner, pessimistic queue | 12 | -94.33 | 160.00 | -254.33 | -244.37 | 12 | -94.33 | 160.00 | -254.33 | -85.09 | -9.24 | -7.86 | 5.77 | -4.72 | -21.39 | 38,275 | -0.25 | -0.24 | 58.08 | 0.28 | 3,822 | 19.98 | 6.30 | 0.00 |
|  ↳ vetoes: {'priority_fills': 2479} |
| touch joiner, carry (no flatten) | 12 | -96.96 | 222.28 | -319.24 | -308.07 | 12 | -96.96 | 222.28 | -319.24 | -66.22 | -30.74 | -8.08 | 6.33 | -4.42 | -18.75 | 51,214 | -0.19 | -0.17 | 46.45 | 0.37 | 4,993 | 19.85 | 10.22 | 0.00 |
|  ↳ vetoes: {'priority_fills': 2323} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 12,858 | 25% | +0.36 |
| join | partial | 0-5ms | ? | 8,096 | 16% | -0.56 |
| improve | sweep | 0-5ms | ? | 5,245 | 10% | -1.12 |
| improve | sweep | 1000-ms | ? | 4,739 | 9% | -0.18 |
| join | sweep | 0-5ms | ? | 4,510 | 9% | -0.40 |
| improve | partial | 0-5ms | ? | 2,842 | 6% | -0.86 |
| improve | sweep | 200-1000ms | ? | 2,826 | 6% | -0.42 |
| improve | partial | 1000-ms | 1000-ms | 2,478 | 5% | +0.17 |
| improve | partial | 200-1000ms | 200-1000ms | 1,360 | 3% | +0.60 |
| improve | sweep | 50-200ms | ? | 1,333 | 3% | +0.53 |
| join | partial | 1000-ms | ? | 1,283 | 3% | +0.33 |
| join | partial | 200-1000ms | 200-1000ms | 581 | 1% | -0.04 |
| improve | sweep | 16-50ms | ? | 479 | 1% | +2.32 |
| improve | partial | 50-200ms | 50-200ms | 460 | 1% | -0.21 |
| improve | partial | 16-50ms | 16-50ms | 275 | 1% | -2.02 |
| join | partial | 50-200ms | 50-200ms | 233 | 0% | -0.10 |
| join | sweep | 5-16ms | ? | 184 | 0% | +1.02 |
| join | sweep | 1000-ms | 1000-ms | 179 | 0% | -0.44 |
| join | sweep | 1000-ms | ? | 176 | 0% | -1.15 |
| join | sweep | 200-1000ms | ? | 124 | 0% | +6.84 |
| improve | partial | 5-16ms | 5-16ms | 97 | 0% | +0.65 |
| join | sweep | 16-50ms | ? | 83 | 0% | -0.31 |
| join | sweep | 50-200ms | ? | 83 | 0% | -1.80 |
| join | partial | 200-1000ms | 1000-ms | 50 | 0% | -0.89 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 23,169 | 46% | +0.02 |
| improve | sweep | — | — | 14,714 | 29% | -0.41 |
| improve | partial | — | — | 7,538 | 15% | -0.23 |
| join | sweep | — | — | 5,400 | 11% | -0.21 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 3,616 | 25% | +0.41 |
| join | partial | 0-5ms | ? | 2,287 | 16% | -0.56 |
| improve | sweep | 1000-ms | ? | 1,600 | 11% | -0.15 |
| improve | sweep | 0-5ms | ? | 1,344 | 9% | -1.12 |
| join | sweep | 0-5ms | ? | 1,183 | 8% | -0.31 |
| improve | sweep | 200-1000ms | ? | 951 | 7% | -0.21 |
| improve | partial | 0-5ms | ? | 803 | 5% | -0.82 |
| improve | partial | 1000-ms | 1000-ms | 715 | 5% | +0.12 |
| improve | sweep | 50-200ms | ? | 412 | 3% | +0.59 |
| improve | partial | 200-1000ms | 200-1000ms | 392 | 3% | +0.47 |
| join | partial | 1000-ms | ? | 355 | 2% | +0.41 |
| join | partial | 200-1000ms | 200-1000ms | 164 | 1% | +0.22 |
| improve | partial | 50-200ms | 50-200ms | 152 | 1% | -0.22 |
| improve | sweep | 16-50ms | ? | 150 | 1% | +0.92 |
| improve | partial | 16-50ms | 16-50ms | 107 | 1% | -1.48 |
| join | partial | 50-200ms | 50-200ms | 72 | 0% | -0.33 |
| join | sweep | 1000-ms | 1000-ms | 50 | 0% | -0.21 |
| join | sweep | 1000-ms | ? | 47 | 0% | -1.16 |
| join | sweep | 5-16ms | ? | 43 | 0% | +0.19 |
| join | sweep | 200-1000ms | ? | 39 | 0% | +1.29 |
| improve | partial | 5-16ms | 5-16ms | 37 | 0% | +0.41 |
| join | sweep | 16-50ms | ? | 22 | 0% | -2.98 |
| join | sweep | 50-200ms | ? | 20 | 0% | +3.56 |
| improve | partial | 0-5ms | 0-5ms | 15 | 0% | +1.86 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 6,511 | 45% | +0.05 |
| improve | sweep | — | — | 4,467 | 31% | -0.35 |
| improve | partial | — | — | 2,226 | 15% | -0.24 |
| join | sweep | — | — | 1,424 | 10% | -0.24 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 11,123 | 29% | +0.35 |
| join | partial | 0-5ms | ? | 6,104 | 16% | -0.40 |
| improve | sweep | 0-5ms | ? | 4,775 | 12% | -0.95 |
| improve | sweep | 1000-ms | ? | 4,512 | 12% | -0.59 |
| improve | sweep | 200-1000ms | ? | 2,889 | 7% | -0.91 |
| join | sweep | 0-5ms | ? | 1,961 | 5% | -0.89 |
| improve | sweep | 50-200ms | ? | 1,586 | 4% | +0.57 |
| join | partial | 1000-ms | ? | 1,107 | 3% | +0.45 |
| improve | partial | 0-5ms | ? | 1,050 | 3% | -1.63 |
| improve | partial | 1000-ms | 1000-ms | 1,030 | 3% | -0.01 |
| improve | partial | 200-1000ms | 200-1000ms | 757 | 2% | +0.54 |
| improve | sweep | 16-50ms | ? | 536 | 1% | +1.25 |
| join | partial | 200-1000ms | 200-1000ms | 425 | 1% | +1.31 |
| improve | partial | 50-200ms | 50-200ms | 256 | 1% | +0.31 |
| improve | partial | 16-50ms | 16-50ms | 137 | 0% | +0.38 |
| join | sweep | 1000-ms | 1000-ms | 115 | 0% | +0.39 |
| join | sweep | 5-16ms | ? | 106 | 0% | -0.18 |
| join | partial | 50-200ms | 50-200ms | 91 | 0% | +0.92 |
| improve | partial | 5-16ms | 5-16ms | 88 | 0% | +1.22 |
| join | partial | 200-1000ms | 1000-ms | 60 | 0% | +1.82 |
| join | sweep | 1000-ms | ? | 48 | 0% | -0.69 |
| join | sweep | 16-50ms | ? | 48 | 0% | +1.23 |
| join | sweep | 200-1000ms | ? | 46 | 0% | +23.50 |
| improve | partial | 0-5ms | 0-5ms | 38 | 0% | +2.51 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 18,946 | 49% | +0.14 |
| improve | sweep | — | — | 14,331 | 37% | -0.58 |
| improve | partial | — | — | 3,376 | 9% | -0.27 |
| join | sweep | — | — | 2,352 | 6% | -0.26 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 16,972 | 41% | +0.25 |
| join | partial | 0-5ms | ? | 12,816 | 31% | -0.60 |
| join | sweep | 0-5ms | ? | 7,711 | 19% | -0.29 |
| join | partial | 200-1000ms | 200-1000ms | 1,471 | 4% | -0.42 |
| join | partial | 1000-ms | ? | 1,269 | 3% | +0.29 |
| join | partial | 50-200ms | 50-200ms | 290 | 1% | +0.61 |
| join | sweep | 1000-ms | 1000-ms | 271 | 1% | -0.57 |
| join | partial | 200-1000ms | 1000-ms | 262 | 1% | +0.35 |
| join | sweep | 5-16ms | ? | 152 | 0% | -0.32 |
| join | sweep | 200-1000ms | 200-1000ms | 124 | 0% | -3.81 |
| join | sweep | 50-200ms | 50-200ms | 106 | 0% | +0.61 |
| join | partial | 50-200ms | 1000-ms | 54 | 0% | +6.77 |
| join | sweep | 200-1000ms | 1000-ms | 23 | 0% | +12.64 |
| join | partial | 50-200ms | 200-1000ms | 20 | 0% | +7.50 |
| join | sweep | 16-50ms | 16-50ms | 20 | 0% | +4.50 |
| join | partial | 200-1000ms | ? | 20 | 0% | -1.50 |
| join | partial | 0-5ms | 200-1000ms | 13 | 0% | +1.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 33,188 | 80% | -0.09 |
| join | sweep | — | — | 8,407 | 20% | -0.30 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 6,200 | 16% | -0.32 |
| improve | sweep | 0-5ms | ? | 5,220 | 14% | -1.21 |
| improve | sweep | 1000-ms | ? | 4,690 | 12% | -0.31 |
| join | partial | 1000-ms | 1000-ms | 4,536 | 12% | +0.41 |
| join | partial | 0-5ms | ? | 3,546 | 9% | -0.39 |
| improve | sweep | 200-1000ms | ? | 2,741 | 7% | -0.86 |
| improve | partial | 0-5ms | ? | 2,736 | 7% | -0.70 |
| improve | partial | 1000-ms | 1000-ms | 2,026 | 5% | +0.45 |
| improve | partial | 200-1000ms | 200-1000ms | 1,353 | 4% | +0.52 |
| improve | sweep | 50-200ms | ? | 1,225 | 3% | +0.84 |
| improve | partial | 50-200ms | 50-200ms | 517 | 1% | -0.10 |
| improve | sweep | 16-50ms | ? | 476 | 1% | +1.95 |
| join | partial | 200-1000ms | 200-1000ms | 401 | 1% | +0.78 |
| improve | partial | 16-50ms | 16-50ms | 316 | 1% | -1.73 |
| join | sweep | 1000-ms | 1000-ms | 277 | 1% | -0.93 |
| join | partial | 1000-ms | ? | 240 | 1% | +0.37 |
| join | partial | 50-200ms | 50-200ms | 239 | 1% | +0.27 |
| join | sweep | 200-1000ms | ? | 194 | 1% | +3.96 |
| join | sweep | 5-16ms | ? | 185 | 0% | +1.04 |
| join | sweep | 1000-ms | ? | 171 | 0% | -0.91 |
| improve | partial | 5-16ms | 5-16ms | 117 | 0% | +0.79 |
| join | sweep | 16-50ms | ? | 98 | 0% | +0.37 |
| join | sweep | 50-200ms | ? | 72 | 0% | +1.29 |
| join | sweep | 200-1000ms | 200-1000ms | 52 | 0% | +1.33 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 14,459 | 38% | -0.56 |
| join | partial | — | — | 9,053 | 24% | +0.10 |
| join | sweep | — | — | 7,298 | 19% | -0.17 |
| improve | partial | — | — | 7,084 | 19% | -0.11 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 12,858 | 25% | +0.36 |
| join | partial | 0-5ms | ? | 8,096 | 16% | -0.56 |
| improve | sweep | 0-5ms | ? | 5,245 | 10% | -1.12 |
| improve | sweep | 1000-ms | ? | 4,739 | 9% | -0.18 |
| join | sweep | 0-5ms | ? | 4,510 | 9% | -0.40 |
| improve | partial | 0-5ms | ? | 2,842 | 6% | -0.86 |
| improve | sweep | 200-1000ms | ? | 2,826 | 6% | -0.42 |
| improve | partial | 1000-ms | 1000-ms | 2,478 | 5% | +0.17 |
| improve | partial | 200-1000ms | 200-1000ms | 1,360 | 3% | +0.60 |
| improve | sweep | 50-200ms | ? | 1,333 | 3% | +0.53 |
| join | partial | 1000-ms | ? | 1,283 | 3% | +0.33 |
| join | partial | 200-1000ms | 200-1000ms | 581 | 1% | -0.04 |
| improve | sweep | 16-50ms | ? | 479 | 1% | +2.32 |
| improve | partial | 50-200ms | 50-200ms | 460 | 1% | -0.21 |
| improve | partial | 16-50ms | 16-50ms | 275 | 1% | -2.02 |
| join | partial | 50-200ms | 50-200ms | 233 | 0% | -0.10 |
| join | sweep | 5-16ms | ? | 184 | 0% | +1.02 |
| join | sweep | 1000-ms | 1000-ms | 179 | 0% | -0.44 |
| join | sweep | 1000-ms | ? | 176 | 0% | -1.15 |
| join | sweep | 200-1000ms | ? | 124 | 0% | +6.84 |
| improve | partial | 5-16ms | 5-16ms | 97 | 0% | +0.65 |
| join | sweep | 16-50ms | ? | 83 | 0% | -0.31 |
| join | sweep | 50-200ms | ? | 83 | 0% | -1.80 |
| join | partial | 200-1000ms | 1000-ms | 50 | 0% | -0.89 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 23,169 | 46% | +0.02 |
| improve | sweep | — | — | 14,714 | 29% | -0.41 |
| improve | partial | — | — | 7,538 | 15% | -0.23 |
| join | sweep | — | — | 5,400 | 11% | -0.21 |