# Cluster-robust standard errors, permkt_offset3_KXNFLSPREAD_2026-09-20.parquet

Markets within a game share every information event, so the market-level t is inflated. `t_clustered` is CR1 clustered by game; `t_game` treats each game's total P&L as one observation.

| config | markets | games | $/market | total $ | t naive | **t clustered** | **t game** | $/game | games + | ICC | worst game |
|---|---|---|---|---|---|---|---|---|---|---|---|
| touch joiner, capital $10k | 281 | 16 | -1.47 | -412.5 | -5.17 | **-4.52** | **-3.65** | -25.78 | 3/16 | 0.00 | -85.2 |
| offset 2, prorata | 254 | 15 | +0.94 | +237.5 | +3.01 | **+1.89** | **+1.71** | +15.84 | 13/15 | 0.05 | -25.2 |
| offset 2, pessimistic | 249 | 13 | +0.60 | +148.7 | +2.16 | **+1.34** | **+1.27** | +11.44 | 6/13 | 0.06 | -19.8 |
| offset 5, pessimistic | 242 | 13 | +0.12 | +29.0 | +0.41 | **+0.32** | **+0.32** | +2.23 | 5/13 | 0.02 | -24.5 |
