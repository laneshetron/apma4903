# Quoter simulation, KXETH15M, 2026-09-17

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 88 | -471.10 | 460.01 | -921.53 | -905.52 | 88 | -471.10 | 460.01 | -921.53 | -469.53 | -1.57 | -5.35 | 3.40 | -14.79 | -14.09 | 169,128 | -0.28 | -0.27 | 47.17 | 2.04 | 23,991 | 19.79 | 0.00 | 10.43 |
|  ↳ vetoes: {'priority_fills': 12932, 'greeks': 3405626} |
| oracle: dodge every sweep-through, 50 ms warning | 88 | 11.61 | 279.27 | -258.74 | -252.04 | 88 | 11.61 | 279.27 | -258.74 | 37.14 | -25.53 | 0.13 | 3.33 | 0.37 | -8.62 | 97,540 | 0.01 | 0.02 | 53.22 | 1.18 | 13,945 | 19.67 | 0.00 | 9.73 |
|  ↳ vetoes: {'ext_veto': 159640, 'priority_fills': 6413, 'greeks': 3405626} |
| oracle: dodge every sweep-through, 250 ms warning | 88 | 112.99 | 197.12 | -75.51 | -81.30 | 88 | 112.99 | 197.12 | -75.51 | 103.60 | 9.38 | 1.28 | 3.11 | 3.87 | -6.95 | 71,849 | 0.16 | 0.17 | 57.61 | 0.87 | 10,497 | 19.51 | 0.00 | 9.47 |
|  ↳ vetoes: {'ext_veto': 423937, 'priority_fills': 4566, 'greeks': 3405626} |
| oracle: dodge every sweep-through, 1 s warning | 88 | 189.34 | 171.81 | 25.03 | -8.82 | 88 | 189.34 | 171.81 | 25.03 | 159.97 | 29.37 | 2.15 | 2.70 | 7.47 | -4.35 | 60,958 | 0.31 | 0.29 | 56.76 | 0.73 | 8,906 | 19.51 | 0.00 | 8.55 |
|  ↳ vetoes: {'ext_veto': 1185540, 'priority_fills': 3764, 'greeks': 3405626} |
| oracle: dodge adverse fills only (mo30 < 0), 250 ms | 88 | 216.54 | 285.18 | -59.65 | -102.90 | 88 | 216.54 | 285.18 | -59.65 | 179.06 | 37.48 | 2.46 | 3.41 | 6.77 | -5.67 | 102,494 | 0.21 | 0.19 | 51.27 | 1.24 | 14,715 | 19.78 | 0.00 | 9.90 |
|  ↳ vetoes: {'ext_veto': 312321, 'priority_fills': 7213, 'greeks': 3405626} |