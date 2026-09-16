// orderprobe measures Kalshi's order-entry latency from where it runs.
//
// It places a 1-contract YES bid far below the touch (default $0.01) on a
// live market with plenty of time to expiry, waits until the order shows up
// on the user_orders channel and in the public orderbook_delta stream, then
// cancels it and waits for both again. Each leg is timed against the local
// clock (chrony-synced on the AWS host) and against the engine's ts_ms.
//
//	orderprobe -config config.yaml -n 50 -series KXBTC15M -price 0.01 -out probe.jsonl
//
// Money at risk per iteration: 1 contract at $0.01 = $0.01, and only if the
// market collapses to that price while the order rests (a few hundred ms).
package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"net/http"
	"os"
	"sort"
	"strings"
	"time"

	"github.com/google/uuid"

	"github.com/laneshetron/kalshi/internal/config"
	"github.com/laneshetron/kalshi/internal/kalshi"
	"github.com/laneshetron/kalshi/internal/kalshi/gen"
)

type sample struct {
	I       int    `json:"i"`
	Ticker  string `json:"ticker"`
	OrderID string `json:"order_id"`
	Send    int64  `json:"send_ns"`
	// create leg, ms relative to Send
	CreateAck    float64 `json:"create_ack_ms"`      // HTTP response received
	CreateEngine float64 `json:"create_engine_ms"`   // engine ts_ms - send
	CreateUser   float64 `json:"create_user_ms"`     // user_orders message received
	CreateDelta  float64 `json:"create_delta_ms"`    // public orderbook_delta received
	CreateDelTs  float64 `json:"create_delta_ts_ms"` // delta's own ts_ms - send
	// cancel leg, ms relative to CancelSend
	CancelSend   int64   `json:"cancel_send_ns"`
	CancelAck    float64 `json:"cancel_ack_ms"`
	CancelEngine float64 `json:"cancel_engine_ms"`
	CancelUser   float64 `json:"cancel_user_ms"`
	CancelDelta  float64 `json:"cancel_delta_ms"`
	CancelDelTs  float64 `json:"cancel_delta_ts_ms"`
	Err          string  `json:"err,omitempty"`
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run() error {
	cfgPath := flag.String("config", "config.yaml", "collector config (for env and credentials)")
	series := flag.String("series", "KXBTC15M", "series to pick a market from")
	price := flag.String("price", "0.01", "YES bid price, dollars")
	n := flag.Int("n", 50, "iterations")
	gap := flag.Duration("gap", 1500*time.Millisecond, "pause between iterations")
	restBase := flag.String("rest", "", "override REST base URL, e.g. https://trading-api.kalshi.com/trade-api/v2")
	out := flag.String("out", "", "write per-iteration JSON lines here")
	flag.Parse()

	cfg, err := config.Load(*cfgPath)
	if err != nil {
		return err
	}
	env, _ := kalshi.ParseEnv(cfg.Env)
	signer, err := kalshi.NewSignerFromFile(cfg.KeyID, cfg.PrivateKeyPath)
	if err != nil {
		return err
	}
	base := env.RESTBase()
	if *restBase != "" {
		base = *restBase
	}
	hc := &http.Client{Timeout: 10 * time.Second}
	cl, err := gen.NewClientWithResponses(base, gen.WithHTTPClient(hc),
		gen.WithRequestEditorFn(func(_ context.Context, req *http.Request) error { return signer.SignRequest(req) }))
	if err != nil {
		return err
	}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// pick the open market of the series with the most time left (>= 8 min)
	ticker, err := pickMarket(ctx, cl, *series)
	if err != nil {
		return err
	}
	fmt.Fprintf(os.Stderr, "market %s, REST %s, price %s\n", ticker, base, *price)

	conn, err := kalshi.Dial(ctx, env, signer, kalshi.DialOptions{})
	if err != nil {
		return err
	}
	if _, err := conn.Subscribe(ctx, kalshi.SubscribeParams{Channels: []string{"user_orders"}, MarketTickers: []string{ticker}}); err != nil {
		return err
	}
	if _, err := conn.Subscribe(ctx, kalshi.SubscribeParams{Channels: []string{"orderbook_delta"}, MarketTickers: []string{ticker}}); err != nil {
		return err
	}
	// drain the snapshot and whatever else arrives; route by content
	userEv := make(chan kalshi.RawMessage, 64)
	deltaEv := make(chan kalshi.RawMessage, 1024)
	go func() {
		for m := range conn.Messages() {
			var e kalshi.Envelope
			if json.Unmarshal(m.Data, &e) != nil {
				continue
			}
			switch e.Type {
			case "user_order":
				userEv <- m
			case "orderbook_delta":
				deltaEv <- m
			}
		}
	}()

	// warm the HTTP connection (TLS handshake) so iteration 1 is not an outlier
	_, _ = cl.GetExchangeStatusWithResponse(ctx)

	var w *os.File
	if *out != "" {
		if w, err = os.Create(*out); err != nil {
			return err
		}
		defer w.Close()
	}
	var samples []sample
	for i := 0; i < *n; i++ {
		s := probeOnce(ctx, cl, ticker, *price, userEv, deltaEv)
		s.I = i
		samples = append(samples, s)
		if w != nil {
			b, _ := json.Marshal(s)
			w.Write(append(b, '\n'))
		}
		if s.Err != "" {
			fmt.Fprintf(os.Stderr, "iter %d: %s\n", i, s.Err)
		} else {
			fmt.Fprintf(os.Stderr, "iter %2d create: ack %.1f engine %.1f user %.1f delta %.1f | cancel: ack %.1f engine %.1f user %.1f delta %.1f ms\n",
				i, s.CreateAck, s.CreateEngine, s.CreateUser, s.CreateDelta, s.CancelAck, s.CancelEngine, s.CancelUser, s.CancelDelta)
		}
		time.Sleep(*gap)
	}
	summarize(samples)
	return nil
}

func pickMarket(ctx context.Context, cl *gen.ClientWithResponses, series string) (string, error) {
	status := gen.GetMarketsParamsStatusOpen
	resp, err := cl.GetMarketsWithResponse(ctx, &gen.GetMarketsParams{SeriesTicker: series, Status: &status})
	if err != nil {
		return "", err
	}
	if resp.JSON200 == nil {
		return "", fmt.Errorf("list markets: HTTP %d", resp.StatusCode())
	}
	best, bestT := "", time.Time{}
	for _, m := range resp.JSON200.Markets {
		if m.CloseTime.After(bestT) {
			best, bestT = m.Ticker, m.CloseTime
		}
	}
	if best == "" || time.Until(bestT) < 8*time.Minute {
		return "", errors.New("no open market with >= 8 min to close")
	}
	return best, nil
}

func drain(ch chan kalshi.RawMessage) {
	for {
		select {
		case <-ch:
		default:
			return
		}
	}
}

// waitDelta waits for an orderbook_delta at price on the yes side with the given sign; returns rx and ts_ms.
func waitDelta(ctx context.Context, ch chan kalshi.RawMessage, price string, sign int, timeout time.Duration) (time.Time, int64, error) {
	deadline := time.After(timeout)
	want := strings.TrimRight(strings.TrimRight(price, "0"), ".")
	for {
		select {
		case m := <-ch:
			var e kalshi.Envelope
			if json.Unmarshal(m.Data, &e) != nil {
				continue
			}
			var d struct {
				Price string `json:"price_dollars"`
				Delta string `json:"delta_fp"`
				Side  string `json:"side"`
				TsMs  int64  `json:"ts_ms"`
			}
			if json.Unmarshal(e.Msg, &d) != nil || d.Side != "yes" {
				continue
			}
			p := strings.TrimRight(strings.TrimRight(d.Price, "0"), ".")
			neg := strings.HasPrefix(d.Delta, "-")
			if p == want && ((sign > 0 && !neg) || (sign < 0 && neg)) {
				return m.Rx, d.TsMs, nil
			}
		case <-deadline:
			return time.Time{}, 0, errors.New("timeout waiting for delta")
		case <-ctx.Done():
			return time.Time{}, 0, ctx.Err()
		}
	}
}

func waitUser(ctx context.Context, ch chan kalshi.RawMessage, orderID, status string, timeout time.Duration) (time.Time, error) {
	deadline := time.After(timeout)
	for {
		select {
		case m := <-ch:
			var e kalshi.Envelope
			if json.Unmarshal(m.Data, &e) != nil {
				continue
			}
			var u struct {
				OrderID string `json:"order_id"`
				Status  string `json:"status"`
			}
			if json.Unmarshal(e.Msg, &u) == nil && u.OrderID == orderID && u.Status == status {
				return m.Rx, nil
			}
		case <-deadline:
			return time.Time{}, fmt.Errorf("timeout waiting for user_order %s", status)
		case <-ctx.Done():
			return time.Time{}, ctx.Err()
		}
	}
}

func probeOnce(ctx context.Context, cl *gen.ClientWithResponses, ticker, price string, userEv, deltaEv chan kalshi.RawMessage) sample {
	drain(userEv)
	drain(deltaEv)
	ms := func(t0 time.Time, t time.Time) float64 { return float64(t.Sub(t0).Nanoseconds()) / 1e6 }
	postOnly := true
	req := gen.CreateOrderV2Request{
		Ticker: ticker, Side: gen.Bid, Count: "1", Price: price, ClientOrderId: uuid.NewString(),
		TimeInForce: gen.GoodTillCanceled, PostOnly: &postOnly, SelfTradePreventionType: gen.Maker,
	}
	s := sample{Ticker: ticker}
	t0 := time.Now()
	s.Send = t0.UnixNano()
	resp, err := cl.CreateOrderV2WithResponse(ctx, req)
	tAck := time.Now()
	if err != nil {
		s.Err = "create: " + err.Error()
		return s
	}
	if resp.JSON201 == nil {
		s.Err = fmt.Sprintf("create: HTTP %d %s", resp.StatusCode(), string(resp.Body))
		return s
	}
	s.OrderID = resp.JSON201.OrderId
	s.CreateAck = ms(t0, tAck)
	s.CreateEngine = float64(resp.JSON201.TsMs) - float64(t0.UnixNano())/1e6
	if resp.JSON201.FillCount != "" && resp.JSON201.FillCount != "0" && resp.JSON201.FillCount != "0.00" {
		s.Err = "create: order filled " + resp.JSON201.FillCount
	}
	if t, err := waitUser(ctx, userEv, s.OrderID, "resting", 3*time.Second); err == nil {
		s.CreateUser = ms(t0, t)
	} else {
		s.CreateUser = -1
	}
	if t, ts, err := waitDelta(ctx, deltaEv, price, +1, 3*time.Second); err == nil {
		s.CreateDelta = ms(t0, t)
		s.CreateDelTs = float64(ts) - float64(t0.UnixNano())/1e6
	} else {
		s.CreateDelta, s.CreateDelTs = -1, -1
	}

	drain(userEv)
	drain(deltaEv)
	t1 := time.Now()
	s.CancelSend = t1.UnixNano()
	cresp, err := cl.CancelOrderV2WithResponse(ctx, s.OrderID, &gen.CancelOrderV2Params{MarketTicker: ticker})
	tCAck := time.Now()
	if err != nil {
		s.Err = "cancel: " + err.Error()
		return s
	}
	if cresp.JSON200 == nil {
		s.Err = fmt.Sprintf("cancel: HTTP %d %s", cresp.StatusCode(), string(cresp.Body))
		return s
	}
	s.CancelAck = ms(t1, tCAck)
	s.CancelEngine = float64(cresp.JSON200.TsMs) - float64(t1.UnixNano())/1e6
	if t, err := waitUser(ctx, userEv, s.OrderID, "canceled", 3*time.Second); err == nil {
		s.CancelUser = ms(t1, t)
	} else {
		s.CancelUser = -1
	}
	if t, ts, err := waitDelta(ctx, deltaEv, price, -1, 3*time.Second); err == nil {
		s.CancelDelta = ms(t1, t)
		s.CancelDelTs = float64(ts) - float64(t1.UnixNano())/1e6
	} else {
		s.CancelDelta, s.CancelDelTs = -1, -1
	}
	return s
}

func summarize(samples []sample) {
	pct := func(xs []float64, p float64) float64 {
		if len(xs) == 0 {
			return -1
		}
		sort.Float64s(xs)
		i := int(p * float64(len(xs)-1))
		return xs[i]
	}
	cols := []struct {
		name string
		get  func(sample) float64
	}{
		{"create: send->engine ts", func(s sample) float64 { return s.CreateEngine }},
		{"create: send->HTTP ack", func(s sample) float64 { return s.CreateAck }},
		{"create: send->user_orders", func(s sample) float64 { return s.CreateUser }},
		{"create: send->public delta", func(s sample) float64 { return s.CreateDelta }},
		{"create: send->delta ts_ms", func(s sample) float64 { return s.CreateDelTs }},
		{"cancel: send->engine ts", func(s sample) float64 { return s.CancelEngine }},
		{"cancel: send->HTTP ack", func(s sample) float64 { return s.CancelAck }},
		{"cancel: send->user_orders", func(s sample) float64 { return s.CancelUser }},
		{"cancel: send->public delta", func(s sample) float64 { return s.CancelDelta }},
		{"cancel: send->delta ts_ms", func(s sample) float64 { return s.CancelDelTs }},
	}
	ok := 0
	for _, s := range samples {
		if s.Err == "" {
			ok++
		}
	}
	fmt.Printf("\n%d/%d iterations ok\n\n| leg | min | p10 | p50 | p90 | max |\n|---|---|---|---|---|---|\n", ok, len(samples))
	for _, c := range cols {
		var xs []float64
		for _, s := range samples {
			if v := c.get(s); s.Err == "" && v >= 0 {
				xs = append(xs, v)
			}
		}
		fmt.Printf("| %s | %.1f | %.1f | %.1f | %.1f | %.1f |\n", c.name, pct(xs, 0), pct(xs, 0.1), pct(xs, 0.5), pct(xs, 0.9), pct(xs, 1))
	}
}
