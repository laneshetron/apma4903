# Quoter simulation, KXBTC15M, 2026-09-16

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| place 9 / cancel 5 / signal 11, engine lag 6 | 25 | -10.58 | 179.77 | -187.08 | -195.58 | 25 | -10.58 | 179.77 | -187.08 | -9.09 | -1.49 | -0.42 | 4.09 | -0.52 | -11.70 | 59,759 | -0.02 | -0.03 | 19.40 | 0.08 | 5,676 | 19.78 | 0.00 | 3.76 |
|  ↳ vetoes: {'join': 405823, 'priority_fills': 1289, 'greeks': 3378962} |
| place 5 / cancel 3 / signal 11, engine lag 6 | 25 | 6.20 | 188.75 | -178.99 | -176.92 | 25 | 6.20 | 188.75 | -178.99 | -3.81 | 10.01 | 0.25 | 4.67 | 0.27 | -11.12 | 62,482 | 0.01 | 0.03 | 20.41 | 0.09 | 5,962 | 19.86 | 0.00 | 4.05 |
|  ↳ vetoes: {'join': 390590, 'priority_fills': 1263, 'greeks': 3378962} |
| place 3 / cancel 3 / signal 11, engine lag 6 | 25 | 7.03 | 192.17 | -182.36 | -181.04 | 25 | 7.03 | 192.17 | -182.36 | 3.49 | 3.55 | 0.28 | 4.28 | 0.33 | -10.17 | 63,572 | 0.01 | 0.01 | 20.67 | 0.09 | 6,068 | 19.74 | 0.00 | 3.44 |
|  ↳ vetoes: {'join': 391549, 'priority_fills': 1287, 'greeks': 3378962} |
| place 2 / cancel 2 / signal 11, engine lag 6 | 25 | 2.14 | 195.69 | -189.86 | -167.86 | 25 | 2.14 | 195.69 | -189.86 | -0.33 | 2.47 | 0.09 | 4.36 | 0.10 | -9.89 | 64,295 | 0.00 | 0.02 | 21.14 | 0.09 | 6,079 | 19.94 | 0.00 | 4.32 |
|  ↳ vetoes: {'join': 381309, 'priority_fills': 1261, 'greeks': 3378962} |
| place 2 / cancel 2 / signal 2, engine lag 6 | 25 | 12.99 | 194.05 | -177.52 | -160.02 | 25 | 12.99 | 194.05 | -177.52 | 6.86 | 6.13 | 0.52 | 3.88 | 0.67 | -7.05 | 63,531 | 0.02 | 0.03 | 21.13 | 0.09 | 5,997 | 19.91 | 0.00 | 4.12 |
|  ↳ vetoes: {'join': 377785, 'priority_fills': 1230, 'greeks': 3378962} |
| place 1 / cancel 1 / signal 1, engine lag 6 | 25 | 14.73 | 201.03 | -182.80 | -173.37 | 25 | 14.73 | 201.03 | -182.80 | 12.22 | 2.51 | 0.59 | 3.91 | 0.75 | -6.85 | 65,026 | 0.02 | 0.04 | 22.25 | 0.09 | 6,246 | 19.82 | 0.00 | 4.15 |
|  ↳ vetoes: {'join': 373753, 'priority_fills': 1265, 'greeks': 3378962} |
| place 9 / cancel 5 / signal 11, engine lag 0 (hypothetical) | 25 | 14.12 | 202.26 | -185.02 | -171.70 | 25 | 14.12 | 202.26 | -185.02 | 9.52 | 4.60 | 0.56 | 4.10 | 0.69 | -9.72 | 65,049 | 0.02 | 0.04 | 24.73 | 0.09 | 6,130 | 19.89 | 0.00 | 3.61 |
|  ↳ vetoes: {'join': 351231, 'priority_fills': 1226, 'greeks': 3378962} |
| place 2 / cancel 2 / signal 2, engine lag 0 (hypothetical) | 25 | 100.63 | 244.04 | -140.87 | -127.26 | 25 | 100.63 | 244.04 | -140.87 | 109.76 | -9.13 | 4.03 | 4.06 | 4.96 | -5.19 | 75,619 | 0.13 | 0.14 | 30.03 | 0.11 | 7,109 | 19.73 | 0.00 | 2.98 |
|  ↳ vetoes: {'priority_fills': 1201, 'join': 356078, 'greeks': 3378962} |
| place 9 / cancel 5 / signal 11, engine lag 6, pessimistic queue | 25 | -53.43 | 79.92 | -130.44 | -169.68 | 25 | -53.43 | 79.92 | -130.44 | -41.43 | -12.00 | -2.14 | 4.65 | -2.30 | -14.01 | 38,764 | -0.14 | -0.16 | 26.41 | 0.05 | 3,484 | 19.88 | 0.00 | 3.38 |
|  ↳ vetoes: {'join': 368181, 'priority_fills': 1795, 'greeks': 3378962} |
| place 2 / cancel 2 / signal 11, engine lag 6, pessimistic queue | 25 | -11.86 | 95.25 | -104.06 | -130.31 | 25 | -11.86 | 95.25 | -104.06 | -18.56 | 6.70 | -0.47 | 4.47 | -0.53 | -12.35 | 42,311 | -0.03 | -0.09 | 28.99 | 0.06 | 3,732 | 19.98 | 0.00 | 3.69 |
|  ↳ vetoes: {'join': 343817, 'priority_fills': 1678, 'greeks': 3378962} |