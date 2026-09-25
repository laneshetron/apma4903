// Package spot records public market-data feeds (trades and top of book)
// from BTC/ETH-USD spot venues, so Kalshi events can be paired with the
// upstream prices that CF Benchmarks' BRTI/ETHUSD_RTI aggregate, and from
// perpetual-swap venues, which tend to lead spot in price discovery.
//
// Frames are recorded verbatim with the same {"rx_ns", "raw"} envelope as
// the Kalshi collector, under <data_dir>/spot/<exchange>/raw/YYYY-MM-DD/HH.jsonl.gz.
package spot

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"math/rand/v2"
	"path/filepath"
	"sync/atomic"
	"time"

	"github.com/coder/websocket"

	"github.com/laneshetron/kalshi/internal/recorder"
)

// Venue describes one exchange feed.
type Venue struct {
	Name           string
	URL            string
	Subscribe      []any // messages sent after connect, in order
	Heartbeat      any   // optional app-level message sent every HeartbeatEvery (a string is sent verbatim)
	HeartbeatEvery time.Duration
}

// Venues returns the supported feeds for the given symbols (base assets, e.g. BTC, ETH).
func Venues(names []string, assets []string) ([]Venue, error) {
	var out []Venue
	for _, n := range names {
		v, ok := venue(n, assets)
		if !ok {
			return nil, fmt.Errorf("spot: unknown venue %q", n)
		}
		out = append(out, v)
	}
	return out, nil
}

func venue(name string, assets []string) (Venue, bool) {
	sym := func(f func(a string) string) []string {
		out := make([]string, 0, len(assets))
		for _, a := range assets {
			out = append(out, f(a))
		}
		return out
	}
	switch name {
	case "coinbase":
		// Exchange (formerly GDAX) public feed: ticker carries best bid/ask and
		// last trade with exchange timestamps; matches are individual trades.
		return Venue{
			Name: name, URL: "wss://ws-feed.exchange.coinbase.com",
			Subscribe: []any{map[string]any{
				"type": "subscribe", "product_ids": sym(func(a string) string { return a + "-USD" }),
				"channels": []string{"ticker", "matches", "heartbeat"},
			}},
		}, true
	case "kraken":
		return Venue{
			Name: name, URL: "wss://ws.kraken.com/v2",
			Subscribe: []any{
				map[string]any{"method": "subscribe", "params": map[string]any{"channel": "trade", "symbol": sym(func(a string) string { return a + "/USD" })}},
				map[string]any{"method": "subscribe", "params": map[string]any{"channel": "ticker", "symbol": sym(func(a string) string { return a + "/USD" })}},
			},
		}, true
	case "bitstamp":
		// Trades only: Bitstamp's order_book_* channel streams 100-level
		// snapshots on every change, gigabytes per day for little value.
		var subs []any
		for _, a := range assets {
			subs = append(subs, map[string]any{"event": "bts:subscribe", "data": map[string]any{"channel": "live_trades_" + lower(a) + "usd"}})
		}
		return Venue{
			Name: name, URL: "wss://ws.bitstamp.net", Subscribe: subs,
			Heartbeat: map[string]any{"event": "bts:heartbeat"}, HeartbeatEvery: 15 * time.Second,
		}, true
	case "gemini":
		// Gemini v1 market data is per symbol; only the first asset is used on
		// this URL, so callers add one venue per asset via "gemini:<ASSET>".
		return Venue{}, false
	case "binance":
		streams := ""
		for i, a := range assets {
			if i > 0 {
				streams += "/"
			}
			streams += lower(a) + "usdt@trade/" + lower(a) + "usdt@bookTicker"
		}
		return Venue{Name: name, URL: "wss://stream.binance.com:9443/stream?streams=" + streams}, true
	case "coinbase_perp":
		// Advanced Trade feed relays the International Exchange perps
		// (BTC-PERP-INTX) without auth; the INTX feed itself rejects US IPs.
		ids := sym(func(a string) string { return a + "-PERP-INTX" })
		return Venue{
			Name: name, URL: "wss://advanced-trade-ws.coinbase.com",
			Subscribe: []any{
				map[string]any{"type": "subscribe", "product_ids": ids, "channel": "ticker"},
				map[string]any{"type": "subscribe", "product_ids": ids, "channel": "market_trades"},
				map[string]any{"type": "subscribe", "product_ids": []string{}, "channel": "heartbeats"},
			},
		}, true
	case "kraken_futures":
		ids := sym(func(a string) string {
			if a == "BTC" {
				a = "XBT"
			}
			return "PF_" + a + "USD"
		})
		return Venue{
			Name: name, URL: "wss://futures.kraken.com/ws/v1",
			Subscribe: []any{
				map[string]any{"event": "subscribe", "feed": "trade", "product_ids": ids},
				map[string]any{"event": "subscribe", "feed": "ticker", "product_ids": ids},
			},
		}, true
	case "okx":
		var args []any
		for _, a := range assets {
			args = append(args, map[string]any{"channel": "trades", "instId": a + "-USDT-SWAP"},
				map[string]any{"channel": "bbo-tbt", "instId": a + "-USDT-SWAP"})
		}
		return Venue{
			Name: name, URL: "wss://ws.okx.com:8443/ws/v5/public",
			Subscribe: []any{map[string]any{"op": "subscribe", "args": args}},
			Heartbeat: "ping", HeartbeatEvery: 25 * time.Second,
		}, true
	case "bybit":
		var args []string
		for _, a := range assets {
			args = append(args, "publicTrade."+a+"USDT", "orderbook.1."+a+"USDT")
		}
		return Venue{
			Name: name, URL: "wss://stream.bybit.com/v5/public/linear",
			Subscribe: []any{map[string]any{"op": "subscribe", "args": args}},
			Heartbeat: map[string]any{"op": "ping"}, HeartbeatEvery: 20 * time.Second,
		}, true
	case "hyperliquid":
		// l2Book is only published every ~5.4 s, so it is useless for a pre-trade
		// touch -- but it is the only public view of how much size rests away from
		// the touch, which is what bounds a resting strategy's achievable fill
		// share. Its 20 levels reach ~12 bp on ZEC and ~7 bp on ETH (only ~2.5 bp
		// on BTC, whose book is too tight for this to say anything).
		var subs []any
		for _, a := range assets {
			subs = append(subs, map[string]any{"method": "subscribe", "subscription": map[string]any{"type": "trades", "coin": a}},
				map[string]any{"method": "subscribe", "subscription": map[string]any{"type": "bbo", "coin": a}},
				map[string]any{"method": "subscribe", "subscription": map[string]any{"type": "l2Book", "coin": a}})
		}
		return Venue{
			Name: name, URL: "wss://api.hyperliquid.xyz/ws", Subscribe: subs,
			Heartbeat: map[string]any{"method": "ping"}, HeartbeatEvery: 50 * time.Second,
		}, true
	}
	if len(name) > 7 && name[:7] == "gemini:" {
		a := name[7:]
		return Venue{Name: "gemini_" + lower(a), URL: "wss://api.gemini.com/v1/marketdata/" + a + "USD?trades=true&top_of_book=true&heartbeat=true"}, true
	}
	return Venue{}, false
}

