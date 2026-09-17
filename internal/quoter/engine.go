package quoter

import (
	"context"
	"fmt"
	"log/slog"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"

	"github.com/laneshetron/kalshi/internal/book"
	"github.com/laneshetron/kalshi/internal/feed"
	"github.com/laneshetron/kalshi/internal/kalshi"
	"github.com/laneshetron/kalshi/internal/recorder"
)

// Market is the contract being quoted.
type Market struct {
	Ticker  string
	Strike  float64
	CloseAt time.Time
}

// BookSource is the live book provider (the feed in production).
type BookSource interface {
	Book(ticker string) (feed.BookView, bool)
	SetMarkets(ctx context.Context, tickers []string) error
}

// EngineConfig wires the engine.
type EngineConfig struct {
	Params   Params
	Limits   Limits
	Series   string
	Mode     string // "paper" | "live"
	Exec     Executor
	Paper    *PaperExecutor // non-nil in paper mode: receives public book events
	Feed     BookSource
	Recorder *recorder.Recorder
	Edge     *EdgeModel
	Logger   *slog.Logger
	// PickMarket returns the market to quote now (nil = none open).
	PickMarket func(ctx context.Context) (*Market, error)
	// Balance, if set, returns the free collateral on the trading shard ($); polled every few seconds.
	Balance func(ctx context.Context) (float64, error)
	// Capital, when Balance is nil, is a fixed budget (paper mode); <0 = unlimited.
	Capital float64
	// Recover, if set (live), is called when a market is adopted: it should cancel any resting
	// orders left on that market by a previous process and return the current position.
	Recover func(ctx context.Context, ticker string) (pos book.Qty, err error)
}

// Engine runs the strategy on one market at a time.
type Engine struct {
	cfg   EngineConfig
	log   *slog.Logger
	strat *Strategy
	risk  *Risk
	spot  *SpotState

	events chan feed.Event
	quotes chan CoinbaseQuote

	mu                sync.Mutex
	market            *Market
	ledger            *Ledger
	inflight          map[book.Side]bool   // a place is being sent
	wantCancel        map[book.Side]string // cancel requested while the place was unacknowledged
	lastBookRx        time.Time
	available         float64   // free collateral ($) as last polled (net of reservations at that time), -1 = unknown/unlimited
	reservedAtPoll    float64   // our working orders' collateral when the balance was polled
	fillCostSincePoll float64   // collateral turned into position cost since the poll
	started           time.Time // engine start, or the last market roll
	closedPnL         float64   // paper: mark P&L of finished markets this session
	startBalance      float64   // live: exchange balance at the first successful poll
	haveStart         bool
	posAtPoll         book.Qty  // our position when the balance was polled (equity needs a consistent snapshot)
	seqGap            bool
	halted            string
	paused            string
	stats             Stats
	vetoes            map[string]int // snapshot of the strategy's veto counters (the strategy is owned by the loop goroutine)
}

// Stats is the status-endpoint summary.
type Stats struct {
	Mode       string         `json:"mode"`
	Market     string         `json:"market"`
	Halted     string         `json:"halted,omitempty"`
	Paused     string         `json:"paused,omitempty"`
	Pos        string         `json:"pos"`
	Cash       float64        `json:"cash_$"`
	MarkPnL    float64        `json:"mark_pnl_$"`
	SessionPnL float64        `json:"session_pnl_$"` // finished markets + current mark
	Fills      int            `json:"fills"`
	Available  float64        `json:"available_$"`
	Placed     int            `json:"placed"`
	Canceled   int            `json:"canceled"`
	Errors     int            `json:"errors"`
	Rejections int            `json:"rejections"`
	Vetoes     map[string]int `json:"vetoes"`
	SpotLagMs  float64        `json:"coinbase_lag_ms"`
	BookAgeMs  float64        `json:"book_age_ms"`
	Working    map[string]any `json:"working"`
	CoinbaseOK bool           `json:"coinbase_connected"`
}

