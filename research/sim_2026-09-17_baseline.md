# Quoter simulation, KXBTC15M, 2026-09-17

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live 20/20 $100 flatten (baseline) | 56 | -138.46 | 506.56 | -639.23 | -612.52 | 56 | -138.46 | 506.56 | -639.23 | -147.39 | 8.92 | -2.47 | 4.63 | -4.00 | -14.76 | 166,048 | -0.08 | -0.07 | 19.37 | 0.14 | 16,782 | 19.88 | 0.00 | 6.84 |
|  ↳ vetoes: {'join': 810004, 'priority_fills': 4407, 'greeks': 7592138} |