# Phase A: market-making viability read

Generated 2026-09-14 03:52 UTC over markets settled in the last 24h. Method: see `python/kalshi_data/research/phase_a.py`.

## KXBTC15M

- markets settled in window: 96 (96 with volume); volume 174,385,230 contracts = 174,385,230/day
- quoted spread (1-min closes): volume-weighted 0.74c, median 1.00c
- busiest hours (UTC): 01h 7%, 02h 7%, 03h 6%, 23h 6%
- share of volume in the last 3 minutes before expiry: 38%

- trade sample: 12 markets, 321,054 trades, 19,788,868 contracts; size median 9 / mean 62 / p90 131; taker bought YES 49% of volume

Maker markout, cents per contract, volume-weighted (positive = maker profits before spread):

| horizon | 10s | 30s | 60s | settlement |
|---|---|---|---|---|
| all trades |  +0.24 |  +0.30 |  +0.36 |  +0.30 |

By minutes-to-expiry at trade time (volume-weighted):

| min to expiry | 10s | 30s | 60s | settlement |
|---|---|---|---|---|
|  0 |  -0.06 |  -0.07 |   n/a  |  +0.02 |
|  1 |  +0.05 |  -0.06 |  -0.20 |  -0.26 |
|  2 |  +0.31 |  +0.73 |  +0.94 |  +1.82 |
|  3 |  +0.14 |  +0.02 |  +0.30 |  +0.71 |
|  4 |  +0.36 |  -0.11 |  -0.05 |  +1.33 |
|  5 |  +0.68 |  +1.12 |  +1.76 |  +3.66 |
|  6 |  -0.04 |  -0.18 |  +0.11 |  -0.22 |
|  7 |  +0.30 |  +0.86 |  +0.60 |  +2.13 |
|  8 |  -0.01 |  -0.08 |  -0.22 |  -4.80 |
|  9 |  +0.18 |  +0.49 |  +0.68 |  +0.46 |
| 10 |  +0.04 |  +0.00 |  -0.26 |  +1.61 |
| 11 |  +0.29 |  +0.51 |  +0.47 |  +2.47 |
| 12 |  +0.39 |  +0.23 |  +0.22 |  +2.47 |
| 13 |  +0.68 |  +0.89 |  +0.39 |  +0.49 |
| 14 |  +0.72 |  +0.64 |  +0.67 |  -4.39 |

Reading: markout already includes the captured half-spread (~0.37c). Implied adverse selection = half-spread - markout: 10s +0.13c, 30s +0.07c, 60s +0.01c, settlement +0.07c. Markout itself is the maker's gross P&L per contract for a touch fill unwound at that horizon.

Per-market (ticker, trades, contracts, markout 30s / settle):

- `KXBTC15M-26SEP130000-00` 33,058 trades, 1,891,274 contracts,  +0.01c /  +1.75c
- `KXBTC15M-26SEP130200-00` 26,576 trades, 1,524,131 contracts,  +1.40c /  +1.05c
- `KXBTC15M-26SEP130400-00` 22,285 trades, 1,267,398 contracts,  +0.35c /  +0.90c
- `KXBTC15M-26SEP130600-00` 15,160 trades, 864,006 contracts,  -0.16c /  +0.01c
- `KXBTC15M-26SEP130800-00` 21,110 trades, 997,021 contracts,  -0.82c /  -0.51c
- `KXBTC15M-26SEP131000-00` 17,545 trades, 1,185,229 contracts,  +0.37c /  +0.20c
- `KXBTC15M-26SEP131200-00` 26,753 trades, 1,544,959 contracts,  +0.16c /  +0.83c
- `KXBTC15M-26SEP131400-00` 23,371 trades, 1,563,297 contracts,  +0.25c /  +0.53c
- `KXBTC15M-26SEP131600-00` 26,948 trades, 1,502,081 contracts,  +0.01c /  -1.12c
- `KXBTC15M-26SEP131800-00` 27,584 trades, 1,824,634 contracts,  +0.21c /  +1.34c
- `KXBTC15M-26SEP132000-00` 40,616 trades, 2,462,112 contracts,  +0.75c /  +0.05c
- `KXBTC15M-26SEP132200-00` 40,048 trades, 3,162,726 contracts,  +0.31c /  -0.91c

