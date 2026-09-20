# Quoter simulation, KXEPLSCORE, 2026-09-19

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 4 | 0.10 | 0.20 | -0.10 | 0.00 | 4 | 0.10 | 0.20 | -0.10 | 0.00 | 0.10 | 0.03 | 0.08 | 0.60 | -0.10 | 80 | 0.13 | 0.25 | 50.00 | 2.03 | 4 | 20.00 | 20.00 | 0.00 |
|  ↳ vetoes: {'priority_fills': 2} |
| touch joiner, size 5 | 4 | 0.03 | 0.05 | -0.03 | 0.00 | 4 | 0.03 | 0.05 | -0.03 | 0.00 | 0.03 | 0.01 | 0.02 | 0.60 | -0.03 | 20 | 0.13 | 0.25 | 50.00 | 0.51 | 4 | 5.00 | 5.00 | 0.00 |
|  ↳ vetoes: {'priority_fills': 2} |
| touch joiner, depth >= 50 | 4 | 0.10 | 0.20 | -0.10 | 0.00 | 4 | 0.10 | 0.20 | -0.10 | 0.00 | 0.10 | 0.03 | 0.08 | 0.60 | -0.10 | 80 | 0.13 | 0.25 | 50.00 | 2.03 | 4 | 20.00 | 20.00 | 0.00 |
|  ↳ vetoes: {'priority_fills': 2, 'thin': 356} |
| join only, never improve | 2 | 0.20 | 0.20 | 0.00 | 0.00 | 2 | 0.20 | 0.20 | 0.00 | 0.00 | 0.20 | 0.10 | 0.00 | nan | 0.10 | 40 | 0.50 | 0.50 | 0.00 | 2.40 | 2 | 20.00 | 20.00 | 0.00 |
| touch joiner, pessimistic queue | 2 | -0.10 | 0.00 | -0.10 | 0.00 | 2 | -0.10 | 0.00 | -0.10 | 0.00 | -0.10 | -0.05 | 0.05 | -1.41 | -0.10 | 40 | -0.25 | 0.00 | 100.00 | 1.77 | 2 | 20.00 | 20.00 | 0.00 |
|  ↳ vetoes: {'priority_fills': 2} |
| touch joiner, carry (no flatten) | 4 | 0.10 | 0.20 | -0.10 | 0.00 | 4 | 0.10 | 0.20 | -0.10 | 0.00 | 0.10 | 0.03 | 0.08 | 0.60 | -0.10 | 80 | 0.13 | 0.25 | 50.00 | 2.03 | 4 | 20.00 | 20.00 | 0.00 |
|  ↳ vetoes: {'priority_fills': 2} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 40 | 50% | +0.00 |
| join | partial | 1000-ms | ? | 40 | 50% | +0.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 40 | 50% | +0.00 |
| join | partial | — | — | 40 | 50% | +0.50 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 10 | 50% | +0.00 |
| join | partial | 1000-ms | ? | 10 | 50% | +0.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 10 | 50% | +0.00 |
| join | partial | — | — | 10 | 50% | +0.50 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 40 | 50% | +0.00 |
| join | partial | 1000-ms | ? | 40 | 50% | +0.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 40 | 50% | +0.00 |
| join | partial | — | — | 40 | 50% | +0.50 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 1000-ms | ? | 40 | 100% | +0.50 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 40 | 100% | +0.50 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 40 | 100% | +0.00 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 40 | 100% | +0.00 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| improve | sweep | 1000-ms | ? | 40 | 50% | +0.00 |
| join | partial | 1000-ms | ? | 40 | 50% | +0.50 |
| **by kind/class** | | | | | | |
| improve | sweep | — | — | 40 | 50% | +0.00 |
| join | partial | — | — | 40 | 50% | +0.50 |