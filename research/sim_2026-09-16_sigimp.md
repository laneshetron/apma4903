# Quoter simulation, KXBTC15M, 2026-09-16

Touch quoter, 100 contracts/side unless noted, max position 500, quoting stops 2 min before expiry, inventory marked at mid. No market impact. See `python/kalshi_data/research/sim.py`.

| config | markets | pnl_$ | spread_$ | inventory_$ | adverse_10s_$ | test_markets | test_pnl_$ | test_spread_$ | test_inventory_$ | realized_$ | unrealized_$ | pnl_per_market_$ | pnl_sd_$ | t_stat | worst_$ | contracts | pnl_c_per_contract | fill_markout_30s_c | improved_fill_% | fill_share_% | fills | avg_max_pos | end_pos_abs | flatten_cost_$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline (signal cancel $2/1s) | 25 | -10.58 | 179.77 | -187.08 | -195.58 | 25 | -10.58 | 179.77 | -187.08 | -9.09 | -1.49 | -0.42 | 4.09 | -0.52 | -11.70 | 59,759 | -0.02 | -0.03 | 19.40 | 0.08 | 5,676 | 19.78 | 0.00 | 3.76 |
|  ↳ vetoes: {'join': 405823, 'priority_fills': 1289, 'greeks': 3378962} |
| signal improve $2/1s, hold 2 s | 25 | -57.68 | 149.10 | -203.52 | -202.94 | 25 | -57.68 | 149.10 | -203.52 | -55.83 | -1.85 | -2.31 | 4.33 | -2.66 | -12.08 | 53,183 | -0.11 | -0.08 | 20.37 | 0.07 | 5,090 | 19.90 | 0.00 | 3.86 |
|  ↳ vetoes: {'join': 598118, 'signal_improve': 9150, 'sig_held': 140490, 'post_only_cross': 7765, 'priority_fills': 1387, 'greeks': 3378962} |
| signal improve $2/1s, hold 0.5 s | 25 | -57.39 | 149.25 | -203.52 | -203.04 | 25 | -57.39 | 149.25 | -203.52 | -56.54 | -0.85 | -2.30 | 4.33 | -2.65 | -12.08 | 53,193 | -0.11 | -0.08 | 20.33 | 0.07 | 5,090 | 19.90 | 0.00 | 3.72 |
|  ↳ vetoes: {'join': 598220, 'signal_improve': 9151, 'sig_held': 140183, 'post_only_cross': 7766, 'priority_fills': 1387, 'greeks': 3378962} |
| signal improve $2/1s, hold 5 s | 25 | -57.68 | 149.10 | -203.52 | -202.94 | 25 | -57.68 | 149.10 | -203.52 | -55.83 | -1.85 | -2.31 | 4.33 | -2.66 | -12.08 | 53,183 | -0.11 | -0.08 | 20.37 | 0.07 | 5,090 | 19.90 | 0.00 | 3.86 |
|  ↳ vetoes: {'join': 598118, 'signal_improve': 9150, 'sig_held': 140490, 'post_only_cross': 7765, 'priority_fills': 1387, 'greeks': 3378962} |
| signal improve $3/1s, hold 2 s | 25 | -61.44 | 164.83 | -222.62 | -227.21 | 25 | -61.44 | 164.83 | -222.62 | -55.06 | -6.38 | -2.46 | 4.85 | -2.53 | -13.33 | 57,554 | -0.11 | -0.09 | 19.99 | 0.08 | 5,517 | 19.92 | 0.80 | 3.90 |
|  ↳ vetoes: {'join': 642324, 'signal_improve': 8617, 'sig_held': 134982, 'post_only_cross': 7350, 'priority_fills': 1443, 'greeks': 3378962} |
| signal improve $5/1s, hold 2 s | 25 | -65.26 | 190.78 | -252.58 | -255.60 | 25 | -65.26 | 190.78 | -252.58 | -58.50 | -6.75 | -2.61 | 4.20 | -3.11 | -12.15 | 65,220 | -0.10 | -0.05 | 19.13 | 0.09 | 6,478 | 19.82 | 0.80 | 3.61 |
|  ↳ vetoes: {'join': 682284, 'signal_improve': 7667, 'sig_held': 120759, 'post_only_cross': 6541, 'priority_fills': 1628, 'greeks': 3378962} |
| signal improve $2/1s, hold 2 s, no join gate | 25 | -58.32 | 160.10 | -215.30 | -204.70 | 25 | -58.32 | 160.10 | -215.30 | -61.59 | 3.27 | -2.33 | 3.88 | -3.01 | -9.84 | 57,358 | -0.10 | -0.11 | 16.03 | 0.08 | 5,514 | 19.90 | 0.00 | 3.72 |
|  ↳ vetoes: {'signal_improve': 9006, 'sig_held': 136280, 'post_only_cross': 7619, 'priority_fills': 1512, 'greeks': 3378962} |
| signal improve $2/1s, hold 2 s, pessimistic queue | 25 | -76.13 | 71.55 | -144.89 | -167.73 | 25 | -76.13 | 71.55 | -144.89 | -62.59 | -13.54 | -3.05 | 3.61 | -4.22 | -11.93 | 36,290 | -0.21 | -0.20 | 27.07 | 0.05 | 3,343 | 19.89 | 0.00 | 3.39 |
|  ↳ vetoes: {'signal_improve': 9211, 'sig_held': 140597, 'post_only_cross': 7853, 'priority_fills': 1772, 'join': 565115, 'greeks': 3378962} |
| signal improve $2/1s, hold 2 s, FIX-like 5/3/9 | 25 | -50.13 | 156.38 | -203.35 | -203.07 | 25 | -50.13 | 156.38 | -203.35 | -52.18 | 2.06 | -2.01 | 4.95 | -2.02 | -12.26 | 54,992 | -0.09 | -0.07 | 21.15 | 0.08 | 5,299 | 19.93 | 0.00 | 3.66 |
|  ↳ vetoes: {'signal_improve': 9165, 'sig_held': 107698, 'post_only_cross': 8268, 'join': 598232, 'priority_fills': 1331, 'greeks': 3378962} |
| signal improve $2/1s, hold 2 s, size 50 | 25 | -108.93 | 341.66 | -443.91 | -465.01 | 25 | -108.93 | 341.66 | -443.91 | -70.51 | -38.43 | -4.36 | 10.80 | -2.02 | -35.78 | 119,977 | -0.09 | -0.10 | 19.15 | 0.17 | 6,172 | 49.59 | 0.00 | 8.11 |
|  ↳ vetoes: {'join': 594908, 'signal_improve': 9135, 'sig_held': 140035, 'post_only_cross': 7748, 'priority_fills': 1567, 'greeks': 3378962} |