# Quoter simulation, KXETH15M, 2026-09-17

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline touch joiner | 88 | -471.10 | 460.01 | -921.53 | -905.52 | 88 | -471.10 | 460.01 | -921.53 | -469.53 | -1.57 | -5.35 | 3.40 | -14.79 | -14.09 | 169,128 | -0.28 | -0.27 | 47.17 | 2.04 | 23,991 | 19.79 | 0.00 | 10.43 |
|  ↳ vetoes: {'priority_fills': 12932, 'greeks': 3405626} |
| touch age >= 50 ms | 88 | -273.16 | 501.49 | -765.16 | -748.80 | 88 | -273.16 | 501.49 | -765.16 | -250.53 | -22.63 | -3.10 | 4.05 | -7.18 | -15.02 | 120,695 | -0.23 | -0.22 | 0.00 | 1.45 | 17,148 | 19.79 | 0.00 | 10.39 |
|  ↳ vetoes: {'young_touch': 1466503, 'priority_fills': 6811, 'greeks': 3405626} |
| touch age >= 200 ms | 88 | -287.36 | 424.46 | -702.84 | -673.81 | 88 | -287.36 | 424.46 | -702.84 | -248.63 | -38.73 | -3.27 | 3.74 | -8.19 | -13.16 | 99,707 | -0.29 | -0.25 | 0.00 | 1.20 | 14,127 | 19.77 | 0.00 | 9.51 |
|  ↳ vetoes: {'young_touch': 2433790, 'priority_fills': 5435, 'greeks': 3405626} |
| touch age >= 500 ms | 88 | -222.39 | 337.27 | -551.64 | -546.59 | 88 | -222.39 | 337.27 | -551.64 | -163.70 | -58.69 | -2.53 | 4.13 | -5.74 | -12.85 | 77,400 | -0.29 | -0.30 | 0.00 | 0.93 | 11,033 | 19.69 | 0.00 | 9.04 |
|  ↳ vetoes: {'young_touch': 3327377, 'priority_fills': 4058, 'greeks': 3405626} |
| touch age >= 1000 ms | 88 | -165.58 | 247.36 | -402.82 | -373.26 | 88 | -165.58 | 247.36 | -402.82 | -115.50 | -50.08 | -1.88 | 3.69 | -4.78 | -11.98 | 55,377 | -0.30 | -0.30 | 0.00 | 0.67 | 7,661 | 19.50 | 0.00 | 11.30 |
|  ↳ vetoes: {'young_touch': 4138116, 'priority_fills': 2700, 'greeks': 3405626} |
| touch age >= 200 ms, improves allowed | 88 | -435.80 | 331.62 | -757.87 | -713.88 | 88 | -435.80 | 331.62 | -757.87 | -415.71 | -20.09 | -4.95 | 3.79 | -12.25 | -15.78 | 135,546 | -0.32 | -0.28 | 35.97 | 1.63 | 19,426 | 19.81 | 0.00 | 10.45 |
|  ↳ vetoes: {'young_touch': 1425579, 'priority_fills': 12450, 'greeks': 3405626} |
| touch age >= 200 ms + depth gate | 88 | 9.95 | 100.28 | -80.16 | -72.61 | 88 | 9.95 | 100.28 | -80.16 | 17.72 | -7.77 | 0.11 | 4.52 | 0.23 | -12.50 | 19,460 | 0.05 | 0.02 | 0.00 | 0.23 | 2,437 | 19.41 | 0.00 | 11.37 |
|  ↳ vetoes: {'young_touch': 2677851, 'thin': 1918559, 'priority_fills': 1261, 'greeks': 3405626} |
| touch age >= 200 ms, size 5 | 88 | -58.56 | 133.79 | -190.29 | -196.81 | 88 | -58.56 | 133.79 | -190.29 | -55.93 | -2.63 | -0.67 | 0.93 | -6.73 | -2.73 | 31,130 | -0.19 | -0.21 | 0.00 | 0.38 | 9,617 | 4.93 | 0.00 | 2.47 |
|  ↳ vetoes: {'young_touch': 2466170, 'priority_fills': 3101, 'greeks': 3405626} |
| touch age >= 200 ms, pessimistic queue | 88 | -298.71 | 295.50 | -585.06 | -582.99 | 88 | -298.71 | 295.50 | -585.06 | -256.51 | -42.20 | -3.39 | 3.92 | -8.12 | -13.82 | 76,292 | -0.39 | -0.38 | 0.00 | 0.92 | 9,705 | 19.60 | 0.00 | 9.97 |
|  ↳ vetoes: {'young_touch': 2446580, 'priority_fills': 6354, 'greeks': 3405626} |