// NewEngine constructs an engine; call Run.
func NewEngine(cfg EngineConfig) *Engine {
	if cfg.Logger == nil {
		cfg.Logger = slog.Default()
	}
	return &Engine{
		cfg: cfg, log: cfg.Logger, strat: NewStrategy(cfg.Params), risk: NewRisk(cfg.Limits), spot: &SpotState{},
		events: make(chan feed.Event, 8192), quotes: make(chan CoinbaseQuote, 1024),
		inflight: map[book.Side]bool{}, wantCancel: map[book.Side]string{}, available: -1,
	}
}

// OnFeedEvent is the feed.Config.OnEvent hook (called on the feed goroutine; must not block long).
func (e *Engine) OnFeedEvent(ev feed.Event) {
	ev.Book = nil // never share the live book across goroutines
	select {
	case e.events <- ev:
	default:
		e.log.Warn("event queue full; dropping", "type", ev.Type)
	}
}

// Quotes is the channel RunCoinbase should write to.
func (e *Engine) Quotes() chan<- CoinbaseQuote { return e.quotes }

// PaperFill is the PaperExecutor's OnFill callback: routes simulated fills to the current ledger.
func (e *Engine) PaperFill(fillID string, f Fill) {
	e.mu.Lock()
	l := e.ledger
	e.stats.Fills++
	e.mu.Unlock()
	if l != nil && f.Ticker == l.ticker {
		l.OnFill(fillID, f)
	}
}

// SetCoinbaseState records Coinbase connection state for the status page.
func (e *Engine) SetCoinbaseState(ok bool, err error) {
	e.mu.Lock()
	e.stats.CoinbaseOK = ok
	e.mu.Unlock()
	if err != nil {
		e.log.Warn("coinbase feed", "err", err)
	}
	e.tape("coinbase_state", map[string]any{"connected": ok, "err": errStr(err)})
}

func errStr(err error) string {
	if err == nil {
		return ""
	}
	return err.Error()
}

// tape writes a quoter event to the recorder.
func (e *Engine) tape(kind string, fields map[string]any) {
	if e.cfg.Recorder == nil {
		return
	}
	f := map[string]any{"kind": kind}
	for k, v := range fields {
		f[k] = v
	}
	_ = e.cfg.Recorder.WriteLocal("quoter", f)
}

// Run processes events until ctx ends. On exit every working order is cancelled.
func (e *Engine) Run(ctx context.Context) error {
	tick := time.NewTicker(100 * time.Millisecond)
	defer tick.Stop()
	roll := time.NewTicker(5 * time.Second)
	defer roll.Stop()
	e.mu.Lock()
	e.started = time.Now()
	if e.cfg.Balance == nil {
		e.available = e.cfg.Capital
	}
	e.mu.Unlock()
	e.rollMarket(ctx)
	e.refreshBalance(ctx)
	bal := time.NewTicker(5 * time.Second)
	defer bal.Stop()
	for {
		select {
		case <-ctx.Done():
			e.shutdown()
			return ctx.Err()
		case ev := <-e.events:
			e.onFeed(ctx, ev)
		case q := <-e.quotes:
			e.onQuote(ctx, q)
		case now := <-tick.C:
			e.onTick(ctx, now)
		case <-roll.C:
			e.rollMarket(ctx)
		case <-bal.C:
			e.refreshBalance(ctx)
		}
	}
}

// refreshBalance polls the exchange for free collateral (live mode).
func (e *Engine) refreshBalance(ctx context.Context) {
	if e.cfg.Balance == nil {
		return
	}
	cctx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	b, err := e.cfg.Balance(cctx)
	if err != nil {
		e.log.Warn("balance", "err", err)
		return
	}
	reserved := 0.0
	var posNow book.Qty
	e.mu.Lock()
	l := e.ledger
	e.mu.Unlock()
	if l != nil {
		for _, o := range l.WorkingOrders() {
			reserved += Collateral(o.Price, o.Qty-o.Filled)
		}
		posNow, _ = l.Position()
	}
	e.mu.Lock()
	e.available, e.reservedAtPoll, e.fillCostSincePoll, e.posAtPoll = b, reserved, 0, posNow
	e.stats.Available = b
	if !e.haveStart {
		e.startBalance, e.haveStart = b, true
		e.log.Info("session start balance", "balance", fmt.Sprintf("%.2f", b))
	}
	e.mu.Unlock()
}

