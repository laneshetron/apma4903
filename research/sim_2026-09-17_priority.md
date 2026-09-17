# Quoter simulation, KXBTC15M, 2026-09-17

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live config, prorata, 9/5/11 (old model) | 19 | 40.38 | 204.16 | -162.17 | -160.34 | 19 | 40.38 | 204.16 | -162.17 | 31.49 | 8.89 | 2.13 | 4.29 | 2.16 | -7.81 | 53,906 | 0.07 | 0.08 | 10.97 | 0.12 | 5,396 | 19.62 | 0.00 | 2.07 |
|  ↳ vetoes: {'join': 272013, 'greeks': 2533340} |
| live config, prorata + price priority | 19 | -9.51 | 229.43 | -237.81 | -245.49 | 19 | -9.51 | 229.43 | -237.81 | -5.46 | -4.05 | -0.50 | 4.51 | -0.48 | -10.89 | 66,643 | -0.01 | -0.02 | 11.40 | 0.14 | 6,594 | 19.87 | 0.00 | 1.52 |
|  ↳ vetoes: {'join': 268371, 'priority_fills': 1387, 'greeks': 2533340} |
| live config, FIFO + price priority | 19 | -80.00 | 115.83 | -194.08 | -201.86 | 19 | -80.00 | 115.83 | -194.08 | -71.93 | -8.07 | -4.21 | 3.67 | -5.00 | -11.27 | 42,227 | -0.19 | -0.19 | 11.83 | 0.09 | 3,703 | 19.85 | 0.00 | 1.96 |
|  ↳ vetoes: {'join': 216586, 'priority_fills': 2066, 'greeks': 2533340} |
| standing 100/200, prorata + price priority | 19 | -165.15 | 1,685.76 | -1,837.83 | -1,905.15 | 19 | -165.15 | 1,685.76 | -1,837.83 | -199.67 | 34.52 | -8.69 | 39.33 | -0.96 | -94.05 | 488,803 | -0.03 | -0.02 | 8.80 | 1.04 | 20,897 | 198.34 | 0.00 | 16.65 |
|  ↳ vetoes: {'join': 399066, 'priority_fills': 4075, 'greeks': 2533340} |
| standing 100/200, prorata + price priority, 2/2/2 | 19 | 453.50 | 2,126.39 | -1,651.55 | -1,681.24 | 19 | 453.50 | 2,126.39 | -1,651.55 | 428.49 | 25.01 | 23.87 | 39.16 | 2.66 | -96.44 | 589,949 | 0.08 | 0.09 | 14.83 | 1.26 | 25,664 | 199.52 | 0.00 | 24.33 |
|  ↳ vetoes: {'join': 413182, 'priority_fills': 4054, 'greeks': 2533340} |