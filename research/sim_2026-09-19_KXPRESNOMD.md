# Quoter simulation, KXPRESNOMD, 2026-09-19

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner | 8 | 0.12 | 0.15 | -0.07 | -0.10 | 8 | 0.12 | 0.15 | -0.07 | 0.03 | 0.09 | 0.01 | 0.02 | 2.19 | 0.00 | 200 | 0.06 | 0.03 | 0.00 | 0.21 | 15 | 20.00 | 20.00 | 0.00 |
|  ↳ vetoes: {'priority_fills': 7, 'capital': 144} |
| touch joiner, size 5 | 8 | 0.03 | 0.04 | -0.02 | -0.03 | 8 | 0.03 | 0.04 | -0.02 | 0.01 | 0.02 | 0.00 | 0.00 | 2.19 | 0.00 | 50 | 0.06 | 0.03 | 0.00 | 0.05 | 14 | 5.00 | 5.00 | 0.00 |
|  ↳ vetoes: {'priority_fills': 6} |
| touch joiner, depth >= 50 | 6 | 0.08 | 0.11 | -0.03 | -0.06 | 6 | 0.08 | 0.11 | -0.03 | 0.02 | 0.06 | 0.01 | 0.02 | 1.92 | 0.00 | 160 | 0.05 | 0.02 | 0.00 | 0.19 | 12 | 20.00 | 20.00 | 0.00 |
|  ↳ vetoes: {'thin': 4236, 'priority_fills': 5, 'capital': 62} |
| join only, never improve | 8 | 0.12 | 0.15 | -0.07 | -0.10 | 8 | 0.12 | 0.15 | -0.07 | 0.03 | 0.09 | 0.01 | 0.02 | 2.19 | 0.00 | 200 | 0.06 | 0.03 | 0.00 | 0.21 | 15 | 20.00 | 20.00 | 0.00 |
|  ↳ vetoes: {'priority_fills': 7, 'capital': 144} |
| touch joiner, pessimistic queue | 7 | 0.11 | 0.14 | -0.07 | -0.10 | 7 | 0.11 | 0.14 | -0.07 | 0.03 | 0.08 | 0.02 | 0.02 | 2.02 | 0.00 | 180 | 0.06 | 0.03 | 0.00 | 0.20 | 13 | 20.00 | 20.00 | 0.00 |
|  ↳ vetoes: {'priority_fills': 8, 'capital': 144} |
| touch joiner, carry (no flatten) | 8 | 0.12 | 0.15 | -0.07 | -0.10 | 8 | 0.12 | 0.15 | -0.07 | 0.03 | 0.09 | 0.01 | 0.02 | 2.19 | 0.00 | 200 | 0.06 | 0.03 | 0.00 | 0.21 | 15 | 20.00 | 20.00 | 0.00 |
|  ↳ vetoes: {'priority_fills': 7, 'capital': 144} |

touch joiner: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 96 | 48% | +0.01 |
| join | partial | 0-5ms | ? | 64 | 32% | +0.08 |
| join | partial | 1000-ms | ? | 40 | 20% | +0.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 104 | 52% | +0.05 |
| join | sweep | — | — | 96 | 48% | +0.01 |

touch joiner, size 5: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 21 | 42% | +0.01 |
| join | partial | 0-5ms | ? | 19 | 38% | +0.07 |
| join | partial | 1000-ms | ? | 10 | 20% | +0.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 29 | 58% | +0.04 |
| join | sweep | — | — | 21 | 42% | +0.01 |

touch joiner, depth >= 50: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | partial | 0-5ms | ? | 61 | 38% | +0.05 |
| join | sweep | 0-5ms | ? | 59 | 37% | +0.00 |
| join | partial | 1000-ms | ? | 40 | 25% | +0.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 101 | 63% | +0.03 |
| join | sweep | — | — | 59 | 37% | +0.00 |

join only, never improve: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 96 | 48% | +0.01 |
| join | partial | 0-5ms | ? | 64 | 32% | +0.08 |
| join | partial | 1000-ms | ? | 40 | 20% | +0.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 104 | 52% | +0.05 |
| join | sweep | — | — | 96 | 48% | +0.01 |

touch joiner, pessimistic queue: our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 99 | 55% | +0.01 |
| join | partial | 0-5ms | ? | 41 | 23% | +0.10 |
| join | sweep | 1000-ms | ? | 20 | 11% | -0.05 |
| join | partial | 1000-ms | ? | 20 | 11% | +0.05 |
| **by kind/class** | | | | | | |
| join | sweep | — | — | 119 | 66% | +0.00 |
| join | partial | — | — | 61 | 34% | +0.08 |

touch joiner, carry (no flatten): our fills by kind / sweep / age of the touch price / age of the level (mo30 ¢, share of contracts)

| kind | class | touch age | level age | contracts | share | mo30 ¢ |
|---|---|---|---|---|---|---|
| join | sweep | 0-5ms | ? | 96 | 48% | +0.01 |
| join | partial | 0-5ms | ? | 64 | 32% | +0.08 |
| join | partial | 1000-ms | ? | 40 | 20% | +0.00 |
| **by kind/class** | | | | | | |
| join | partial | — | — | 104 | 52% | +0.05 |
| join | sweep | — | — | 96 | 48% | +0.01 |