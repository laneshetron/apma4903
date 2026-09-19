# Quoter simulation, KXBTCD, 2026-09-17

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hourly: ttx <= 3 h, pessimistic queue | 321 | -302.19 | 629.94 | -916.99 | -943.25 | 321 | -302.19 | 629.94 | -916.99 | -261.83 | -40.36 | -0.94 | 3.79 | -4.44 | -24.45 | 169,579 | -0.18 | -0.19 | 47.72 | 0.52 | 13,797 | 18.46 | 0.00 | 7.85 |
|  ↳ vetoes: {'priority_fills': 6820, 'capital': 124895, 'greeks': 2139188} |

hourly: ttx <= 3 h, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 36,501 | 21% | -0.77 |
| join | partial | 1000-ms | 1000-ms | 24,022 | 14% | +0.22 |
| improve | partial | 1000-ms | 1000-ms | 18,280 | 11% | +0.38 |
| improve | sweep | 1000-ms | ? | 17,038 | 10% | +0.00 |
| join | partial | 0-5ms | ? | 15,032 | 9% | -0.21 |
| improve | partial | 200-1000ms | 200-1000ms | 9,951 | 6% | +0.51 |
| improve | partial | 0-5ms | ? | 8,509 | 5% | -0.11 |
| improve | sweep | 200-1000ms | ? | 6,585 | 4% | -0.11 |
| improve | sweep | 0-5ms | ? | 6,471 | 4% | -0.12 |
| join | partial | 200-1000ms | 200-1000ms | 3,731 | 2% | -0.26 |
| improve | partial | 50-200ms | 50-200ms | 3,422 | 2% | +0.19 |
| join | sweep | 1000-ms | 1000-ms | 2,845 | 2% | -1.48 |
| improve | sweep | 50-200ms | ? | 2,303 | 1% | +0.32 |
| join | sweep | 5-16ms | ? | 2,232 | 1% | -2.74 |
| join | partial | 1000-ms | ? | 1,760 | 1% | +0.14 |
| join | sweep | 200-1000ms | ? | 1,652 | 1% | +0.03 |
| join | sweep | 50-200ms | ? | 1,441 | 1% | -0.93 |
| improve | partial | 16-50ms | 16-50ms | 1,238 | 1% | -0.75 |
| improve | sweep | 16-50ms | ? | 1,188 | 1% | +0.03 |
| join | sweep | 16-50ms | ? | 1,069 | 1% | -0.44 |
| join | partial | 50-200ms | 50-200ms | 941 | 1% | -0.75 |
| join | sweep | 1000-ms | ? | 804 | 0% | +0.18 |
| join | partial | 200-1000ms | 1000-ms | 606 | 0% | -1.50 |
| improve | partial | 5-16ms | 5-16ms | 520 | 0% | +0.63 |
| **by kind/class** | | | | | | |
| join | sweep | — | — | 47,394 | 28% | -0.88 |
| join | partial | — | — | 46,686 | 27% | -0.02 |
| improve | partial | — | — | 42,119 | 25% | +0.27 |
| improve | sweep | — | — | 34,235 | 20% | -0.05 |