baseline touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 28,487 | 17% | -0.98 |
| join | partial | 0-5ms | ? | 22,883 | 14% | -0.16 |
| improve | sweep | 0-5ms | ? | 20,678 | 12% | -0.19 |
| join | partial | 1000-ms | 1000-ms | 19,244 | 11% | +0.09 |
| improve | sweep | 1000-ms | ? | 12,754 | 8% | -0.26 |
| improve | partial | 0-5ms | ? | 10,902 | 6% | -0.21 |
| improve | sweep | 200-1000ms | ? | 9,778 | 6% | -0.10 |
| improve | partial | 200-1000ms | 200-1000ms | 7,497 | 4% | +0.10 |
| improve | partial | 1000-ms | 1000-ms | 6,431 | 4% | +0.05 |
| join | partial | 200-1000ms | 200-1000ms | 5,079 | 3% | +0.77 |
| improve | sweep | 50-200ms | ? | 4,959 | 3% | -0.24 |
| improve | partial | 50-200ms | 50-200ms | 2,363 | 1% | -0.41 |
| join | sweep | 200-1000ms | ? | 2,118 | 1% | +0.97 |
| join | partial | 1000-ms | ? | 1,939 | 1% | -0.78 |
| join | sweep | 50-200ms | ? | 1,612 | 1% | -0.24 |
| join | sweep | 5-16ms | ? | 1,541 | 1% | -1.31 |
| improve | sweep | 16-50ms | ? | 1,511 | 1% | -0.07 |
| join | partial | 200-1000ms | 1000-ms | 1,349 | 1% | -0.56 |
| join | sweep | 1000-ms | 1000-ms | 1,008 | 1% | -2.26 |
| join | partial | 50-200ms | 50-200ms | 850 | 1% | +1.02 |
| join | sweep | 1000-ms | ? | 704 | 0% | -1.86 |
| improve | partial | 16-50ms | 16-50ms | 649 | 0% | -0.93 |
| improve | partial | 5-16ms | 5-16ms | 648 | 0% | +1.49 |
| join | sweep | 16-50ms | ? | 645 | 0% | +0.58 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 52,164 | 31% | -0.01 |
| improve | sweep | — | — | 50,834 | 30% | -0.22 |
| join | sweep | — | — | 37,335 | 22% | -0.87 |
| improve | partial | — | — | 28,795 | 17% | -0.04 |

touch age >= 50 ms: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 41,373 | 34% | -0.46 |
| join | partial | 0-5ms | ? | 33,415 | 28% | -0.11 |
| join | partial | 1000-ms | 1000-ms | 29,483 | 24% | +0.22 |
| join | partial | 200-1000ms | 200-1000ms | 5,844 | 5% | +0.04 |
| join | partial | 1000-ms | ? | 2,421 | 2% | -0.54 |
| join | partial | 200-1000ms | 1000-ms | 1,694 | 1% | -0.46 |
| join | sweep | 200-1000ms | 200-1000ms | 1,541 | 1% | -0.09 |
| join | sweep | 1000-ms | 1000-ms | 1,299 | 1% | -2.71 |
| join | sweep | 5-16ms | ? | 1,021 | 1% | -2.34 |
| join | sweep | 50-200ms | 50-200ms | 569 | 0% | +0.27 |
| join | partial | 50-200ms | 50-200ms | 495 | 0% | -1.91 |
| join | partial | 200-1000ms | ? | 390 | 0% | -0.42 |
| join | sweep | 200-1000ms | 1000-ms | 305 | 0% | -4.52 |
| join | sweep | 50-200ms | 1000-ms | 186 | 0% | +1.85 |
| join | sweep | 1000-ms | ? | 179 | 0% | -4.11 |
| join | sweep | 200-1000ms | ? | 135 | 0% | +0.76 |
| join | sweep | 50-200ms | 200-1000ms | 91 | 0% | -0.73 |
| join | partial | 50-200ms | 1000-ms | 73 | 0% | +4.32 |
| join | partial | 50-200ms | 200-1000ms | 52 | 0% | -0.05 |
| join | sweep | 0-5ms | 0-5ms | 24 | 0% | +2.58 |
| join | partial | 0-5ms | 1000-ms | 22 | 0% | +6.40 |
| join | sweep | 0-5ms | 200-1000ms | 20 | 0% | +1.55 |
| join | sweep | 5-16ms | 1000-ms | 20 | 0% | +1.50 |
| join | partial | 5-16ms | ? | 14 | 0% | +4.33 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 73,930 | 61% | +0.00 |
| join | sweep | — | — | 46,765 | 39% | -0.56 |

