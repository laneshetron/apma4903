package kalshi

import (
	"context"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/laneshetron/kalshi/internal/kalshi/gen"
)

// REST is a thin, signed wrapper over the generated client for the handful
// of endpoints the collector needs.
type REST struct {
	c *gen.ClientWithResponses
}

// NewREST builds a signed REST client for env.
func NewREST(env Env, signer *Signer, httpClient *http.Client) (*REST, error) {
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 15 * time.Second}
	}
	c, err := gen.NewClientWithResponses(env.RESTBase(),
		gen.WithHTTPClient(httpClient),
		gen.WithRequestEditorFn(func(_ context.Context, req *http.Request) error {
			return signer.SignRequest(req)
		}),
	)
	if err != nil {
		return nil, err
	}
	return &REST{c: c}, nil
}

// Raw exposes the generated client for endpoints without a wrapper.
func (r *REST) Raw() *gen.ClientWithResponses { return r.c }

// Orderbook is a REST orderbook snapshot in wire format (bids only, both sides).
type Orderbook struct {
	Yes []PriceLevel
	No  []PriceLevel
}

// GetOrderbook fetches the full book for ticker (depth 0 = all levels).
func (r *REST) GetOrderbook(ctx context.Context, ticker string) (*Orderbook, error) {
	resp, err := r.c.GetMarketOrderbookWithResponse(ctx, ticker, &gen.GetMarketOrderbookParams{})
	if err != nil {
		return nil, fmt.Errorf("kalshi: get orderbook %s: %w", ticker, err)
	}
	if resp.JSON200 == nil {
		return nil, httpError("get orderbook "+ticker, resp.HTTPResponse, resp.Body)
	}
	fp := resp.JSON200.OrderbookFp
	ob := &Orderbook{Yes: toLevels(fp.YesDollars), No: toLevels(fp.NoDollars)}
	return ob, nil
}

func toLevels(in []gen.PriceLevelDollarsCountFp) []PriceLevel {
	out := make([]PriceLevel, 0, len(in))
	for _, l := range in {
		if len(l) >= 2 {
			out = append(out, PriceLevel{l[0], l[1]})
		}
	}
	return out
}

// ListOpenMarkets returns every open market in a series, following pagination.
func (r *REST) ListOpenMarkets(ctx context.Context, series string) ([]gen.Market, error) {
	var out []gen.Market
	limit := gen.MarketLimitQuery(1000)
	status := gen.GetMarketsParamsStatusOpen
	params := &gen.GetMarketsParams{SeriesTicker: series, Status: &status, Limit: &limit}
	for {
		resp, err := r.c.GetMarketsWithResponse(ctx, params)
		if err != nil {
			return nil, fmt.Errorf("kalshi: list markets %s: %w", series, err)
		}
		if resp.JSON200 == nil {
			return nil, httpError("list markets "+series, resp.HTTPResponse, resp.Body)
		}
		out = append(out, resp.JSON200.Markets...)
		if resp.JSON200.Cursor == "" {
			return out, nil
		}
		params.Cursor = resp.JSON200.Cursor
	}
}

// ListActiveMarkets returns every open market on the exchange with 24 h volume
// >= minVolume contracts, via the events listing with nested markets (one
// page per 200 events; ~80 pages for the whole exchange). Series in exclude
// are skipped.
func (r *REST) ListActiveMarkets(ctx context.Context, minVolume float64, exclude []string) ([]gen.Market, error) {
	skip := map[string]bool{}
	for _, s := range exclude {
		skip[s] = true
	}
	var out []gen.Market
	limit := 200
	status := gen.GetEventsParamsStatus("open")
	params := &gen.GetEventsParams{Status: &status, Limit: &limit, WithNestedMarkets: true}
	for {
		resp, err := r.c.GetEventsWithResponse(ctx, params)
		if err != nil {
			return nil, fmt.Errorf("kalshi: list events: %w", err)
		}
		if resp.JSON200 == nil {
			return nil, httpError("list events", resp.HTTPResponse, resp.Body)
		}
		for _, e := range resp.JSON200.Events {
			if skip[e.SeriesTicker] {
				continue
			}
			for _, m := range e.Markets {
				v, err := strconv.ParseFloat(string(m.Volume24hFp), 64)
				if err == nil && v >= minVolume {
					out = append(out, m)
				}
			}
		}
		if resp.JSON200.Cursor == "" {
			return out, nil
		}
		c := resp.JSON200.Cursor
		params.Cursor = &c
	}
}

func httpError(op string, resp *http.Response, body []byte) error {
	const max = 300
	if len(body) > max {
		body = body[:max]
	}
	return fmt.Errorf("kalshi: %s: HTTP %d: %s", op, resp.StatusCode, body)
}
