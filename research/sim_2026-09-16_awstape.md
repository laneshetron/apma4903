# Quoter simulation, KXBTC15M, 2026-09-16

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2ms all (reference) | 18 | 772.89 | 1,634.03 | -860.66 | -955.47 | 18 | 772.89 | 1,634.03 | -860.66 | 787.76 | -14.87 | 42.94 | 28.28 | 6.44 | -45.30 | 423,189 | 0.18 | 0.17 | 13.01 | 0.82 | 15,953 | 197.70 | 88.94 | 23.97 |
| REST explicit shard (place 9 / cancel 5 / signal 11) | 18 | 344.78 | 1,294.66 | -949.40 | -875.51 | 18 | 344.78 | 1,294.66 | -949.40 | 324.05 | 20.73 | 19.15 | 34.66 | 2.34 | -70.57 | 339,831 | 0.10 | 0.13 | 4.93 | 0.66 | 12,759 | 198.12 | 85.19 | 22.93 |
| REST explicit + join gate + greeks cap | 18 | 510.07 | 844.33 | -334.26 | -362.36 | 18 | 510.07 | 844.33 | -334.26 | 392.62 | 117.45 | 28.34 | 32.89 | 3.66 | -61.30 | 237,542 | 0.21 | 0.19 | 9.36 | 0.46 | 8,984 | 197.29 | 97.64 | 24.28 |
|  ↳ vetoes: {'join': 450030, 'greeks': 2342512} |
| REST explicit, max pos 100 | 18 | 211.69 | 726.99 | -514.82 | -556.36 | 18 | 211.69 | 726.99 | -514.82 | 215.71 | -4.02 | 11.76 | 15.92 | 3.13 | -24.14 | 195,173 | 0.11 | 0.07 | 5.95 | 0.38 | 6,435 | 99.07 | 35.43 | 9.28 |
| FIX-like (place 5 / cancel 3 / signal 9) | 18 | 494.43 | 1,398.04 | -903.12 | -939.11 | 18 | 494.43 | 1,398.04 | -903.12 | 513.66 | -19.23 | 27.47 | 28.52 | 4.09 | -67.58 | 366,428 | 0.13 | 0.11 | 9.03 | 0.71 | 13,649 | 196.73 | 80.65 | 22.37 |
| place 3 / cancel 3 / signal 9 | 18 | 550.92 | 1,490.23 | -938.82 | -922.24 | 18 | 550.92 | 1,490.23 | -938.82 | 572.61 | -21.68 | 30.61 | 30.39 | 4.27 | -67.85 | 390,035 | 0.14 | 0.13 | 9.40 | 0.76 | 14,460 | 198.42 | 87.98 | 24.60 |