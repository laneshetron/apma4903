# Quoter simulation, KXBTC15M, 2026-09-17

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| size 20 / max 100, $100 (live config) | 15 | 100.29 | 327.21 | -226.92 | -228.90 | 15 | 100.29 | 327.21 | -226.92 | 57.51 | 42.78 | 6.69 | 17.33 | 1.49 | -35.99 | 81,776 | 0.12 | 0.15 | 7.70 | 0.22 | 8,758 | 98.93 | 60.06 | 11.16 |
|  ↳ vetoes: {'join': 336146, 'greeks': 2144340} |
| + reduce-only exempt from greeks cap and join gate | 15 | 98.57 | 400.67 | -302.10 | -340.24 | 15 | 98.57 | 400.67 | -302.10 | 70.47 | 28.10 | 6.57 | 17.07 | 1.49 | -19.24 | 98,568 | 0.10 | 0.07 | 7.17 | 0.26 | 10,555 | 98.47 | 37.21 | 5.72 |
|  ↳ vetoes: {'join': 160870, 'greeks': 1072170} |
| + skew above 50% of cap | 15 | 22.77 | 24.92 | -2.15 | 19.52 | 15 | 22.77 | 24.92 | -2.15 | -113.66 | 136.43 | 1.52 | 29.21 | 0.20 | -49.80 | 5,876 | 0.39 | 0.95 | 16.40 | 0.02 | 573 | 98.30 | 85.35 | 15.56 |
|  ↳ vetoes: {'join': 157304, 'greeks': 2144340} |
| + skew above 25% of cap | 15 | 90.86 | 17.72 | 73.14 | -0.45 | 15 | 90.86 | 17.72 | 73.14 | -67.60 | 158.47 | 6.06 | 30.68 | 0.76 | -43.34 | 4,268 | 2.13 | 0.58 | 24.75 | 0.01 | 404 | 97.83 | 87.76 | 15.45 |
|  ↳ vetoes: {'join': 156820, 'greeks': 2144340} |
| + reduce-only exempt + skew 50% | 15 | -24.59 | 46.71 | -71.29 | 25.45 | 15 | -24.59 | 46.71 | -71.29 | -237.23 | 212.64 | -1.64 | 25.87 | -0.25 | -49.43 | 10,646 | -0.23 | 0.81 | 17.37 | 0.03 | 1,059 | 98.51 | 74.72 | 12.25 |
|  ↳ vetoes: {'join': 14498, 'greeks': 1194180} |
| size 100 / max 200 (standing) | 15 | 259.82 | 1,197.40 | -937.58 | -892.86 | 15 | 259.82 | 1,197.40 | -937.58 | 190.41 | 69.41 | 17.32 | 41.25 | 1.63 | -98.95 | 297,611 | 0.09 | 0.10 | 8.67 | 0.79 | 12,300 | 198.94 | 77.94 | 13.03 |
|  ↳ vetoes: {'join': 282055, 'greeks': 2144340} |
| size 100 / max 200 + reduce-only exempt + skew 50% | 15 | 205.46 | 192.62 | 12.83 | 134.80 | 15 | 205.46 | 192.62 | 12.83 | -242.50 | 447.96 | 13.70 | 31.33 | 1.69 | -40.85 | 40,550 | 0.51 | 0.88 | 16.41 | 0.11 | 1,542 | 187.25 | 125.82 | 21.36 |
|  ↳ vetoes: {'join': 6137, 'greeks': 1072170} |