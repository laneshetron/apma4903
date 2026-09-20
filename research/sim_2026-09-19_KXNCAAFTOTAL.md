# Quoter simulation, KXNCAAFTOTAL, 2026-09-19

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 714 | -37.35 | 161.85 | -174.31 | -221.71 | 714 | -37.35 | 161.85 | -174.31 | 57.81 | -95.16 | -0.05 | 0.57 | -2.43 | -4.93 | 13,850 | -0.27 | -0.08 | 65.85 | 0.07 | 9,162 | 3.27 | 0.58 | 9.06 |
|  ↳ vetoes: {'priority_fills': 7448, 'capital': 23890130} |
| touch joiner, size 5 | 720 | -102.84 | 222.94 | -305.55 | -327.11 | 720 | -102.84 | 222.94 | -305.55 | -6.03 | -96.81 | -0.14 | 0.51 | -7.48 | -5.66 | 20,177 | -0.51 | -0.20 | 69.85 | 0.10 | 11,382 | 2.71 | 0.60 | 7.40 |
|  ↳ vetoes: {'priority_fills': 9400, 'capital': 18265785} |
| touch joiner, depth >= 50 | 716 | -41.05 | 152.37 | -166.47 | -214.28 | 716 | -41.05 | 152.37 | -166.47 | 76.77 | -117.82 | -0.06 | 0.58 | -2.63 | -3.86 | 11,622 | -0.35 | -0.11 | 81.96 | 0.06 | 7,365 | 2.99 | 0.61 | 9.09 |
|  ↳ vetoes: {'thin': 5246850, 'priority_fills': 7146, 'capital': 21839714} |
| join only, never improve | 689 | -15.96 | 146.03 | -139.63 | -187.44 | 689 | -15.96 | 146.03 | -139.63 | 69.81 | -85.77 | -0.02 | 0.64 | -0.95 | -3.69 | 9,798 | -0.16 | 0.13 | 0.00 | 0.05 | 7,205 | 2.60 | 0.54 | 7.19 |
|  ↳ vetoes: {'priority_fills': 2866, 'capital': 22270812} |
| touch joiner, pessimistic queue | 708 | -60.86 | 154.53 | -192.63 | -218.08 | 708 | -60.86 | 154.53 | -192.63 | 39.99 | -100.85 | -0.09 | 0.58 | -3.92 | -3.96 | 12,664 | -0.48 | -0.13 | 76.29 | 0.06 | 8,173 | 2.99 | 0.62 | 8.07 |
|  ↳ vetoes: {'priority_fills': 8129, 'capital': 24348924} |
| touch joiner, carry (no flatten) | 703 | -24.23 | 134.13 | -158.31 | -199.20 | 703 | -24.23 | 134.13 | -158.31 | 44.32 | -68.54 | -0.03 | 0.51 | -1.79 | -4.87 | 11,814 | -0.21 | -0.16 | 65.18 | 0.06 | 8,344 | 2.53 | 1.08 | 7.21 |
|  ↳ vetoes: {'priority_fills': 6717, 'capital': 27483944} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 4,277 | 25% | -0.23 |
| improve | sweep | 1000-ms | ? | 4,264 | 25% | +0.37 |
| join | partial | 1000-ms | 1000-ms | 1,676 | 10% | +0.25 |
| join | partial | 0-5ms | ? | 1,605 | 9% | -0.81 |
| improve | partial | 1000-ms | 1000-ms | 1,100 | 6% | +0.45 |
| join | sweep | 0-5ms | ? | 1,001 | 6% | -1.31 |
| join | partial | 1000-ms | ? | 780 | 5% | +0.38 |
| improve | partial | 0-5ms | ? | 607 | 4% | -0.86 |
| improve | sweep | 200-1000ms | ? | 521 | 3% | +0.46 |
| improve | sweep | 50-200ms | ? | 301 | 2% | +0.73 |
| join | sweep | 1000-ms | ? | 271 | 2% | -1.74 |
| improve | sweep | 16-50ms | ? | 98 | 1% | +1.84 |
| improve | partial | 200-1000ms | 200-1000ms | 95 | 1% | +0.02 |
| improve | partial | 50-200ms | 50-200ms | 84 | 0% | +0.65 |
| join | sweep | 1000-ms | 1000-ms | 71 | 0% | -1.16 |
| join | sweep | 200-1000ms | ? | 40 | 0% | +0.47 |
| improve | partial | 16-50ms | 16-50ms | 39 | 0% | -0.44 |
| join | partial | 200-1000ms | 200-1000ms | 29 | 0% | -0.22 |
| join | sweep | 16-50ms | ? | 24 | 0% | -0.96 |
| improve | partial | 5-16ms | 5-16ms | 24 | 0% | -0.38 |
| join | sweep | 5-16ms | ? | 18 | 0% | -1.51 |
| join | sweep | 200-1000ms | 1000-ms | 17 | 0% | -6.00 |
| join | sweep | 50-200ms | ? | 13 | 0% | -0.65 |
| join | partial | 50-200ms | 50-200ms | 9 | 0% | +1.94 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 9,473 | 56% | +0.13 |
| join | partial | — | — | 4,104 | 24% | -0.14 |
| improve | partial | — | — | 1,952 | 11% | +0.01 |
| join | sweep | — | — | 1,459 | 9% | -1.38 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 6,499 | 27% | +0.33 |
| improve | sweep | 0-5ms | ? | 6,119 | 25% | -0.55 |
| join | partial | 1000-ms | 1000-ms | 1,972 | 8% | +0.18 |
| join | partial | 0-5ms | ? | 1,777 | 7% | -0.88 |
| improve | partial | 1000-ms | 1000-ms | 1,623 | 7% | +0.17 |
| join | sweep | 0-5ms | ? | 1,366 | 6% | -1.21 |
| improve | sweep | 200-1000ms | ? | 1,038 | 4% | +0.76 |
| improve | partial | 0-5ms | ? | 1,012 | 4% | -0.96 |
| join | partial | 1000-ms | ? | 741 | 3% | +0.41 |
| improve | sweep | 50-200ms | ? | 687 | 3% | -0.74 |
| join | sweep | 1000-ms | ? | 289 | 1% | -0.34 |
| improve | sweep | 16-50ms | ? | 250 | 1% | -0.61 |
| improve | partial | 200-1000ms | 200-1000ms | 191 | 1% | +0.36 |
| improve | partial | 50-200ms | 50-200ms | 162 | 1% | -0.18 |
| improve | partial | 16-50ms | 16-50ms | 99 | 0% | +0.50 |
| join | sweep | 1000-ms | 1000-ms | 72 | 0% | -0.72 |
| join | partial | 200-1000ms | 200-1000ms | 46 | 0% | -0.04 |
| improve | partial | 5-16ms | 5-16ms | 40 | 0% | -1.95 |
| join | sweep | 16-50ms | ? | 29 | 0% | +0.31 |
| join | sweep | 200-1000ms | ? | 26 | 0% | -2.00 |
| join | sweep | 5-16ms | ? | 20 | 0% | -3.13 |
| join | partial | 50-200ms | 50-200ms | 19 | 0% | -1.22 |
| improve | partial | 0-5ms | 0-5ms | 18 | 0% | -5.47 |
| join | sweep | 50-200ms | ? | 16 | 0% | -1.59 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 14,616 | 60% | -0.07 |
| join | partial | — | — | 4,569 | 19% | -0.20 |
| improve | partial | — | — | 3,149 | 13% | -0.25 |
| join | sweep | — | — | 1,839 | 8% | -1.08 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 5,028 | 36% | +0.39 |
| improve | sweep | 0-5ms | ? | 4,279 | 30% | -0.71 |
| join | partial | 1000-ms | 1000-ms | 1,048 | 7% | +0.26 |
| join | partial | 1000-ms | ? | 722 | 5% | +0.48 |
| join | partial | 0-5ms | ? | 699 | 5% | -0.68 |
| improve | sweep | 200-1000ms | ? | 548 | 4% | -0.16 |
| improve | partial | 1000-ms | 1000-ms | 536 | 4% | +0.19 |
| improve | sweep | 50-200ms | ? | 377 | 3% | +0.41 |
| join | sweep | 0-5ms | ? | 324 | 2% | -1.15 |
| improve | sweep | 16-50ms | ? | 159 | 1% | -0.79 |
| join | sweep | 1000-ms | ? | 103 | 1% | -0.22 |
| improve | partial | 0-5ms | ? | 98 | 1% | -0.95 |
| improve | partial | 200-1000ms | 200-1000ms | 55 | 0% | -0.58 |
| improve | partial | 50-200ms | 50-200ms | 54 | 0% | -0.85 |
| join | sweep | 1000-ms | 1000-ms | 27 | 0% | -1.59 |
| improve | partial | 5-16ms | 5-16ms | 20 | 0% | +1.30 |
| improve | partial | 16-50ms | 16-50ms | 17 | 0% | +0.32 |
| join | sweep | 16-50ms | ? | 17 | 0% | +0.50 |
| improve | partial | 0-5ms | 0-5ms | 9 | 0% | +0.89 |
| join | sweep | 200-1000ms | ? | 8 | 0% | -1.69 |
| join | partial | 200-1000ms | 200-1000ms | 7 | 0% | -1.29 |
| improve | sweep | 50-200ms | 1000-ms | 4 | 0% | -2.00 |
| improve | sweep | 5-16ms | ? | 3 | 0% | -1.19 |
| join | sweep | 5-16ms | ? | 3 | 0% | -4.83 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 10,399 | 73% | -0.11 |
| join | partial | — | — | 2,482 | 18% | +0.06 |
| improve | partial | — | — | 789 | 6% | -0.04 |
| join | sweep | — | — | 484 | 3% | -0.95 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 0-5ms | ? | 4,374 | 35% | -0.16 |
| join | partial | 1000-ms | 1000-ms | 3,744 | 30% | +0.39 |
| join | sweep | 0-5ms | ? | 2,826 | 23% | -0.06 |
| join | partial | 1000-ms | ? | 1,120 | 9% | +0.85 |
| join | sweep | 1000-ms | 1000-ms | 130 | 1% | -1.25 |
| join | partial | 200-1000ms | 200-1000ms | 83 | 1% | +1.24 |
| join | partial | 50-200ms | 50-200ms | 74 | 1% | +1.68 |
| join | sweep | 1000-ms | ? | 45 | 0% | -1.60 |
| join | partial | 200-1000ms | 1000-ms | 27 | 0% | +2.61 |
| join | sweep | 5-16ms | ? | 26 | 0% | -0.51 |
| join | partial | 200-1000ms | ? | 13 | 0% | +4.80 |
| join | sweep | 200-1000ms | 200-1000ms | 11 | 0% | +1.18 |
| join | partial | 50-200ms | 1000-ms | 9 | 0% | +0.28 |
| join | sweep | 200-1000ms | 1000-ms | 8 | 0% | -2.75 |
| join | sweep | 50-200ms | 50-200ms | 4 | 0% | +0.50 |
| join | partial | 5-16ms | ? | 3 | 0% | -2.16 |
| join | partial | 16-50ms | 16-50ms | 3 | 0% | +5.33 |
| join | partial | 16-50ms | 1000-ms | 2 | 0% | +0.50 |
| join | sweep | 200-1000ms | ? | 1 | 0% | -14.21 |
| join | partial | 16-50ms | 50-200ms | 1 | 0% | +2.00 |
| join | sweep | 16-50ms | 16-50ms | 1 | 0% | +0.50 |
| join | sweep | 50-200ms | ? | 0 | 0% | +3.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 9,452 | 76% | +0.22 |
| join | sweep | — | — | 3,052 | 24% | -0.14 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 4,552 | 29% | +0.43 |
| improve | sweep | 0-5ms | ? | 4,420 | 29% | -0.59 |
| join | sweep | 0-5ms | ? | 1,452 | 9% | -1.20 |
| improve | partial | 1000-ms | 1000-ms | 1,035 | 7% | +0.42 |
| improve | partial | 0-5ms | ? | 660 | 4% | -0.63 |
| join | partial | 1000-ms | 1000-ms | 656 | 4% | +0.19 |
| join | partial | 0-5ms | ? | 597 | 4% | -0.84 |
| improve | sweep | 200-1000ms | ? | 529 | 3% | +1.14 |
| improve | sweep | 50-200ms | ? | 393 | 3% | +0.99 |
| join | sweep | 1000-ms | ? | 308 | 2% | -0.60 |
| improve | sweep | 16-50ms | ? | 160 | 1% | +0.77 |
| improve | partial | 200-1000ms | 200-1000ms | 151 | 1% | -0.63 |
| join | partial | 1000-ms | ? | 137 | 1% | +0.32 |
| improve | partial | 50-200ms | 50-200ms | 105 | 1% | +0.38 |
| join | sweep | 1000-ms | 1000-ms | 58 | 0% | -0.90 |
| improve | partial | 16-50ms | 16-50ms | 40 | 0% | +0.00 |
| join | sweep | 200-1000ms | ? | 38 | 0% | +0.51 |
| improve | partial | 5-16ms | 5-16ms | 38 | 0% | -0.38 |
| join | sweep | 50-200ms | ? | 27 | 0% | -0.48 |
| join | sweep | 5-16ms | ? | 26 | 0% | -3.40 |
| join | partial | 50-200ms | 50-200ms | 17 | 0% | +0.85 |
| join | partial | 200-1000ms | 200-1000ms | 17 | 0% | -0.97 |
| improve | sweep | 1000-ms | 1000-ms | 14 | 0% | -0.36 |
| join | sweep | 16-50ms | ? | 13 | 0% | -1.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 10,071 | 65% | +0.04 |
| improve | partial | — | — | 2,036 | 13% | -0.02 |
| join | sweep | — | — | 1,934 | 12% | -1.10 |
| join | partial | — | — | 1,431 | 9% | -0.23 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 0-5ms | ? | 3,726 | 26% | -0.42 |
| improve | sweep | 1000-ms | ? | 3,602 | 25% | +0.28 |
| join | partial | 1000-ms | 1000-ms | 1,498 | 10% | +0.23 |
| join | partial | 0-5ms | ? | 1,308 | 9% | -0.84 |
| improve | partial | 1000-ms | 1000-ms | 890 | 6% | +0.46 |
| join | sweep | 0-5ms | ? | 868 | 6% | -1.54 |
| join | partial | 1000-ms | ? | 714 | 5% | +0.42 |
| improve | partial | 0-5ms | ? | 510 | 4% | -0.64 |
| improve | sweep | 200-1000ms | ? | 466 | 3% | +0.08 |
| improve | sweep | 50-200ms | ? | 284 | 2% | +0.74 |
| join | sweep | 1000-ms | ? | 202 | 1% | -0.49 |
| improve | sweep | 16-50ms | ? | 89 | 1% | +0.57 |
| improve | partial | 200-1000ms | 200-1000ms | 76 | 1% | -0.65 |
| improve | partial | 50-200ms | 50-200ms | 75 | 1% | +0.89 |
| improve | partial | 16-50ms | 16-50ms | 53 | 0% | +0.32 |
| join | sweep | 1000-ms | 1000-ms | 35 | 0% | -0.68 |
| join | sweep | 200-1000ms | ? | 24 | 0% | +0.02 |
| join | partial | 200-1000ms | 200-1000ms | 24 | 0% | -0.11 |
| join | sweep | 200-1000ms | 1000-ms | 18 | 0% | -5.64 |
| improve | partial | 5-16ms | 5-16ms | 12 | 0% | +0.29 |
| join | sweep | 16-50ms | ? | 11 | 0% | -1.95 |
| join | sweep | 50-200ms | ? | 10 | 0% | -1.93 |
| join | sweep | 5-16ms | ? | 8 | 0% | -4.14 |
| join | partial | 50-200ms | 50-200ms | 5 | 0% | -2.60 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 8,170 | 56% | -0.04 |
| join | partial | — | — | 3,553 | 24% | -0.13 |
| improve | partial | — | — | 1,619 | 11% | +0.07 |
| join | sweep | — | — | 1,178 | 8% | -1.40 |