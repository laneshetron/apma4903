# Quoter simulation, KXBTC15M, 2026-09-17

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live config (size 20 / max 100, $100), carry to settlement | 15 | 100.29 | 327.21 | -226.92 | -228.90 | 15 | 100.29 | 327.21 | -226.92 | 57.51 | 42.78 | 6.69 | 17.33 | 1.49 | -35.99 | 81,776 | 0.12 | 0.15 | 7.70 | 0.22 | 8,758 | 98.93 | 60.06 | 11.16 |
|  ↳ vetoes: {'join': 336146, 'greeks': 2144340} |
| + flatten at stop (take the touch) | 15 | 90.68 | 327.21 | -226.92 | -228.90 | 15 | 90.68 | 327.21 | -226.92 | 57.51 | 33.17 | 6.05 | 17.69 | 1.32 | -38.01 | 81,776 | 0.11 | 0.15 | 7.70 | 0.22 | 8,758 | 98.93 | 0.00 | 11.16 |
|  ↳ vetoes: {'join': 336146, 'greeks': 2144340} |
| + reduce-only exempt + flatten | 15 | 94.12 | 400.67 | -302.10 | -340.24 | 15 | 94.12 | 400.67 | -302.10 | 70.47 | 23.65 | 6.27 | 16.90 | 1.44 | -19.49 | 98,568 | 0.10 | 0.07 | 7.17 | 0.26 | 10,555 | 98.47 | 0.00 | 5.72 |
|  ↳ vetoes: {'join': 160870, 'greeks': 1072170} |
| + reduce-only exempt + skew 50% + flatten | 15 | -34.82 | 46.71 | -71.29 | 25.45 | 15 | -34.82 | 46.71 | -71.29 | -237.23 | 202.40 | -2.32 | 25.74 | -0.35 | -49.46 | 10,646 | -0.33 | 0.81 | 17.37 | 0.03 | 1,059 | 98.51 | 0.00 | 12.25 |
|  ↳ vetoes: {'join': 14498, 'greeks': 1194180} |
| + reduce-only + skew 50% + flatten, stop 3min | 15 | -61.02 | 59.09 | -113.55 | 7.78 | 15 | -61.02 | 59.09 | -113.55 | -281.71 | 220.69 | -4.07 | 22.78 | -0.69 | -49.17 | 13,498 | -0.45 | 0.61 | 17.67 | 0.04 | 1,364 | 98.51 | 1.33 | 9.54 |
|  ↳ vetoes: {'join': 15670, 'greeks': 1669881} |
| standing (size 100 / max 200), carry | 15 | 259.82 | 1,197.40 | -937.58 | -892.86 | 15 | 259.82 | 1,197.40 | -937.58 | 190.41 | 69.41 | 17.32 | 41.25 | 1.63 | -98.95 | 297,611 | 0.09 | 0.10 | 8.67 | 0.79 | 12,300 | 198.94 | 77.94 | 13.03 |
|  ↳ vetoes: {'join': 282055, 'greeks': 2144340} |
| standing + reduce-only + skew 50% + flatten | 15 | 187.41 | 192.62 | 12.83 | 134.80 | 15 | 187.41 | 192.62 | 12.83 | -242.50 | 429.91 | 12.49 | 31.58 | 1.53 | -42.81 | 40,550 | 0.46 | 0.88 | 16.41 | 0.11 | 1,542 | 187.25 | 0.00 | 21.36 |
|  ↳ vetoes: {'join': 6137, 'greeks': 1072170} |