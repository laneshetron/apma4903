# Quoter simulation, KXBTCD, 2026-09-17

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hourly: all strikes, ttx <= 1 h | 329 | -197.17 | 1,065.46 | -1,239.31 | -1,167.85 | 329 | -197.17 | 1,065.46 | -1,239.31 | -121.18 | -75.99 | -0.60 | 3.44 | -3.16 | -19.69 | 255,029 | -0.08 | -0.04 | 34.14 | 0.79 | 21,578 | 18.89 | 0.00 | 7.47 |
|  ↳ vetoes: {'priority_fills': 5671, 'capital': 52754, 'greeks': 2139188} |

hourly: all strikes, ttx <= 1 h: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 87,380 | 34% | +0.18 |
| join | partial | 0-5ms | ? | 36,370 | 14% | -0.24 |
| improve | partial | 1000-ms | 1000-ms | 23,009 | 9% | +0.40 |
| join | sweep | 0-5ms | ? | 22,210 | 9% | -0.87 |
| improve | sweep | 1000-ms | ? | 17,482 | 7% | -0.03 |
| improve | partial | 200-1000ms | 200-1000ms | 11,431 | 4% | +0.48 |
| improve | partial | 0-5ms | ? | 9,945 | 4% | +0.13 |
| join | partial | 200-1000ms | 200-1000ms | 8,195 | 3% | +0.13 |
| join | partial | 1000-ms | ? | 6,875 | 3% | +0.58 |
| improve | sweep | 200-1000ms | ? | 6,443 | 3% | -0.08 |
| improve | sweep | 0-5ms | ? | 5,617 | 2% | -0.19 |
| improve | partial | 50-200ms | 50-200ms | 3,774 | 1% | -0.15 |
| improve | sweep | 50-200ms | ? | 2,362 | 1% | +0.05 |
| join | sweep | 5-16ms | ? | 1,838 | 1% | -2.37 |
| join | sweep | 1000-ms | 1000-ms | 1,546 | 1% | -1.36 |
| join | sweep | 50-200ms | ? | 1,536 | 1% | -1.10 |
| join | partial | 50-200ms | 50-200ms | 1,481 | 1% | -1.23 |
| join | sweep | 200-1000ms | ? | 1,379 | 1% | -0.01 |
| join | partial | 200-1000ms | 1000-ms | 1,329 | 1% | -1.23 |
| improve | partial | 16-50ms | 16-50ms | 1,322 | 1% | -1.14 |
| improve | sweep | 16-50ms | ? | 1,194 | 0% | -0.24 |
| join | sweep | 16-50ms | ? | 884 | 0% | -0.93 |
| improve | partial | 5-16ms | 5-16ms | 640 | 0% | +0.98 |
| join | sweep | 1000-ms | ? | 544 | 0% | +0.40 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 142,406 | 55% | +0.05 |
| improve | partial | — | — | 50,318 | 20% | +0.29 |
| improve | sweep | — | — | 33,606 | 13% | -0.08 |
| join | sweep | — | — | 30,623 | 12% | -0.95 |