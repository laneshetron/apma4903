# Quoter simulation, KXBTC15M, 2026-09-16

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live config, prorata, 9/5/11 (old model) | 25 | 81.11 | 189.31 | -105.29 | -123.74 | 25 | 81.11 | 189.31 | -105.29 | 64.34 | 16.78 | 3.24 | 3.64 | 4.46 | -6.42 | 52,755 | 0.15 | 0.13 | 9.11 | 0.07 | 4,898 | 19.71 | 0.00 | 3.33 |
|  ↳ vetoes: {'join': 366838, 'greeks': 3378962} |
| live config, prorata + price priority | 25 | 14.83 | 202.33 | -184.59 | -172.45 | 25 | 14.83 | 202.33 | -184.59 | 11.32 | 3.51 | 0.59 | 4.20 | 0.71 | -9.72 | 61,484 | 0.02 | 0.04 | 9.62 | 0.09 | 5,623 | 19.92 | 0.00 | 3.52 |
|  ↳ vetoes: {'join': 358883, 'priority_fills': 840, 'greeks': 3378962} |
| live config, FIFO + price priority | 25 | -11.96 | 99.87 | -109.44 | -121.03 | 25 | -11.96 | 99.87 | -109.44 | -19.35 | 7.38 | -0.48 | 4.38 | -0.55 | -9.36 | 37,479 | -0.03 | -0.08 | 8.84 | 0.05 | 3,044 | 19.97 | 0.00 | 2.96 |
|  ↳ vetoes: {'priority_fills': 1200, 'join': 326446, 'greeks': 3378962} |
| standing 100/200, prorata + price priority | 25 | 159.86 | 1,496.50 | -1,307.09 | -1,508.31 | 25 | 159.86 | 1,496.50 | -1,307.09 | 73.96 | 85.90 | 6.39 | 38.51 | 0.83 | -86.91 | 459,430 | 0.03 | -0.03 | 7.16 | 0.65 | 17,172 | 197.97 | 0.00 | 34.88 |
|  ↳ vetoes: {'join': 552792, 'priority_fills': 2444, 'greeks': 3378962} |
| standing 100/200, prorata + price priority, 2/2/2 | 25 | 663.01 | 1,864.97 | -1,173.11 | -1,311.34 | 25 | 663.01 | 1,864.97 | -1,173.11 | 594.84 | 68.17 | 26.52 | 39.73 | 3.34 | -57.88 | 550,881 | 0.12 | 0.10 | 13.65 | 0.78 | 20,876 | 198.08 | 0.00 | 34.55 |
|  ↳ vetoes: {'priority_fills': 2354, 'join': 562841, 'greeks': 3378962} |