touch age >= 200 ms: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 34,777 | 35% | -0.48 |
| join | partial | 0-5ms | ? | 27,689 | 28% | -0.18 |
| join | partial | 1000-ms | 1000-ms | 26,800 | 27% | +0.11 |
| join | partial | 200-1000ms | 200-1000ms | 2,745 | 3% | +0.15 |
| join | partial | 1000-ms | ? | 2,290 | 2% | -0.62 |
| join | sweep | 1000-ms | 1000-ms | 1,414 | 1% | -2.38 |
| join | sweep | 200-1000ms | 200-1000ms | 1,223 | 1% | +0.03 |
| join | partial | 200-1000ms | 1000-ms | 984 | 1% | +0.45 |
| join | sweep | 5-16ms | ? | 819 | 1% | -0.16 |
| join | sweep | 200-1000ms | 1000-ms | 299 | 0% | -5.26 |
| join | sweep | 1000-ms | ? | 222 | 0% | -5.25 |
| join | sweep | 200-1000ms | ? | 176 | 0% | -1.03 |
| join | partial | 200-1000ms | ? | 156 | 0% | +1.74 |
| join | partial | 0-5ms | 1000-ms | 61 | 0% | +9.25 |
| join | sweep | 0-5ms | 200-1000ms | 20 | 0% | +1.55 |
| join | sweep | 0-5ms | 0-5ms | 20 | 0% | +3.60 |
| join | partial | 5-16ms | 200-1000ms | 8 | 0% | -8.50 |
| join | partial | 0-5ms | 0-5ms | 2 | 0% | +4.60 |
| join | partial | 5-16ms | 5-16ms | 1 | 0% | +4.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 60,737 | 61% | -0.03 |
| join | sweep | — | — | 38,970 | 39% | -0.59 |

touch age >= 500 ms: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 26,478 | 34% | -0.55 |
| join | partial | 1000-ms | 1000-ms | 23,233 | 30% | -0.03 |
| join | partial | 0-5ms | ? | 21,226 | 27% | +0.07 |
| join | partial | 1000-ms | ? | 1,993 | 3% | -0.62 |
| join | sweep | 1000-ms | 1000-ms | 1,557 | 2% | -2.71 |
| join | partial | 200-1000ms | 200-1000ms | 753 | 1% | -2.51 |
| join | sweep | 5-16ms | ? | 642 | 1% | -0.16 |
| join | sweep | 200-1000ms | 200-1000ms | 558 | 1% | +0.45 |
| join | partial | 200-1000ms | 1000-ms | 349 | 0% | -0.24 |
| join | sweep | 1000-ms | ? | 216 | 0% | -4.57 |
| join | sweep | 200-1000ms | 1000-ms | 135 | 0% | -6.20 |
| join | partial | 0-5ms | 1000-ms | 84 | 0% | +5.99 |
| join | sweep | 200-1000ms | ? | 72 | 0% | -7.08 |
| join | partial | 200-1000ms | ? | 57 | 0% | -0.47 |
| join | partial | 5-16ms | ? | 20 | 0% | -24.50 |
| join | partial | 0-5ms | 0-5ms | 12 | 0% | -8.99 |
| join | partial | 5-16ms | 1000-ms | 8 | 0% | +16.50 |
| join | sweep | 0-5ms | 0-5ms | 4 | 0% | -2.50 |
| join | partial | 5-16ms | 5-16ms | 3 | 0% | -0.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 47,739 | 62% | -0.05 |
| join | sweep | — | — | 29,661 | 38% | -0.71 |

