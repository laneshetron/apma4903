.PHONY: build run test test-go test-py generate specs parquet validate

build:
	go build -o bin/collector ./cmd/collector

run: build
	./bin/collector -config config.yaml

test: test-go test-py

test-go:
	go test -race ./...

test-py:
	cd python && uv run pytest -q

# Regenerate the REST client from specs/openapi.yaml.
generate:
	go generate ./...

# Refresh vendored Kalshi specs, then regenerate.
specs:
	curl -sSL https://docs.kalshi.com/openapi.yaml -o specs/openapi.yaml
	curl -sSL https://docs.kalshi.com/asyncapi.yaml -o specs/asyncapi.yaml
	$(MAKE) generate

# Usage: make parquet DAY=2026-09-14
parquet:
	cd python && uv run python -m kalshi_data.to_parquet $(DAY) --data-dir ../data

validate:
	cd python && uv run python -m kalshi_data.validate $(DAY) --data-dir ../data -v