// sessionPnL is the session's P&L for the loss limit. Live: the exchange's
// balance change (settlements included) plus the current open position at
// mid; paper: the sum of finished markets' marks plus the current mark.
func (e *Engine) sessionPnL(l *Ledger, mid book.Price) float64 {
	e.mu.Lock()
	defer e.mu.Unlock()
	if e.cfg.Balance != nil {
		if !e.haveStart {
			return 0
		}
		pos := e.posAtPoll // same instant as the balance; a fresher position would double-count fills the balance has not seen
		posValue := 0.0
		if pos > 0 {
			posValue = float64(pos) / 100 * float64(mid) / float64(book.OneDollar)
		} else if pos < 0 {
			posValue = float64(-pos) / 100 * float64(book.OneDollar-mid) / float64(book.OneDollar)
		}
		// equity = exchange balance (cost of the open position already out, settlements in) + open position at mid.
		// Deliberately no between-poll adjustments: those are estimates, and a stop must not fire on estimates.
		return e.available - e.startBalance + posValue
	}
	return e.closedPnL + l.MarkPnL(mid)
}

// freeCollateral is the exchange balance less what our working orders reserve since the last poll,
// and in paper mode the fixed budget less all reservations and the position's cost.
func (e *Engine) freeCollateral(l *Ledger) (float64, bool) {
	e.mu.Lock()
	avail, atPoll, fillCost := e.available, e.reservedAtPoll, e.fillCostSincePoll
	e.mu.Unlock()
	if avail < 0 {
		return 0, false // unknown / unlimited
	}
	reserved := 0.0
	for _, o := range l.WorkingOrders() {
		reserved += Collateral(o.Price, o.Qty-o.Filled)
	}
	if e.cfg.Balance == nil {
		return avail - l.CollateralUsed() - reserved, true // paper: fixed budget less position collateral and reservations
	}
	// live: Kalshi's balance is gross cash (resting reservations are not deducted); fills since the
	// poll have spent cash the poll did not see
	_ = atPoll
	return avail - reserved - fillCost, true
}

