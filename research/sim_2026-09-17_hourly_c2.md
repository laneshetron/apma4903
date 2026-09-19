# Quoter simulation, KXBTCD, 2026-09-17

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hourly: all strikes, ttx <= 3 h | 335 | -200.17 | 1,063.92 | -1,238.75 | -1,167.48 | 335 | -200.17 | 1,063.92 | -1,238.75 | -117.80 | -82.38 | -0.60 | 3.51 | -3.12 | -20.09 | 254,902 | -0.08 | -0.04 | 34.18 | 0.78 | 21,702 | 18.75 | 0.00 | 7.41 |
|  ↳ vetoes: {'priority_fills': 5739, 'capital': 119248, 'greeks': 2139188} |

hourly: all strikes, ttx <= 3 h: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 87,232 | 34% | +0.17 |
| join | partial | 0-5ms | ? | 36,114 | 14% | -0.26 |
| improve | partial | 1000-ms | 1000-ms | 23,074 | 9% | +0.41 |
| join | sweep | 0-5ms | ? | 22,419 | 9% | -0.87 |
| improve | sweep | 1000-ms | ? | 17,584 | 7% | -0.02 |
| improve | partial | 200-1000ms | 200-1000ms | 11,450 | 4% | +0.50 |
| improve | partial | 0-5ms | ? | 9,943 | 4% | +0.12 |
| join | partial | 200-1000ms | 200-1000ms | 8,164 | 3% | +0.13 |
| join | partial | 1000-ms | ? | 6,686 | 3% | +0.57 |
| improve | sweep | 200-1000ms | ? | 6,522 | 3% | -0.01 |
| improve | sweep | 0-5ms | ? | 5,485 | 2% | -0.19 |
| improve | partial | 50-200ms | 50-200ms | 3,825 | 1% | -0.05 |
| improve | sweep | 50-200ms | ? | 2,325 | 1% | +0.05 |
| join | sweep | 5-16ms | ? | 1,831 | 1% | -2.31 |
| join | sweep | 1000-ms | 1000-ms | 1,557 | 1% | -1.37 |
| join | sweep | 50-200ms | ? | 1,533 | 1% | -1.05 |
| join | partial | 50-200ms | 50-200ms | 1,460 | 1% | -1.27 |
| join | sweep | 200-1000ms | ? | 1,390 | 1% | +0.09 |
| join | partial | 200-1000ms | 1000-ms | 1,345 | 1% | -1.22 |
| improve | partial | 16-50ms | 16-50ms | 1,332 | 1% | -1.23 |
| improve | sweep | 16-50ms | ? | 1,266 | 0% | -0.26 |
| join | sweep | 16-50ms | ? | 885 | 0% | -0.93 |
| improve | partial | 5-16ms | 5-16ms | 659 | 0% | +0.94 |
| join | sweep | 1000-ms | ? | 567 | 0% | +0.40 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 141,763 | 55% | +0.04 |
| improve | partial | — | — | 50,480 | 20% | +0.31 |
| improve | sweep | — | — | 33,694 | 13% | -0.07 |
| join | sweep | — | — | 30,888 | 12% | -0.94 |