# Quoter simulation, KXBTC15M, 2026-09-17

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| place 9 / cancel 5 / signal 11, engine lag 6 | 70 | -185.45 | 613.82 | -791.05 | -757.25 | 70 | -185.45 | 613.82 | -791.05 | -201.40 | 15.95 | -2.65 | 4.46 | -4.97 | -14.76 | 200,387 | -0.09 | -0.07 | 18.64 | 0.13 | 19,893 | 19.87 | 0.00 | 9.43 |
|  ↳ vetoes: {'join': 986328, 'priority_fills': 5144, 'greeks': 10730316} |
| place 5 / cancel 3 / signal 11, engine lag 6 | 70 | -173.69 | 638.87 | -805.43 | -784.34 | 70 | -173.69 | 638.87 | -805.43 | -171.57 | -2.12 | -2.48 | 4.88 | -4.26 | -19.12 | 207,826 | -0.08 | -0.07 | 19.10 | 0.14 | 20,498 | 19.89 | 0.00 | 8.32 |
|  ↳ vetoes: {'join': 938017, 'priority_fills': 5142, 'greeks': 10730316} |
| place 3 / cancel 3 / signal 11, engine lag 6 | 70 | -129.36 | 648.49 | -771.81 | -786.63 | 70 | -129.36 | 648.49 | -771.81 | -137.56 | 8.20 | -1.85 | 4.13 | -3.74 | -13.68 | 211,785 | -0.06 | -0.06 | 19.73 | 0.14 | 20,950 | 19.85 | 0.00 | 7.21 |
|  ↳ vetoes: {'join': 938159, 'priority_fills': 5239, 'greeks': 10730316} |
| place 2 / cancel 2 / signal 11, engine lag 6 | 70 | -145.28 | 663.94 | -801.52 | -802.07 | 70 | -145.28 | 663.94 | -801.52 | -136.44 | -8.85 | -2.08 | 4.72 | -3.68 | -13.39 | 214,441 | -0.07 | -0.05 | 20.24 | 0.14 | 21,054 | 19.88 | 0.00 | 9.14 |
|  ↳ vetoes: {'join': 921573, 'priority_fills': 5158, 'greeks': 10730316} |
| place 2 / cancel 2 / signal 2, engine lag 6 | 70 | -130.27 | 661.54 | -784.29 | -788.45 | 70 | -130.27 | 661.54 | -784.29 | -124.91 | -5.36 | -1.86 | 4.80 | -3.24 | -13.13 | 213,148 | -0.06 | -0.05 | 20.21 | 0.14 | 20,904 | 19.88 | 0.00 | 8.79 |
|  ↳ vetoes: {'join': 913242, 'priority_fills': 5070, 'greeks': 10730316} |
| place 1 / cancel 1 / signal 1, engine lag 6 | 70 | -89.16 | 679.59 | -762.09 | -745.33 | 70 | -89.16 | 679.59 | -762.09 | -82.07 | -7.10 | -1.27 | 5.00 | -2.13 | -16.66 | 217,064 | -0.04 | -0.03 | 21.20 | 0.14 | 21,243 | 19.90 | 0.00 | 8.24 |
|  ↳ vetoes: {'join': 891518, 'priority_fills': 5019, 'greeks': 10730316} |
| place 9 / cancel 5 / signal 11, engine lag 0 (hypothetical) | 70 | -77.07 | 674.75 | -745.57 | -731.14 | 70 | -77.07 | 674.75 | -745.57 | -89.35 | 12.28 | -1.10 | 4.15 | -2.22 | -12.62 | 214,170 | -0.04 | -0.03 | 23.70 | 0.14 | 20,952 | 19.88 | 0.00 | 7.30 |
|  ↳ vetoes: {'join': 830453, 'priority_fills': 4914, 'greeks': 10730316} |
| place 2 / cancel 2 / signal 2, engine lag 0 (hypothetical) | 70 | 178.11 | 831.31 | -646.52 | -639.32 | 70 | 178.11 | 831.31 | -646.52 | 164.96 | 13.14 | 2.54 | 3.91 | 5.45 | -5.11 | 254,280 | 0.07 | 0.09 | 29.11 | 0.17 | 25,005 | 19.91 | 0.00 | 7.79 |
|  ↳ vetoes: {'join': 825048, 'priority_fills': 5079, 'greeks': 10730316} |
| place 9 / cancel 5 / signal 11, engine lag 6, pessimistic queue | 70 | -372.48 | 259.20 | -623.21 | -567.25 | 70 | -372.48 | 259.20 | -623.21 | -390.41 | 17.93 | -5.32 | 4.19 | -10.63 | -20.67 | 125,641 | -0.30 | -0.25 | 25.82 | 0.08 | 11,839 | 19.84 | 0.00 | 9.78 |
|  ↳ vetoes: {'join': 875136, 'priority_fills': 7076, 'greeks': 10730316} |
| place 2 / cancel 2 / signal 11, engine lag 6, pessimistic queue | 70 | -329.07 | 307.99 | -630.38 | -584.70 | 70 | -329.07 | 307.99 | -630.38 | -330.63 | 1.56 | -4.70 | 4.48 | -8.77 | -18.17 | 137,804 | -0.24 | -0.21 | 28.63 | 0.09 | 12,826 | 19.89 | 0.00 | 7.92 |
|  ↳ vetoes: {'join': 803452, 'priority_fills': 6896, 'greeks': 10730316} |