func (e *Engine) shutdown() {
	e.mu.Lock()
	l := e.ledger
	e.mu.Unlock()
	if l == nil {
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	for _, side := range []book.Side{book.Yes, book.No} {
		if err := l.Cancel(ctx, e.cfg.Exec, side, "shutdown"); err != nil {
			e.log.Error("shutdown cancel", "side", side, "err", err)
		}
	}
	e.tape("shutdown", nil)
}

// rollMarket switches to the market PickMarket returns when it changes.
func (e *Engine) rollMarket(ctx context.Context) {
	m, err := e.cfg.PickMarket(ctx)
	if err != nil {
		e.log.Warn("pick market", "err", err)
		return
	}
	e.mu.Lock()
	cur := e.market
	e.mu.Unlock()
	if m == nil || (cur != nil && cur.Ticker == m.Ticker) {
		return
	}
	if cur != nil {
		e.shutdownMarket(cur)
	}
	ledger := NewLedger(m.Ticker, func(kind string, fields map[string]any) {
		fields["ticker"] = m.Ticker
		e.tape(kind, fields)
	})
	// subscribe first so a recovered position can be marked at a real mid
	if err := e.cfg.Feed.SetMarkets(ctx, []string{m.Ticker}); err != nil {
		e.log.Error("subscribe market", "ticker", m.Ticker, "err", err)
	}
	if e.cfg.Recover != nil {
		rctx, cancel := context.WithTimeout(ctx, 10*time.Second)
		pos, err := e.cfg.Recover(rctx, m.Ticker)
		cancel()
		if err != nil {
			e.log.Error("recover position", "ticker", m.Ticker, "err", err)
		} else if pos != 0 {
			mid, ok := e.waitMid(ctx, m.Ticker, 5*time.Second)
			if !ok {
				e.log.Warn("no book to mark the recovered position; marking at 50c", "ticker", m.Ticker)
				mid = 5000
			}
			ledger.Seed(pos, mid)
			e.log.Warn("recovered position from a previous process", "ticker", m.Ticker, "pos", pos, "marked_at", mid)
			e.tape("recovered", map[string]any{"ticker": m.Ticker, "pos": pos.String(), "mid": mid.String()})
		}
	}
	e.mu.Lock()
	e.market, e.ledger = m, ledger
	e.inflight, e.wantCancel = map[book.Side]bool{}, map[book.Side]string{}
	e.strat = NewStrategy(e.cfg.Params)               // fresh cooldowns
	e.lastBookRx, e.started = time.Time{}, time.Now() // the new market's book needs a moment to arrive
	e.mu.Unlock()
	e.log.Info("quoting", "ticker", m.Ticker, "strike", m.Strike, "close", m.CloseAt.Format(time.RFC3339))
	e.tape("market", map[string]any{"ticker": m.Ticker, "strike": m.Strike, "close_at": m.CloseAt.UnixMilli()})
}

// waitMid polls the feed for a usable mid on ticker for up to d.
func (e *Engine) waitMid(ctx context.Context, ticker string, d time.Duration) (book.Price, bool) {
	deadline := time.Now().Add(d)
	for time.Now().Before(deadline) && ctx.Err() == nil {
		if bv, ok := e.cfg.Feed.Book(ticker); ok && !bv.Stale {
			if mid, ok := bv.Book.Top().Mid(); ok {
				return mid, true
			}
		}
		time.Sleep(50 * time.Millisecond)
	}
	return 0, false
}

func (e *Engine) shutdownMarket(m *Market) {
	e.mu.Lock()
	l := e.ledger
	e.mu.Unlock()
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	for _, side := range []book.Side{book.Yes, book.No} {
		_ = l.Cancel(ctx, e.cfg.Exec, side, "roll")
	}
	pos, cash := l.Position()
	mid := book.Price(5000)
	if bv, ok := e.cfg.Feed.Book(m.Ticker); ok {
		if mm, ok := bv.Book.Top().Mid(); ok {
			mid = mm
		}
	}
	pnl := l.MarkPnL(mid)
	e.mu.Lock()
	e.closedPnL += pnl
	e.stats.SessionPnL = e.closedPnL
	e.mu.Unlock()
	e.tape("market_done", map[string]any{"ticker": m.Ticker, "pos": pos.String(), "cash": cash, "fills": len(l.Fills()), "mark_pnl": pnl, "session_pnl": e.closedPnL})
	e.log.Info("market done", "ticker", m.Ticker, "pos", pos, "cash", fmt.Sprintf("%.2f", cash), "fills", len(l.Fills()), "mark_pnl", fmt.Sprintf("%.2f", pnl), "session", fmt.Sprintf("%.2f", e.closedPnL))
}

func (e *Engine) onFeed(ctx context.Context, ev feed.Event) {
	e.mu.Lock()
	m, l := e.market, e.ledger
	if ev.Gap {
		e.seqGap = true
	}
	e.mu.Unlock()
	switch ev.Type {
	case kalshi.TypeCFBenchmarks5Hz, kalshi.TypeCFBenchmarksValue:
		if ev.Index != nil && ev.Ticker == "BRTI" {
			if v, err := parseFloat(ev.Index.Value); err == nil {
				e.spot.OnBRTI(ev.Rx, v)
			}
		}
		return
	case kalshi.TypeUserOrder:
		if l != nil && ev.Order != nil && ev.Order.Ticker == m.Ticker {
			rem, _ := book.ParseQty(ev.Order.RemainingCountFP)
			l.OnOrderUpdate(ev.Order.OrderID, ev.Order.ClientOrderID, ev.Order.Status, rem)
			e.tape("user_order", map[string]any{"order_id": ev.Order.OrderID, "status": ev.Order.Status, "remaining": ev.Order.RemainingCountFP})
			e.afterAck(ctx)
		}
		return
	case kalshi.TypeFill:
		if l != nil && ev.Fill != nil && ev.Fill.MarketTicker == m.Ticker && e.cfg.Mode == "live" {
			e.applyLiveFill(l, ev)
		}
		return
	}
	if m == nil || ev.Ticker != m.Ticker {
		return
	}
	switch ev.Type {
	case kalshi.TypeOrderbookSnapshot, kalshi.TypeOrderbookDelta:
		e.mu.Lock()
		e.lastBookRx = ev.Rx
		e.mu.Unlock()
		if ev.Delta != nil && e.cfg.Paper != nil && !ev.Stale {
			side, err := book.ParseSide(ev.Delta.Side)
			price, err2 := book.ParsePrice(ev.Delta.PriceDollars)
			delta, err3 := book.ParseQty(ev.Delta.DeltaFP)
			if err == nil && err2 == nil && err3 == nil {
				before := book.Qty(0)
				if bv, ok := e.cfg.Feed.Book(m.Ticker); ok {
					for _, lv := range bv.Book.Bids(side) {
						if lv.Price == price {
							before = lv.Qty - delta // the book already has the delta applied
						}
					}
				}
				e.cfg.Paper.OnDelta(ev.Rx, m.Ticker, side, price, delta, ev.Delta.TsMs, before)
			}
		}
		e.decide(ctx, ev.Rx)
	case kalshi.TypeTrade:
		if ev.Trade != nil && e.cfg.Paper != nil {
			price, err := book.ParsePrice(ev.Trade.YesPriceDollars)
			qty, err2 := book.ParseQty(ev.Trade.CountFP)
			if err == nil && err2 == nil {
				e.cfg.Paper.OnTrade(ev.Rx, m.Ticker, price, qty, ev.Trade.TakerSide, ev.Trade.TsMs)
			}
		}
	}
}

func (e *Engine) applyLiveFill(l *Ledger, ev feed.Event) {
	f := ev.Fill
	o := l.byOrderID(f.OrderID)
	if o == nil {
		return
	}
	qty, err := book.ParseQty(f.CountFP)
	if err != nil {
		return
	}
	// fills always carry the YES price; a NO bid at p is a YES sale at 1-p
	yes, err := book.ParsePrice(f.YesPriceDollars)
	if err != nil {
		e.log.Warn("fill without yes price", "order", f.OrderID)
		return
	}
	price := yes
	if o.Side == book.No {
		price = book.OneDollar - yes
	}
	l.OnFill(f.TradeID, Fill{Rx: ev.Rx, Ticker: f.MarketTicker, OrderID: f.OrderID, Side: o.Side, Price: price, Qty: qty, Taker: f.IsTaker})
	e.mu.Lock()
	e.stats.Fills++
	e.fillCostSincePoll += Collateral(price, qty) // a fill turns reserved collateral into position cost
	e.mu.Unlock()
}

func (e *Engine) onQuote(ctx context.Context, q CoinbaseQuote) {
	e.spot.OnCoinbaseQuote(q.Rx, q.ExchTs, q.Bid, q.Ask, q.BidSz, q.AskSz)
	e.mu.Lock()
	m, l := e.market, e.ledger
	e.mu.Unlock()
	if m == nil || l == nil || e.risk.Halted() != "" {
		return
	}
	views, pos := l.Views()
	in := Inputs{Now: q.Rx, Pos: pos, Orders: views, CloseAt: m.CloseAt, Strike: m.Strike, Spot: e.spot, Edge: e.cfg.Edge}
	for _, a := range e.strat.OnSpotTick(in) {
		e.execute(ctx, l, a, q.Rx)
	}
}

func (e *Engine) onTick(ctx context.Context, now time.Time) {
	if e.cfg.Paper != nil {
		e.cfg.Paper.Tick(now)
	}
	e.mu.Lock()
	m, l := e.market, e.ledger
	lastBook, gap, started := e.lastBookRx, e.seqGap, e.started
	e.seqGap = false
	e.mu.Unlock()
	if m == nil || l == nil {
		return
	}
	// feeds that have not delivered anything yet are measured from startup, with a grace period to connect
	const startupGrace = 20 * time.Second
	bookAge := time.Duration(0)
	if !lastBook.IsZero() {
		bookAge = now.Sub(lastBook)
	} else if now.Sub(started) > startupGrace {
		bookAge = now.Sub(started)
	}
	spotAge := time.Duration(0)
	if e.spot.cbLastRx.IsZero() {
		if now.Sub(started) > startupGrace {
			spotAge = now.Sub(started)
		}
	} else {
		spotAge = e.spot.CoinbaseAge(now)
	}
	mid := book.Price(5000)
	if bv, ok := e.cfg.Feed.Book(m.Ticker); ok {
		if mm, ok := bv.Book.Top().Mid(); ok {
			mid = mm
		}
	}
	pos, _ := l.Position()
	h, p := e.risk.Check(now, pos, e.sessionPnL(l, mid), bookAge, spotAge, gap)
	if h != "" && e.halted == "" {
		e.halted = h
		e.log.Error("HALT", "reason", h)
		e.tape("halt", map[string]any{"reason": h})
		for _, side := range []book.Side{book.Yes, book.No} {
			e.execute(ctx, l, Action{Kind: Cancel, Side: side, Reason: "halt"}, now)
		}
	}
	e.mu.Lock()
	wasPaused := e.paused
	e.paused = p
	e.mu.Unlock()
	if p != "" && wasPaused == "" {
		e.log.Warn("PAUSE", "reason", p)
		e.tape("pause", map[string]any{"reason": p})
		for _, side := range []book.Side{book.Yes, book.No} {
			e.execute(ctx, l, Action{Kind: Cancel, Side: side, Reason: "pause"}, now)
		}
	} else if p == "" && wasPaused != "" {
		e.log.Info("RESUME")
		e.tape("resume", nil)
	}
	e.decide(ctx, now)
}

// decide runs the strategy against the current book and executes the actions.
func (e *Engine) decide(ctx context.Context, now time.Time) {
	e.mu.Lock()
	m, l, paused := e.market, e.ledger, e.paused
	e.mu.Unlock()
	if m == nil || l == nil || e.risk.Halted() != "" || paused != "" {
		return
	}
	bv, ok := e.cfg.Feed.Book(m.Ticker)
	if !ok {
		return
	}
	views, pos := l.Views()
	e.mu.Lock()
	for side := range e.inflight { // a place in flight counts as pending-new for the strategy
		if views[side] == nil {
			views[side] = &OrderView{Side: side, State: PendingNew, Price: -1}
		}
	}
	e.mu.Unlock()
	free, known := e.freeCollateral(l)
	in := Inputs{Now: now, Book: bv.Book, Stale: bv.Stale, Pos: pos, Orders: views, CloseAt: m.CloseAt, Strike: m.Strike, Spot: e.spot, Edge: e.cfg.Edge,
		Available: free, CapitalKnown: known}
	for _, a := range e.strat.Decide(in) {
		e.execute(ctx, l, a, now)
	}
	e.mu.Lock()
	if e.vetoes == nil || len(e.vetoes) != len(e.strat.Vetoes) {
		e.vetoes = map[string]int{}
	}
	for k, v := range e.strat.Vetoes {
		e.vetoes[k] = v
	}
	e.mu.Unlock()
}

// execute carries out one action without blocking the event loop.
func (e *Engine) execute(ctx context.Context, l *Ledger, a Action, now time.Time) {
	switch a.Kind {
	case Place:
		e.mu.Lock()
		if e.inflight[a.Side] {
			e.mu.Unlock()
			return
		}
		e.inflight[a.Side] = true
		e.stats.Placed++
		e.mu.Unlock()
		e.risk.RecordOrder(now)
		go func() {
			cctx, cancel := context.WithTimeout(ctx, 5*time.Second)
			defer cancel()
			err := l.Place(cctx, e.cfg.Exec, a.Side, a.Price, a.Qty, "q-"+uuid.NewString(), a.Reason, now)
			e.mu.Lock()
			delete(e.inflight, a.Side)
			e.mu.Unlock()
			if err != nil {
				switch {
				case strings.Contains(err.Error(), "insufficient_balance"):
					// our collateral estimate ran ahead of the exchange: stop sizing until the next poll
					e.mu.Lock()
					if e.available > 0 {
						e.available = 0
					}
					e.stats.Rejections++
					e.mu.Unlock()
					e.log.Warn("place rejected: insufficient balance", "side", a.Side)
				case strings.Contains(err.Error(), "rate limit"):
					e.mu.Lock()
					e.stats.Rejections++
					e.mu.Unlock()
				case strings.Contains(err.Error(), "invalid_order"):
					// post-only would have crossed: the book moved under the quote; the next book event re-decides
					e.mu.Lock()
					e.stats.Rejections++
					e.mu.Unlock()
				default:
					e.risk.RecordError()
					e.mu.Lock()
					e.stats.Errors++
					e.mu.Unlock()
					e.log.Warn("place failed", "side", a.Side, "err", err)
				}
				return
			}
			e.risk.RecordOK()
			e.afterAck(ctx)
		}()
	case Cancel:
		if l.Working(a.Side) == nil {
			return
		}
		e.mu.Lock()
		e.stats.Canceled++
		e.mu.Unlock()
		go func() {
			cctx, cancel := context.WithTimeout(ctx, 5*time.Second)
			defer cancel()
			err := l.Cancel(cctx, e.cfg.Exec, a.Side, a.Reason)
			if IsPendingNew(err) {
				e.mu.Lock()
				e.wantCancel[a.Side] = a.Reason
				e.mu.Unlock()
				return
			}
			if err != nil {
				e.risk.RecordError()
				e.mu.Lock()
				e.stats.Errors++
				e.mu.Unlock()
				e.log.Warn("cancel failed", "side", a.Side, "err", err)
				return
			}
			e.risk.RecordOK()
		}()
	}
}

// afterAck issues cancels that were requested while a place was unacknowledged.
func (e *Engine) afterAck(ctx context.Context) {
	e.mu.Lock()
	l := e.ledger
	pending := e.wantCancel
	e.wantCancel = map[book.Side]string{}
	e.mu.Unlock()
	for side, reason := range pending {
		if l != nil {
			e.execute(ctx, l, Action{Kind: Cancel, Side: side, Reason: reason}, time.Now())
		}
	}
}

// Stats returns a snapshot for the status endpoint.
func (e *Engine) Stats() Stats {
	e.mu.Lock()
	defer e.mu.Unlock()
	s := e.stats
	s.Mode = e.cfg.Mode
	s.Halted = e.risk.Halted()
	s.Paused = e.paused
	s.Vetoes = map[string]int{}
	for k, v := range e.vetoes {
		s.Vetoes[k] = v
	}
	s.Working = map[string]any{}
	if e.market != nil && e.ledger != nil {
		s.Market = e.market.Ticker
		pos, cash := e.ledger.Position()
		s.Pos, s.Cash = pos.String(), cash
		mid := book.Price(5000)
		if bv, ok := e.cfg.Feed.Book(e.market.Ticker); ok {
			if mm, ok := bv.Book.Top().Mid(); ok {
				mid = mm
			}
		}
		s.MarkPnL = e.ledger.MarkPnL(mid)
		e.mu.Unlock()
		s.SessionPnL = e.sessionPnL(e.ledger, mid)
		e.mu.Lock()
		s.Fills = len(e.ledger.Fills())
		views, _ := e.ledger.Views()
		for side, v := range views {
			w := map[string]any{"price": v.Price.String(), "qty": v.Qty.String(), "state": v.State.String()}
			if e.cfg.Paper != nil {
				if a, ok := e.cfg.Paper.Ahead(v.ID); ok {
					w["ahead"] = a
				}
			}
			s.Working[side.String()] = w
		}
		if !e.lastBookRx.IsZero() {
			s.BookAgeMs = float64(time.Since(e.lastBookRx).Microseconds()) / 1e3
		}
	}
	s.SpotLagMs = e.spot.CoinbaseLagMs()
	return s
}

func parseFloat(s string) (float64, error) {
	var v float64
	_, err := fmt.Sscanf(s, "%g", &v)
	return v, err
}
