package quoter

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"github.com/laneshetron/kalshi/internal/book"
	"github.com/laneshetron/kalshi/internal/kalshi"
	"github.com/laneshetron/kalshi/internal/kalshi/gen"
)

// LiveExecutor places real orders through the REST API with explicit shard
// routing (auto-routing adds ~2 ms) and a post-only, maker-STP profile.
type LiveExecutor struct {
	cl     *gen.ClientWithResponses
	shard  int
	bucket *TokenBucket
}

// NewLiveExecutor builds a signed client for env routing to shard.
func NewLiveExecutor(env kalshi.Env, signer *kalshi.Signer, shard int, bucket *TokenBucket) (*LiveExecutor, error) {
	hc := &http.Client{Timeout: 5 * time.Second}
	cl, err := gen.NewClientWithResponses(env.RESTBase(), gen.WithHTTPClient(hc),
		gen.WithRequestEditorFn(func(_ context.Context, req *http.Request) error { return signer.SignRequest(req) }))
	if err != nil {
		return nil, err
	}
	return &LiveExecutor{cl: cl, shard: shard, bucket: bucket}, nil
}

// Warm makes one cheap request so the TLS session is established before the first order.
func (e *LiveExecutor) Warm(ctx context.Context) {
	_, _ = e.cl.GetExchangeStatusWithResponse(ctx)
}

// Place submits a post-only YES-book bid: side Yes -> bid at price; side No -> ask at 1-price.
func (e *LiveExecutor) Place(ctx context.Context, ticker string, side book.Side, price book.Price, qty book.Qty, clientID string) (string, time.Time, error) {
	if e.bucket != nil && !e.bucket.Take(CostOrder) {
		return "", time.Time{}, fmt.Errorf("rate limit: no write tokens for an order")
	}
	postOnly := true
	ex := gen.ExchangeIndex(e.shard)
	req := gen.CreateOrderV2Request{
		Ticker: ticker, Count: qty.String(), ClientOrderId: clientID, TimeInForce: gen.GoodTillCanceled,
		PostOnly: &postOnly, SelfTradePreventionType: gen.Maker, ExchangeIndex: &ex,
	}
	// the V2 endpoint quotes everything from the YES side: a NO bid at p is a YES ask at 1-p
	if side == book.Yes {
		req.Side, req.Price = gen.Bid, price.String()
	} else {
		req.Side, req.Price = gen.Ask, (book.OneDollar - price).String()
	}
	resp, err := e.cl.CreateOrderV2WithResponse(ctx, req)
	if err != nil {
		return "", time.Time{}, err
	}
	if resp.JSON201 == nil {
		return "", time.Time{}, fmt.Errorf("create order: HTTP %d %s", resp.StatusCode(), truncate(resp.Body, 200))
	}
	return resp.JSON201.OrderId, time.UnixMilli(resp.JSON201.TsMs), nil
}

// Cancel cancels orderID on the executor's shard.
func (e *LiveExecutor) Cancel(ctx context.Context, _ string, orderID string) (time.Time, error) {
	if e.bucket != nil && !e.bucket.Take(CostCancel) {
		return time.Time{}, fmt.Errorf("rate limit: no write tokens for a cancel")
	}
	ex := gen.ExchangeIndex(e.shard)
	resp, err := e.cl.CancelOrderV2WithResponse(ctx, orderID, &gen.CancelOrderV2Params{ExchangeIndex: &ex})
	if err != nil {
		return time.Time{}, err
	}
	if resp.JSON200 == nil {
		return time.Time{}, fmt.Errorf("cancel order: HTTP %d %s", resp.StatusCode(), truncate(resp.Body, 200))
	}
	return time.UnixMilli(resp.JSON200.TsMs), nil
}

func truncate(b []byte, n int) string {
	if len(b) > n {
		return string(b[:n]) + "..."
	}
	return string(b)
}
