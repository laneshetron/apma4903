# kalshi

Market-data collection and real-time order-book reconstruction for
[Kalshi](https://kalshi.com), as the foundation for market making.

- **Go** (`cmd/collector`) — the hot path: authenticated WebSocket feed,
  per-subscription sequence tracking with gap recovery, in-memory order books,
  raw message recording, reconnect.
- **Python** (`python/`) — offline: raw log → Parquet, a reference order-book
  replay, and a validator that checks reconstructed books against REST
  snapshots.

## Setup

1. Create an API key at kalshi.com → Settings → API Keys. Save the downloaded
   private-key PEM outside the repo or in the repo root (`*.pem` is gitignored).
2. `cp .env.example .env` and fill in `KALSHI_API_KEY_ID` and
   `KALSHI_PRIVATE_KEY_PATH`.
3. `cp config.example.yaml config.yaml` and set the markets to follow —
   explicit `tickers` and/or `series` (open markets in a series are listed
   via REST and kept in sync every `refresh_interval`).
4. `make run`

```
$ curl -s localhost:8080/status | jq .feed
$ curl -s localhost:8080/book/KXBTC15M-26SEP131900-00?depth=5
```

Spot feeds (the BRTI/ETHUSD_RTI constituents) are recorded by a second
binary, `make run-spot` (status on `localhost:8081/status`), into
`data/spot/<venue>/`. Python tooling: `cd python && uv sync`.

## Data

Every WebSocket frame is appended verbatim to
`data/raw/YYYY-MM-DD/HH.jsonl.gz` (UTC) as
`{"rx_ns": <receive time, unix ns>, "raw": <message>}`. Collector-side
events (`connect`, `disconnect`, `subscribed`, `gap`, `resync`,
`markets_sync`, `rest_snapshot`) are written into the same stream with
`"type": "_local"`, so a replay knows exactly when a book is invalid.

```
make parquet DAY=2026-09-14     # -> data/parquet/<table>/date=2026-09-14/
make validate DAY=2026-09-14    # replay + compare to recorded REST snapshots
```

Parquet tables: `orderbook_snapshot_levels`, `orderbook_delta`, `trade`,
`local_event`. Prices are `int32` in 1/10000 dollar, quantities `int64` in
1/100 contract — the same integer units the Go and Python books use.

## Order-book semantics

Kalshi books are bids-only on both sides: a YES bid at price *p* is the same
resting order as a NO ask at *1 − p*. `orderbook_snapshot` replaces a
market's book; `orderbook_delta` is a *relative* quantity change at one
price level. `seq` is monotonic per subscription (`sid`), not per market: a
gap invalidates every market on that sid, and the collector requests fresh
snapshots via `update_subscription {action: get_snapshot}`. A delta that
would drive a level negative is treated the same way.

Both implementations are tested against the shared fixtures in
`testdata/book_cases.json`.

## Layout

```
cmd/collector        CLI entry point
internal/kalshi      auth (RSA-PSS), WebSocket conn, REST wrappers, message types
internal/kalshi/gen  REST client generated from specs/openapi.yaml (go generate)
internal/book        order book
internal/feed        subscriptions, seq/gap handling, resync, reconnect, recording
internal/recorder    hourly gzipped JSONL writer
internal/status      HTTP: /status, /markets, /book/{ticker}
internal/spot        public spot-exchange WebSocket recorder (cmd/spot)
specs/               vendored Kalshi OpenAPI + AsyncAPI specs (make specs)
python/kalshi_data   raw reader, replay, to_parquet, validate, spot normalizer
python/kalshi_data/research  phase_a (REST history), markouts, latency
testdata/            fixtures shared by Go and Python tests; spot/ has sample venue frames
research/            findings and generated reports
```

## Development

```
make test        # go test -race + pytest
make generate    # regenerate REST client after editing specs/openapi.yaml
```
