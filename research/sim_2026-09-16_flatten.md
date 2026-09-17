# Quoter simulation, KXBTC15M, 2026-09-16

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live config (size 20 / max 100, $100), carry to settlement | 25 | 201.83 | 374.63 | -172.80 | -297.85 | 25 | 201.83 | 374.63 | -172.80 | 119.78 | 82.05 | 8.07 | 23.28 | 1.73 | -49.00 | 106,068 | 0.19 | 0.07 | 6.76 | 0.15 | 10,585 | 97.39 | 58.67 | 18.65 |
|  ↳ vetoes: {'join': 665545, 'greeks': 3378962} |
| + flatten at stop (take the touch) | 25 | 186.79 | 374.63 | -172.80 | -297.85 | 25 | 186.79 | 374.63 | -172.80 | 119.78 | 67.01 | 7.47 | 23.30 | 1.60 | -49.13 | 106,068 | 0.18 | 0.07 | 6.76 | 0.15 | 10,585 | 97.39 | 0.00 | 18.65 |
|  ↳ vetoes: {'join': 665545, 'greeks': 3378962} |
| + reduce-only exempt + flatten | 25 | 91.27 | 472.30 | -373.99 | -513.78 | 25 | 91.27 | 472.30 | -373.99 | 28.57 | 62.70 | 3.65 | 19.22 | 0.95 | -41.02 | 129,994 | 0.07 | -0.01 | 6.04 | 0.18 | 12,802 | 97.34 | 0.80 | 9.78 |
|  ↳ vetoes: {'join': 331620, 'greeks': 1689481} |
| + reduce-only exempt + skew 50% + flatten | 25 | 258.73 | 57.95 | 218.85 | -14.90 | 25 | 258.73 | 57.95 | 218.85 | -50.07 | 308.81 | 10.35 | 24.19 | 2.14 | -40.64 | 12,738 | 2.03 | 0.40 | 19.23 | 0.02 | 1,201 | 94.99 | 0.00 | 22.59 |
|  ↳ vetoes: {'join': 36105, 'greeks': 1689481} |
| + reduce-only + skew 50% + flatten, stop 3min | 25 | 181.59 | 85.57 | 102.97 | -72.02 | 25 | 181.59 | 85.57 | 102.97 | -58.19 | 239.78 | 7.26 | 27.51 | 1.32 | -41.41 | 19,090 | 0.95 | 0.04 | 17.81 | 0.03 | 1,802 | 95.64 | 0.00 | 12.47 |
|  ↳ vetoes: {'join': 38670, 'greeks': 2789583} |
| standing (size 100 / max 200), carry | 25 | 567.97 | 1,408.69 | -840.73 | -974.20 | 25 | 567.97 | 1,408.69 | -840.73 | 465.25 | 102.72 | 22.72 | 39.37 | 2.89 | -85.09 | 393,919 | 0.14 | 0.11 | 7.47 | 0.55 | 14,862 | 197.73 | 96.41 | 34.77 |
|  ↳ vetoes: {'join': 563484, 'greeks': 3378962} |
| standing + reduce-only + skew 50% + flatten | 25 | 76.35 | 146.42 | -40.12 | -188.85 | 25 | 76.35 | 146.42 | -40.12 | -385.93 | 462.28 | 3.05 | 52.27 | 0.29 | -117.76 | 31,404 | 0.24 | -0.15 | 18.16 | 0.04 | 1,107 | 174.28 | 3.88 | 36.97 |
|  ↳ vetoes: {'greeks': 1689481, 'join': 12401} |