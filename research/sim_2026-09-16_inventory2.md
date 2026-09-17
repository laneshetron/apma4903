# Quoter simulation, KXBTC15M, 2026-09-16

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| size 20 / max 100, $100 (live config) | 25 | 201.83 | 374.63 | -172.80 | -297.85 | 25 | 201.83 | 374.63 | -172.80 | 119.78 | 82.05 | 8.07 | 23.28 | 1.73 | -49.00 | 106,068 | 0.19 | 0.07 | 6.76 | 0.15 | 10,585 | 97.39 | 58.67 | 18.65 |
|  ↳ vetoes: {'join': 665545, 'greeks': 3378962} |
| + reduce-only exempt from greeks cap and join gate | 25 | 98.22 | 472.30 | -373.99 | -513.78 | 25 | 98.22 | 472.30 | -373.99 | 28.57 | 69.65 | 3.93 | 19.10 | 1.03 | -40.69 | 129,994 | 0.08 | -0.01 | 6.04 | 0.18 | 12,802 | 97.34 | 35.87 | 9.78 |
|  ↳ vetoes: {'join': 331620, 'greeks': 1689481} |
| + skew above 50% of cap | 25 | 344.80 | 34.55 | 310.24 | 24.72 | 25 | 344.80 | 34.55 | 310.24 | -45.28 | 390.08 | 13.79 | 25.60 | 2.69 | -40.41 | 7,470 | 4.62 | 0.86 | 18.53 | 0.01 | 696 | 94.83 | 85.97 | 29.79 |
|  ↳ vetoes: {'join': 344414, 'greeks': 3378962} |
| + skew above 25% of cap | 25 | 205.40 | 23.43 | 181.98 | 22.83 | 25 | 205.40 | 23.43 | 181.98 | -91.04 | 296.44 | 8.22 | 29.83 | 1.38 | -41.83 | 5,335 | 3.85 | 0.79 | 23.06 | 0.01 | 490 | 96.52 | 87.96 | 30.69 |
|  ↳ vetoes: {'join': 339944, 'greeks': 3378962} |
| + reduce-only exempt + skew 50% | 25 | 276.80 | 57.95 | 218.85 | -14.90 | 25 | 276.80 | 57.95 | 218.85 | -50.07 | 326.87 | 11.07 | 24.16 | 2.29 | -40.41 | 12,738 | 2.17 | 0.40 | 19.23 | 0.02 | 1,201 | 94.99 | 72.27 | 22.59 |
|  ↳ vetoes: {'join': 36105, 'greeks': 1689481} |
| size 100 / max 200 (standing) | 25 | 567.97 | 1,408.69 | -840.73 | -974.20 | 25 | 567.97 | 1,408.69 | -840.73 | 465.25 | 102.72 | 22.72 | 39.37 | 2.89 | -85.09 | 393,919 | 0.14 | 0.11 | 7.47 | 0.55 | 14,862 | 197.73 | 96.41 | 34.77 |
|  ↳ vetoes: {'join': 563484, 'greeks': 3378962} |
| size 100 / max 200 + reduce-only exempt + skew 50% | 25 | 105.82 | 146.42 | -40.12 | -188.85 | 25 | 105.82 | 146.42 | -40.12 | -385.93 | 491.74 | 4.23 | 52.24 | 0.41 | -117.73 | 31,404 | 0.34 | -0.15 | 18.16 | 0.04 | 1,107 | 174.28 | 114.95 | 36.97 |
|  ↳ vetoes: {'greeks': 1689481, 'join': 12401} |