touch age >= 1000 ms: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 18,241 | 33% | -0.89 |
| join | partial | 1000-ms | 1000-ms | 17,468 | 32% | +0.15 |
| join | partial | 0-5ms | ? | 15,543 | 28% | +0.19 |
| join | sweep | 1000-ms | 1000-ms | 1,656 | 3% | -2.99 |
| join | partial | 1000-ms | ? | 1,570 | 3% | -0.65 |
| join | sweep | 5-16ms | ? | 529 | 1% | +0.78 |
| join | sweep | 1000-ms | ? | 256 | 0% | -4.19 |
| join | partial | 0-5ms | 1000-ms | 61 | 0% | +9.26 |
| join | partial | 0-5ms | 0-5ms | 46 | 0% | -0.76 |
| join | sweep | 0-5ms | 0-5ms | 6 | 0% | -0.50 |
| join | partial | 5-16ms | 5-16ms | 1 | 0% | +3.05 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 34,689 | 63% | +0.14 |
| join | sweep | — | — | 20,688 | 37% | -1.06 |

touch age >= 200 ms, improves allowed: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 32,460 | 24% | -0.73 |
| join | partial | 0-5ms | ? | 22,085 | 16% | -0.44 |
| join | partial | 1000-ms | 1000-ms | 19,851 | 15% | +0.21 |
| improve | sweep | 0-5ms | ? | 16,313 | 12% | -0.17 |
| improve | sweep | 1000-ms | ? | 12,112 | 9% | -0.00 |
| improve | sweep | 200-1000ms | ? | 9,754 | 7% | +0.27 |
| improve | sweep | 50-200ms | ? | 5,804 | 4% | -0.14 |
| join | partial | 200-1000ms | 200-1000ms | 2,378 | 2% | +0.54 |
| join | sweep | 200-1000ms | ? | 2,153 | 2% | -0.17 |
| improve | sweep | 16-50ms | ? | 1,731 | 1% | -0.19 |
| join | partial | 1000-ms | ? | 1,713 | 1% | -0.44 |
| join | sweep | 1000-ms | 1000-ms | 1,409 | 1% | -2.35 |
| join | sweep | 5-16ms | ? | 1,326 | 1% | -0.38 |
| join | sweep | 50-200ms | ? | 1,223 | 1% | -0.59 |
| join | sweep | 200-1000ms | 200-1000ms | 1,029 | 1% | -0.77 |
| join | sweep | 1000-ms | ? | 819 | 1% | -3.02 |
| improve | partial | 5-16ms | 5-16ms | 612 | 0% | +1.76 |
| join | partial | 200-1000ms | 1000-ms | 593 | 0% | +1.58 |
| improve | partial | 0-5ms | ? | 543 | 0% | -0.14 |
| join | sweep | 16-50ms | ? | 518 | 0% | +0.13 |
| join | sweep | 200-1000ms | 1000-ms | 325 | 0% | -5.96 |
| improve | partial | 0-5ms | 0-5ms | 315 | 0% | +0.73 |
| join | partial | 200-1000ms | ? | 224 | 0% | +1.70 |
| improve | sweep | 5-16ms | ? | 124 | 0% | -5.77 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 46,903 | 35% | -0.08 |
| improve | sweep | — | — | 45,881 | 34% | -0.05 |
| join | sweep | — | — | 41,284 | 30% | -0.82 |
| improve | partial | — | — | 1,478 | 1% | +0.84 |