## KXETH15M

- markets settled in window: 96 (96 with volume); volume 10,557,456 contracts = 10,557,456/day
- quoted spread (1-min closes): volume-weighted 1.06c, median 1.00c
- busiest hours (UTC): 02h 6%, 03h 5%, 16h 5%, 23h 5%
- share of volume in the last 3 minutes before expiry: 47%

- trade sample: 12 markets, 52,691 trades, 1,363,117 contracts; size median 10 / mean 26 / p90 48; taker bought YES 49% of volume

Maker markout, cents per contract, volume-weighted (positive = maker profits before spread):

| horizon | 10s | 30s | 60s | settlement |
|---|---|---|---|---|
| all trades |  +0.28 |  +0.17 |  +0.51 |  +0.17 |

By minutes-to-expiry at trade time (volume-weighted):

| min to expiry | 10s | 30s | 60s | settlement |
|---|---|---|---|---|
|  0 |  -0.16 |  +0.45 |   n/a  |  +0.06 |
|  1 |  +0.18 |  -0.79 |  +0.05 |  +0.45 |
|  2 |  +0.66 |  +1.04 |  +3.30 |  +3.67 |
|  3 |  +0.50 |  +0.54 |  +0.68 |  +1.88 |
|  4 |  +0.80 |  -0.06 |  -0.39 |  +3.50 |
|  5 |  +0.26 |  +0.17 |  +0.19 |  -1.69 |
|  6 |  +0.07 |  +0.61 |  +0.04 |  +0.65 |
|  7 |  +0.88 |  +1.81 |  +1.22 |  -0.69 |
|  8 |  -0.62 |  -0.21 |  -1.15 |  +1.08 |
|  9 |  +0.53 |  +0.05 |  +1.08 |  +1.12 |
| 10 |  +0.45 |  +0.58 |  +0.89 |  -1.65 |
| 11 |  +0.31 |  -0.69 |  -0.85 |  -6.97 |
| 12 |  +1.03 |  +0.35 |  +0.53 |  -0.69 |
| 13 |  -1.06 |  -1.42 |  -2.29 |  -2.27 |
| 14 |  +1.06 |  +0.46 |  +0.42 |  -4.78 |

Reading: markout already includes the captured half-spread (~0.53c). Implied adverse selection = half-spread - markout: 10s +0.25c, 30s +0.36c, 60s +0.02c, settlement +0.36c. Markout itself is the maker's gross P&L per contract for a touch fill unwound at that horizon.

Per-market (ticker, trades, contracts, markout 30s / settle):

- `KXETH15M-26SEP130000-00` 5,530 trades, 141,628 contracts,  -2.71c /  -2.88c
- `KXETH15M-26SEP130200-00` 4,424 trades, 127,015 contracts,  -0.12c /  +4.65c
- `KXETH15M-26SEP130400-00` 3,757 trades, 84,253 contracts,  +0.04c /  -2.18c
- `KXETH15M-26SEP130600-00` 2,977 trades, 65,853 contracts,  +0.13c /  -2.91c
- `KXETH15M-26SEP130800-00` 3,020 trades, 74,004 contracts,  -0.83c /  -2.07c
- `KXETH15M-26SEP131000-00` 3,473 trades, 81,107 contracts,  +0.44c /  +1.99c
- `KXETH15M-26SEP131200-00` 6,074 trades, 173,006 contracts,  +2.04c /  +6.11c
- `KXETH15M-26SEP131400-00` 4,906 trades, 139,866 contracts,  -0.04c /  -4.21c
- `KXETH15M-26SEP131600-00` 5,071 trades, 148,162 contracts,  +1.83c /  +1.62c
- `KXETH15M-26SEP131800-00` 4,399 trades, 112,847 contracts,  -0.13c /  -1.05c
- `KXETH15M-26SEP132000-00` 4,768 trades, 108,054 contracts,  -0.62c /  -0.81c
- `KXETH15M-26SEP132200-00` 4,292 trades, 107,323 contracts,  +1.04c /  -0.88c

## KXBTCD

- markets settled in window: 4404 (522 with volume); volume 31,931,931 contracts = 31,931,931/day
- quoted spread (1-min closes): volume-weighted 1.09c, median 1.00c
- busiest hours (UTC): 02h 9%, 22h 7%, 00h 7%, 01h 7%
- share of volume in the last 3 minutes before expiry: 8%

