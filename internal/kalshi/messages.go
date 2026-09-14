package kalshi

import (
	"encoding/json"
	"fmt"
)

// WebSocket message and command types, following specs/asyncapi.yaml.

// Channel names.
const (
	ChannelOrderbookDelta  = "orderbook_delta"
	ChannelTicker          = "ticker"
	ChannelTrade           = "trade"
	ChannelMarketLifecycle = "market_lifecycle_v2"
)

// Server message types.
const (
	TypeSubscribed        = "subscribed"
	TypeUnsubscribed      = "unsubscribed"
	TypeOK                = "ok"
	TypeError             = "error"
	TypeOrderbookSnapshot = "orderbook_snapshot"
	TypeOrderbookDelta    = "orderbook_delta"
	TypeTicker            = "ticker"
	TypeTrade             = "trade"
)

// Command is a client -> server command envelope.
type Command struct {
	ID     int    `json:"id"`
	Cmd    string `json:"cmd"`
	Params any    `json:"params,omitempty"`
}

// SubscribeParams are the params for cmd "subscribe".
type SubscribeParams struct {
	Channels      []string `json:"channels"`
	MarketTickers []string `json:"market_tickers,omitempty"`
}

// UnsubscribeParams are the params for cmd "unsubscribe".
type UnsubscribeParams struct {
	Sids []int `json:"sids"`
}

// UpdateSubscription actions.
const (
	ActionAddMarkets    = "add_markets"
	ActionDeleteMarkets = "delete_markets"
	ActionGetSnapshot   = "get_snapshot"
)

// UpdateSubscriptionParams are the params for cmd "update_subscription".
type UpdateSubscriptionParams struct {
	Sids          []int    `json:"sids"`
	MarketTickers []string `json:"market_tickers"`
	Action        string   `json:"action"`
}

// Envelope is the common shape of every server -> client message. Msg is left
// raw so callers can decode it into the type-specific payload.
type Envelope struct {
	ID   int             `json:"id,omitempty"` // echo of the command id on responses
	Type string          `json:"type"`
	Sid  int             `json:"sid,omitempty"`
	Seq  uint64          `json:"seq,omitempty"`
	Msg  json.RawMessage `json:"msg,omitempty"`
}

// Decode decodes Msg into v.
func (e *Envelope) Decode(v any) error {
	if err := json.Unmarshal(e.Msg, v); err != nil {
		return fmt.Errorf("kalshi: decode %s msg: %w", e.Type, err)
	}
	return nil
}

// SubscribedMsg is the msg of a "subscribed" response.
type SubscribedMsg struct {
	Channel string `json:"channel"`
	Sid     int    `json:"sid"`
}

// OKMsg is the msg of an "ok" response to update_subscription.
type OKMsg struct {
	MarketTickers []string `json:"market_tickers"`
}

// ErrorMsg is the msg of an "error" response.
type ErrorMsg struct {
	Code int    `json:"code"`
	Msg  string `json:"msg"`
}

func (e ErrorMsg) Error() string { return fmt.Sprintf("kalshi ws error %d: %s", e.Code, e.Msg) }

// PriceLevel is a [price_dollars, contracts_fp] tuple.
type PriceLevel [2]string

func (l PriceLevel) Price() string { return l[0] }
func (l PriceLevel) Qty() string   { return l[1] }

// OrderbookSnapshotMsg is the msg of an "orderbook_snapshot". Both sides list
// resting bids; either may be absent when empty.
type OrderbookSnapshotMsg struct {
	MarketTicker string       `json:"market_ticker"`
	MarketID     string       `json:"market_id"`
	YesDollarsFP []PriceLevel `json:"yes_dollars_fp"`
	NoDollarsFP  []PriceLevel `json:"no_dollars_fp"`
}

// OrderbookDeltaMsg is the msg of an "orderbook_delta": a relative quantity
// change at one price level on one side.
type OrderbookDeltaMsg struct {
	MarketTicker  string `json:"market_ticker"`
	MarketID      string `json:"market_id"`
	PriceDollars  string `json:"price_dollars"`
	DeltaFP       string `json:"delta_fp"`
	Side          string `json:"side"`
	TsMs          int64  `json:"ts_ms"`
	ClientOrderID string `json:"client_order_id,omitempty"`
}

// TradeMsg is the msg of a "trade".
type TradeMsg struct {
	TradeID          string `json:"trade_id"`
	MarketTicker     string `json:"market_ticker"`
	YesPriceDollars  string `json:"yes_price_dollars"`
	NoPriceDollars   string `json:"no_price_dollars"`
	CountFP          string `json:"count_fp"`
	TakerSide        string `json:"taker_side"`
	TakerOutcomeSide string `json:"taker_outcome_side"`
	TakerBookSide    string `json:"taker_book_side"`
	IsBlockTrade     bool   `json:"is_block_trade"`
	TsMs             int64  `json:"ts_ms"`
}

// TickerMsg is the msg of a "ticker".
type TickerMsg struct {
	MarketTicker    string `json:"market_ticker"`
	PriceDollars    string `json:"price_dollars"`
	YesBidDollars   string `json:"yes_bid_dollars"`
	YesAskDollars   string `json:"yes_ask_dollars"`
	VolumeFP        string `json:"volume_fp"`
	OpenInterestFP  string `json:"open_interest_fp"`
	YesBidSizeFP    string `json:"yes_bid_size_fp"`
	YesAskSizeFP    string `json:"yes_ask_size_fp"`
	LastTradeSizeFP string `json:"last_trade_size_fp"`
	TsMs            int64  `json:"ts_ms"`
}

// UnmarshalFrom decodes an envelope from raw bytes.
func (e *Envelope) UnmarshalFrom(data []byte) error {
	return json.Unmarshal(data, e)
}