touch age >= 200 ms + depth gate: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 7,872 | 40% | +0.05 |
| join | partial | 0-5ms | ? | 4,672 | 24% | +0.47 |
| join | partial | 1000-ms | 1000-ms | 4,610 | 24% | +0.04 |
| join | partial | 1000-ms | ? | 657 | 3% | -1.29 |
| join | sweep | 200-1000ms | 200-1000ms | 422 | 2% | +0.31 |
| join | partial | 200-1000ms | 200-1000ms | 288 | 1% | +0.80 |
| join | sweep | 1000-ms | 1000-ms | 243 | 1% | -2.30 |
| join | partial | 200-1000ms | 1000-ms | 195 | 1% | +0.63 |
| join | sweep | 200-1000ms | 1000-ms | 187 | 1% | -0.98 |
| join | sweep | 5-16ms | ? | 162 | 1% | -4.84 |
| join | sweep | 1000-ms | ? | 56 | 0% | -1.86 |
| join | partial | 200-1000ms | ? | 52 | 0% | +0.65 |
| join | sweep | 0-5ms | 0-5ms | 20 | 0% | -24.50 |
| join | sweep | 200-1000ms | ? | 20 | 0% | +8.50 |
| join | partial | 0-5ms | 0-5ms | 5 | 0% | -12.10 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 10,479 | 54% | +0.18 |
| join | sweep | — | — | 8,981 | 46% | -0.16 |

touch age >= 200 ms, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 0-5ms | ? | 9,292 | 30% | -0.21 |
| join | partial | 1000-ms | 1000-ms | 9,187 | 30% | +0.10 |
| join | sweep | 0-5ms | ? | 9,135 | 29% | -0.45 |
| join | partial | 200-1000ms | 200-1000ms | 1,145 | 4% | +0.41 |
| join | partial | 1000-ms | ? | 831 | 3% | -0.68 |
| join | partial | 200-1000ms | 1000-ms | 351 | 1% | +0.65 |
| join | sweep | 200-1000ms | 200-1000ms | 339 | 1% | +0.20 |
| join | sweep | 1000-ms | 1000-ms | 337 | 1% | -3.01 |
| join | sweep | 5-16ms | ? | 236 | 1% | -1.19 |
| join | sweep | 200-1000ms | 1000-ms | 79 | 0% | -5.58 |
| join | partial | 200-1000ms | ? | 71 | 0% | +2.23 |
| join | sweep | 1000-ms | ? | 49 | 0% | -1.32 |
| join | sweep | 200-1000ms | ? | 44 | 0% | -2.67 |
| join | partial | 0-5ms | 1000-ms | 16 | 0% | +9.04 |
| join | partial | 0-5ms | 0-5ms | 6 | 0% | +4.06 |
| join | sweep | 0-5ms | 200-1000ms | 5 | 0% | +1.55 |
| join | sweep | 0-5ms | 0-5ms | 5 | 0% | +3.60 |
| join | partial | 5-16ms | 5-16ms | 1 | 0% | +4.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 20,901 | 67% | -0.03 |
| join | sweep | — | — | 10,230 | 33% | -0.58 |

touch age >= 200 ms, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 43,158 | 57% | -0.60 |
| join | partial | 0-5ms | ? | 13,496 | 18% | +0.09 |
| join | partial | 1000-ms | 1000-ms | 10,742 | 14% | +0.13 |
| join | sweep | 1000-ms | 1000-ms | 2,072 | 3% | -2.06 |
| join | partial | 200-1000ms | 200-1000ms | 1,873 | 2% | +0.59 |
| join | sweep | 200-1000ms | 200-1000ms | 1,186 | 2% | +0.02 |
| join | sweep | 5-16ms | ? | 1,083 | 1% | -0.11 |
| join | partial | 1000-ms | ? | 841 | 1% | -0.25 |
| join | partial | 200-1000ms | 1000-ms | 729 | 1% | +0.30 |
| join | sweep | 200-1000ms | 1000-ms | 390 | 1% | -4.31 |
| join | sweep | 1000-ms | ? | 257 | 0% | -2.88 |
| join | partial | 200-1000ms | ? | 206 | 0% | +1.17 |
| join | sweep | 200-1000ms | ? | 179 | 0% | +0.23 |
| join | partial | 0-5ms | 1000-ms | 20 | 0% | +6.50 |
| join | partial | 5-16ms | ? | 20 | 0% | -24.50 |
| join | sweep | 0-5ms | 0-5ms | 20 | 0% | +3.60 |
| join | partial | 0-5ms | 0-5ms | 11 | 0% | -6.47 |
| join | partial | 5-16ms | 200-1000ms | 8 | 0% | -8.50 |
| **by kind/class** | | | | | | |
| join | sweep | — | — | 48,346 | 63% | -0.68 |
| join | partial | — | — | 27,947 | 37% | +0.12 |