- trade sample: 12 markets, 15,641 trades, 1,282,763 contracts; size median 20 / mean 82 / p90 213; taker bought YES 51% of volume

Maker markout, cents per contract, volume-weighted (positive = maker profits before spread):

| horizon | 10s | 30s | 60s | settlement |
|---|---|---|---|---|
| all trades |  +0.32 |  -0.08 |  -0.39 |  +1.19 |

By minutes-to-expiry at trade time (volume-weighted):

| min to expiry | 10s | 30s | 60s | settlement |
|---|---|---|---|---|
|  0 |  +0.22 |  +0.13 |   n/a  |  +0.35 |
|  1 |  +3.59 |  -3.61 |  -7.26 |  -5.38 |
|  2 |  +3.25 |  -0.44 |  -0.28 |  +9.89 |
|  3 |  +1.56 |  +1.31 |  +1.83 |  +0.83 |
|  4 |  +0.92 |  +0.79 |  +0.50 |  -4.99 |
|  5 |  +0.29 |  +0.26 |  +1.11 | +16.31 |
|  6 |  +0.27 |  +0.20 |  -0.59 | +15.69 |
|  7 |  +0.92 |  +3.12 |  -6.32 |  +7.19 |
|  8 |  +0.64 |  +0.49 |  +0.54 |  -2.80 |
|  9 |  +0.55 |  +0.29 |  +0.03 |  +2.39 |
| 10 |  +0.31 |  +0.92 |  +1.71 |  +4.24 |
| 11 |  -0.47 |  +0.75 |  +2.69 | +17.82 |
| 12 |  +1.19 |  +0.85 |  +1.43 |  -1.91 |
| 13 |  -3.68 |  -1.14 |  -2.34 |  -6.36 |
| 14 |  +0.27 |  -0.51 |  -0.80 |  +0.56 |
| 15 |  -0.07 |  -0.61 |  -0.65 | +16.29 |
| 16 |  +0.75 |  +1.07 |  +1.06 |  +7.50 |
| 17 |  -0.31 |  -0.12 |  -0.29 | +13.71 |
| 18 |  +0.53 |  +0.42 |  +0.72 |  -2.46 |
| 19 |  +0.33 |  +0.05 |  +0.12 |  +5.10 |
| 20 |  -0.14 |  +0.74 |  +1.49 | +15.40 |

Reading: markout already includes the captured half-spread (~0.54c). Implied adverse selection = half-spread - markout: 10s +0.23c, 30s +0.62c, 60s +0.93c, settlement -0.65c. Markout itself is the maker's gross P&L per contract for a touch fill unwound at that horizon.

Per-market (ticker, trades, contracts, markout 30s / settle):

- `KXBTCD-26SEP1300-T77199.99` 7,369 trades, 604,050 contracts,  -0.52c /  +5.29c
- `KXBTCD-26SEP1302-T76799.99` 6 trades, 515 contracts,   n/a c /  -1.00c
- `KXBTCD-26SEP1304-T74699.99` 2 trades, 48 contracts,   n/a c /  +1.00c
- `KXBTCD-26SEP1306-T79999.99` 1 trades, 94 contracts,   n/a c /  +1.00c
- `KXBTCD-26SEP1309-T76999.99` 321 trades, 32,500 contracts,  +0.68c /  +2.49c
- `KXBTCD-26SEP1311-T76699.99` 392 trades, 44,548 contracts,  +0.51c /  -0.70c
- `KXBTCD-26SEP1313-T76799.99` 89 trades, 9,020 contracts,  +0.09c /  +0.07c
- `KXBTCD-26SEP1316-T77299.99` 4,177 trades, 309,552 contracts,  +0.06c /  -2.41c
- `KXBTCD-26SEP1317-T74499.99` 3 trades, 118 contracts,   n/a c /  +1.00c
- `KXBTCD-26SEP1319-T76999.99` 2,328 trades, 192,044 contracts,  +0.70c /  -4.15c
- `KXBTCD-26SEP1320-T77799.99` 10 trades, 431 contracts,   n/a c /  +1.31c
- `KXBTCD-26SEP1322-T76499.99` 943 trades, 89,844 contracts,  +0.21c /  -1.95c
