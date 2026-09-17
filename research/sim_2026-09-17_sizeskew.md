# Quoter simulation, KXBTC15M, 2026-09-17

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| size 20 / max 20, flatten (live) | 15 | 38.71 | 161.01 | -120.80 | -101.08 | 15 | 38.71 | 161.01 | -120.80 | 32.43 | 6.27 | 2.58 | 4.46 | 2.24 | -7.81 | 40,665 | 0.10 | 0.12 | 10.80 | 0.11 | 4,055 | 19.65 | 0.00 | 1.84 |
|  ↳ vetoes: {'join': 193390, 'greeks': 2144340} |
| size 20 / max 40, flatten | 15 | 70.99 | 273.88 | -200.38 | -223.47 | 15 | 70.99 | 273.88 | -200.38 | 60.13 | 10.85 | 4.73 | 7.84 | 2.34 | -15.17 | 68,904 | 0.10 | 0.10 | 8.33 | 0.18 | 7,224 | 39.85 | 0.00 | 3.08 |
|  ↳ vetoes: {'join': 290820, 'greeks': 2144340} |
| size 20 / max 40, flatten + size skew | 15 | 67.11 | 299.20 | -229.90 | -224.54 | 15 | 67.11 | 299.20 | -229.90 | 59.86 | 7.25 | 4.47 | 7.09 | 2.45 | -14.16 | 75,483 | 0.09 | 0.10 | 8.96 | 0.20 | 7,424 | 29.90 | 0.00 | 2.76 |
|  ↳ vetoes: {'join': 295596, 'greeks': 2144340} |
| size 20 / max 60, flatten + size skew | 15 | 58.55 | 336.39 | -274.49 | -281.90 | 15 | 58.55 | 336.39 | -274.49 | 46.28 | 12.27 | 3.90 | 10.73 | 1.41 | -25.66 | 84,927 | 0.07 | 0.08 | 7.76 | 0.23 | 9,260 | 46.50 | 0.00 | 4.16 |
|  ↳ vetoes: {'join': 351011, 'greeks': 2144340} |
| size 20 / max 100, flatten + size skew | 15 | 58.84 | 360.41 | -296.65 | -306.93 | 15 | 58.84 | 360.41 | -296.65 | 45.48 | 13.37 | 3.92 | 15.65 | 0.97 | -37.35 | 91,215 | 0.06 | 0.07 | 7.06 | 0.24 | 10,421 | 82.65 | 0.00 | 6.11 |
|  ↳ vetoes: {'join': 383695, 'greeks': 2144340} |
| size 10 / max 40, flatten + size skew | 15 | 30.20 | 182.84 | -150.59 | -163.36 | 15 | 30.20 | 182.84 | -150.59 | 22.72 | 7.48 | 2.01 | 6.91 | 1.13 | -18.20 | 46,270 | 0.07 | 0.06 | 7.26 | 0.12 | 8,702 | 32.69 | 0.00 | 2.60 |
|  ↳ vetoes: {'join': 376194, 'greeks': 2144340} |
| size 100 / max 200, flatten + size skew | 15 | 317.99 | 1,322.30 | -993.39 | -925.96 | 15 | 317.99 | 1,322.30 | -993.39 | 290.06 | 27.93 | 21.20 | 39.34 | 2.09 | -67.03 | 329,609 | 0.10 | 0.12 | 9.50 | 0.88 | 13,069 | 149.74 | 0.00 | 13.49 |
|  ↳ vetoes: {'join': 292881, 'greeks': 2144340} |