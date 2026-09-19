# Quoter simulation, KXBTCD, 2026-09-17

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hourly: ttx <= 3 h, no gates | 75 | -194.38 | 410.39 | -600.13 | -985.42 | 75 | -194.38 | 410.39 | -600.13 | -119.05 | -75.33 | -2.59 | 5.31 | -4.22 | -19.72 | 102,543 | -0.19 | -0.16 | 30.61 | 0.45 | 13,951 | 15.56 | 0.00 | 4.54 |
|  ↳ vetoes: {'priority_fills': 4679, 'capital': 9023748} |

hourly: ttx <= 3 h, no gates: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | 1000-ms | 63,795 | 37% | +0.10 |
| join | partial | 0-5ms | ? | 22,358 | 13% | -0.55 |
| improve | partial | 1000-ms | 1000-ms | 16,098 | 9% | +0.29 |
| join | sweep | 0-5ms | ? | 11,001 | 6% | -0.96 |
| improve | sweep | 1000-ms | ? | 9,905 | 6% | -0.13 |
| improve | partial | 200-1000ms | 200-1000ms | 6,817 | 4% | -0.27 |
| improve | partial | 0-5ms | ? | 6,786 | 4% | -0.11 |
| join | partial | 1000-ms | ? | 6,275 | 4% | +0.32 |
| join | partial | 200-1000ms | 200-1000ms | 4,398 | 3% | +0.22 |
| improve | sweep | 200-1000ms | ? | 4,331 | 3% | -0.61 |
| improve | sweep | 0-5ms | ? | 3,384 | 2% | -0.79 |
| improve | partial | 50-200ms | 50-200ms | 2,084 | 1% | +0.16 |
| improve | sweep | 50-200ms | ? | 1,796 | 1% | +0.73 |
| join | partial | 200-1000ms | 1000-ms | 1,461 | 1% | -1.56 |
| join | sweep | 5-16ms | ? | 1,311 | 1% | -2.93 |
| join | sweep | 50-200ms | ? | 1,103 | 1% | -1.18 |
| join | sweep | 200-1000ms | ? | 966 | 1% | -0.08 |
| join | partial | 50-200ms | 50-200ms | 957 | 1% | -0.33 |
| improve | partial | 16-50ms | 16-50ms | 902 | 1% | -0.44 |
| join | sweep | 1000-ms | 1000-ms | 820 | 0% | -2.99 |
| improve | sweep | 16-50ms | ? | 771 | 0% | +0.19 |
| join | sweep | 16-50ms | ? | 673 | 0% | +0.87 |
| join | sweep | 1000-ms | ? | 530 | 0% | +0.01 |
| improve | partial | 5-16ms | 5-16ms | 451 | 0% | +1.26 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 100,073 | 59% | -0.07 |
| improve | partial | — | — | 33,325 | 20% | +0.11 |
| improve | sweep | — | — | 20,506 | 12% | -0.27 |
| join | sweep | — | — | 16,913 | 10% | -1.15 |