func lower(s string) string {
	b := []byte(s)
	for i, c := range b {
		if c >= 'A' && c <= 'Z' {
			b[i] = c + 32
		}
	}
	return string(b)
}

// Stats are per-venue counters.
type Stats struct {
	Connected  atomic.Bool
	Messages   atomic.Uint64
	Reconnects atomic.Uint64
	LastMsgNs  atomic.Int64
}

// Run records one venue until ctx is cancelled, reconnecting with backoff.
func Run(ctx context.Context, v Venue, dataDir string, log *slog.Logger, st *Stats) error {
	rec, err := recorder.Open(filepath.Join(dataDir, "spot", v.Name), time.Second)
	if err != nil {
		return err
	}
	defer rec.Close()
	log = log.With("venue", v.Name)
	backoff := time.Second
	for {
		err := runOnce(ctx, v, rec, log, st)
		if ctx.Err() != nil {
			return ctx.Err()
		}
		log.Warn("connection ended", "err", err, "retry_in", backoff)
		select {
		case <-time.After(backoff/2 + time.Duration(rand.Int64N(int64(backoff)))):
		case <-ctx.Done():
			return ctx.Err()
		}
		backoff = min(backoff*2, 30*time.Second)
		st.Reconnects.Add(1)
	}
}

func runOnce(ctx context.Context, v Venue, rec *recorder.Recorder, log *slog.Logger, st *Stats) error {
	dctx, cancel := context.WithTimeout(ctx, 20*time.Second)
	ws, resp, err := websocket.Dial(dctx, v.URL, nil)
	cancel()
	if err != nil {
		if resp != nil {
			return fmt.Errorf("dial: HTTP %d: %w", resp.StatusCode, err)
		}
		return fmt.Errorf("dial: %w", err)
	}
	ws.SetReadLimit(16 << 20)
	defer ws.Close(websocket.StatusNormalClosure, "bye")
	st.Connected.Store(true)
	defer st.Connected.Store(false)
	_ = rec.WriteLocal(recorder.EventConnect, map[string]any{"url": v.URL})
	defer func() { _ = rec.WriteLocal(recorder.EventDisconnect, nil) }()
	log.Info("connected")

	for _, m := range v.Subscribe {
		b, _ := json.Marshal(m)
		if err := ws.Write(ctx, websocket.MessageText, b); err != nil {
			return fmt.Errorf("subscribe: %w", err)
		}
	}

	// keepalive: protocol pings, plus the venue's app-level heartbeat if any
	kctx, kcancel := context.WithCancel(ctx)
	defer kcancel()
	go func() {
		ping := time.NewTicker(20 * time.Second)
		defer ping.Stop()
		var hb <-chan time.Time
		if v.Heartbeat != nil {
			t := time.NewTicker(v.HeartbeatEvery)
			defer t.Stop()
			hb = t.C
		}
		for {
			select {
			case <-kctx.Done():
				return
			case <-ping.C:
				pctx, c := context.WithTimeout(kctx, 10*time.Second)
				if err := ws.Ping(pctx); err != nil {
					c()
					ws.Close(websocket.StatusPolicyViolation, "ping timeout")
					return
				}
				c()
			case <-hb:
				b, ok := []byte(nil), false
				if s, isStr := v.Heartbeat.(string); isStr {
					b, ok = []byte(s), true
				}
				if !ok {
					b, _ = json.Marshal(v.Heartbeat)
				}
				_ = ws.Write(kctx, websocket.MessageText, b)
			}
		}
	}()

	for {
		typ, data, err := ws.Read(ctx)
		rx := time.Now()
		if err != nil {
			return fmt.Errorf("read: %w", err)
		}
		if typ != websocket.MessageText {
			continue
		}
		st.Messages.Add(1)
		st.LastMsgNs.Store(rx.UnixNano())
		if err := rec.Write(rx, data); err != nil {
			log.Error("record", "err", err)
		}
	}
}
