# Quoter simulation, KXBTC15M, 2026-09-14

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base (2ms, cancel $2/1s, stop 5min, max pos 200) | 65 | 2,861.59 | 7,498.50 | -4,638.59 | -4,799.15 | 32 | 1,269.44 | 2,837.42 | -1,567.99 | 2,592.86 | 268.73 | 44.02 | 36.14 | 9.82 | -47.47 | 1,786,588 | 0.16 | 0.16 | 15.57 | 1.49 | 95,160 | 187.95 | 86.21 | 73.03 |
| value policy: cancel if edge < 0, debounce 300ms | 65 | 2,901.72 | 6,476.85 | -3,574.67 | -3,683.25 | 32 | 1,128.44 | 2,450.81 | -1,322.36 | 2,557.12 | 344.60 | 44.64 | 37.57 | 9.58 | -57.96 | 1,541,464 | 0.19 | 0.20 | 16.20 | 1.28 | 83,010 | 187.52 | 83.30 | 70.02 |
|  ↳ vetoes: {'edge': 2274494} |
| value policy: cancel if edge < 0, no debounce | 65 | 2,415.52 | 4,386.63 | -1,970.36 | -2,166.28 | 32 | 965.18 | 1,662.62 | -697.44 | 1,981.31 | 434.20 | 37.16 | 28.24 | 10.61 | -32.97 | 1,053,351 | 0.23 | 0.22 | 13.29 | 0.88 | 57,329 | 186.43 | 95.03 | 80.92 |
|  ↳ vetoes: {'edge': 7995337} |