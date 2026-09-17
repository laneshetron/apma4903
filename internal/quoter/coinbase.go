package quoter

import (
	"context"
	"encoding/json"
	"strconv"
	"time"

	"github.com/coder/websocket"
)

// CoinbaseQuote is one top-of-book update from the Exchange ticker channel.
type CoinbaseQuote struct {
	Rx           time.Time
	ExchTs       time.Time
	Bid, Ask     float64
	BidSz, AskSz float64
}

// RunCoinbase streams BTC-USD ticker updates to out until ctx ends,
// reconnecting on failure. Raw frames are handed to record (if non-nil)
// before parsing so the tape is complete.
func RunCoinbase(ctx context.Context, product string, out chan<- CoinbaseQuote, record func(rx time.Time, raw []byte), onState func(connected bool, err error)) {
	backoff := time.Second
	for ctx.Err() == nil {
		err := runCoinbaseOnce(ctx, product, out, record, onState)
		if ctx.Err() != nil {
			return
		}
		if onState != nil {
			onState(false, err)
		}
		time.Sleep(backoff)
		if backoff < 10*time.Second {
			backoff *= 2
		}
	}
}

func runCoinbaseOnce(ctx context.Context, product string, out chan<- CoinbaseQuote, record func(time.Time, []byte), onState func(bool, error)) error {
	dctx, cancel := context.WithTimeout(ctx, 15*time.Second)
	ws, _, err := websocket.Dial(dctx, "wss://ws-feed.exchange.coinbase.com", nil)
	cancel()
	if err != nil {
		return err
	}
	defer ws.Close(websocket.StatusNormalClosure, "bye")
	ws.SetReadLimit(4 << 20)
	sub, _ := json.Marshal(map[string]any{"type": "subscribe", "product_ids": []string{product}, "channels": []string{"ticker", "heartbeat"}})
	if err := ws.Write(ctx, websocket.MessageText, sub); err != nil {
		return err
	}
	if onState != nil {
		onState(true, nil)
	}
	for {
		_, data, err := ws.Read(ctx)
		rx := time.Now()
		if err != nil {
			return err
		}
		if record != nil {
			record(rx, data)
		}
		var t struct {
			Type      string `json:"type"`
			ProductID string `json:"product_id"`
			BestBid   string `json:"best_bid"`
			BestAsk   string `json:"best_ask"`
			BestBidSz string `json:"best_bid_size"`
			BestAskSz string `json:"best_ask_size"`
			Time      string `json:"time"`
		}
		if json.Unmarshal(data, &t) != nil || t.Type != "ticker" || t.ProductID != product || t.BestBid == "" {
			continue
		}
		bid, e1 := strconv.ParseFloat(t.BestBid, 64)
		ask, e2 := strconv.ParseFloat(t.BestAsk, 64)
		if e1 != nil || e2 != nil {
			continue
		}
		bs, _ := strconv.ParseFloat(t.BestBidSz, 64)
		as, _ := strconv.ParseFloat(t.BestAskSz, 64)
		ts, _ := time.Parse(time.RFC3339Nano, t.Time)
		select {
		case out <- CoinbaseQuote{Rx: rx, ExchTs: ts, Bid: bid, Ask: ask, BidSz: bs, AskSz: as}:
		case <-ctx.Done():
			return ctx.Err()
		}
	}
}
