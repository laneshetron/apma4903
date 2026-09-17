# Quoter simulation, KXBTC15M, 2026-09-16

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| size 20 / max 20, flatten (live) | 25 | 81.11 | 189.31 | -105.29 | -123.74 | 25 | 81.11 | 189.31 | -105.29 | 64.34 | 16.78 | 3.24 | 3.64 | 4.46 | -6.42 | 52,755 | 0.15 | 0.13 | 9.11 | 0.07 | 4,898 | 19.71 | 0.00 | 3.33 |
|  ↳ vetoes: {'join': 366838, 'greeks': 3378962} |
| size 20 / max 40, flatten | 25 | 72.05 | 312.93 | -234.34 | -218.64 | 25 | 72.05 | 312.93 | -234.34 | 50.85 | 21.20 | 2.88 | 9.98 | 1.44 | -22.95 | 88,028 | 0.08 | 0.10 | 7.39 | 0.12 | 8,604 | 39.28 | 0.00 | 7.62 |
|  ↳ vetoes: {'join': 570596, 'greeks': 3378962} |
| size 20 / max 40, flatten + size skew | 25 | 126.76 | 346.99 | -214.74 | -224.51 | 25 | 126.76 | 346.99 | -214.74 | 113.07 | 13.69 | 5.07 | 7.65 | 3.31 | -14.44 | 97,351 | 0.13 | 0.13 | 7.80 | 0.14 | 8,889 | 29.76 | 0.00 | 6.38 |
|  ↳ vetoes: {'join': 562747, 'greeks': 3378962} |
| size 20 / max 60, flatten + size skew | 25 | 100.17 | 388.75 | -280.69 | -265.66 | 25 | 100.17 | 388.75 | -280.69 | 83.29 | 16.89 | 4.01 | 11.12 | 1.80 | -24.21 | 110,196 | 0.09 | 0.10 | 6.80 | 0.16 | 11,297 | 46.52 | 0.00 | 9.17 |
|  ↳ vetoes: {'join': 693096, 'greeks': 3378962} |
| size 20 / max 100, flatten + size skew | 25 | 114.46 | 415.31 | -290.23 | -321.26 | 25 | 114.46 | 415.31 | -290.23 | 74.31 | 40.15 | 4.58 | 14.97 | 1.53 | -32.90 | 118,331 | 0.10 | 0.08 | 6.46 | 0.17 | 12,615 | 81.95 | 0.00 | 12.69 |
|  ↳ vetoes: {'join': 769965, 'greeks': 3378962} |
| size 10 / max 40, flatten + size skew | 25 | 47.84 | 208.47 | -156.12 | -156.82 | 25 | 47.84 | 208.47 | -156.12 | 32.74 | 15.10 | 1.91 | 6.80 | 1.41 | -14.43 | 59,373 | 0.08 | 0.08 | 6.69 | 0.08 | 10,683 | 32.64 | 0.00 | 5.41 |
|  ↳ vetoes: {'join': 751963, 'greeks': 3378962} |
| size 100 / max 200, flatten + size skew | 25 | 614.07 | 1,557.99 | -918.23 | -1,121.97 | 25 | 614.07 | 1,557.99 | -918.23 | 578.54 | 35.54 | 24.56 | 36.96 | 3.32 | -74.57 | 433,931 | 0.14 | 0.12 | 8.23 | 0.61 | 15,806 | 148.36 | 0.00 | 29.10 |
|  ↳ vetoes: {'join': 563921, 'greeks': 3378962} |