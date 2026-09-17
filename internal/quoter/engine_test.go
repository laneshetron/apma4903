package quoter

import (
	"context"
	"fmt"
	"sync"
	"testing"
	"time"

	"github.com/laneshetron/kalshi/internal/book"
	"github.com/laneshetron/kalshi/internal/feed"
	"github.com/laneshetron/kalshi/internal/kalshi"
)

// fakeSource is a BookSource with a settable book.
type fakeSource struct {
	mu      sync.Mutex
	books   map[string]*book.Book
	markets []string
}

func (f *fakeSource) Book(t string) (feed.BookView, bool) {
	f.mu.Lock()
	defer f.mu.Unlock()
	b, ok := f.books[t]
	if !ok {
		return feed.BookView{}, false
	}
	return feed.BookView{Ticker: t, Book: b.Clone(), LastRx: time.Now()}, true
}

func (f *fakeSource) SetMarkets(_ context.Context, ts []string) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.markets = ts
	return nil
}

func (f *fakeSource) set(t string, b *book.Book) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.books[t] = b
}

func waitFor(t *testing.T, what string, cond func() bool) {
	t.Helper()
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		if cond() {
			return
		}
		time.Sleep(5 * time.Millisecond)
	}
	t.Fatalf("timeout waiting for %s", what)
}

// testLimits are DefaultLimits without the Coinbase-silence stop (tests feed no spot quotes).
func testLimits() Limits {
	l := DefaultLimits()
	l.MaxSpotAge = time.Hour
	return l
}

func newTestEngine(t *testing.T, src *fakeSource, mkt *Market, limits Limits) (*Engine, *PaperExecutor, context.CancelFunc) {
	t.Helper()
	var eng *Engine
	paper := NewPaperExecutor(0, 0, func(tk string) (*book.Book, bool) {
		bv, ok := src.Book(tk)
		return bv.Book, ok
	}, func(id string, f Fill) { eng.PaperFill(id, f) })
	var mu sync.Mutex
	cur := mkt
	eng = NewEngine(EngineConfig{
		Params: Params{Size: 100 * 100, MaxPos: 200 * 100, StopBefore: 5 * time.Minute, SignalMove: 2},
		Limits: limits, Mode: "paper", Exec: paper, Paper: paper, Feed: src, Capital: -1,
		PickMarket: func(context.Context) (*Market, error) { mu.Lock(); defer mu.Unlock(); return cur, nil },
	})
	ctx, cancel := context.WithCancel(context.Background())
	go func() { _ = eng.Run(ctx) }()
	return eng, paper, cancel
}

func delta(tk string, side book.Side, price book.Price, d book.Qty, ts int64) feed.Event {
	return feed.Event{Rx: time.Now(), Type: kalshi.TypeOrderbookDelta, Ticker: tk,
		Delta: &kalshi.OrderbookDeltaMsg{MarketTicker: tk, Side: side.String(), PriceDollars: price.String(), DeltaFP: d.String(), TsMs: ts}}
}

func trade(tk string, yesPrice book.Price, qty book.Qty, taker string, ts int64) feed.Event {
	return feed.Event{Rx: time.Now(), Type: kalshi.TypeTrade, Ticker: tk,
		Trade: &kalshi.TradeMsg{MarketTicker: tk, YesPriceDollars: yesPrice.String(), CountFP: qty.String(), TakerSide: taker, TsMs: ts}}
}

func TestEngineQuotesFillsAndTracksPosition(t *testing.T) {
	tk := "KXBTC15M-TEST"
	src := &fakeSource{books: map[string]*book.Book{tk: mkBook(5000, 300*100, 4900, 300*100)}}
	mkt := &Market{Ticker: tk, Strike: 76000, CloseAt: time.Now().Add(10 * time.Minute)}
	eng, _, cancel := newTestEngine(t, src, mkt, testLimits())
	defer cancel()

	// a book event triggers a decision: both sides get quoted at the touch
	eng.OnFeedEvent(delta(tk, book.Yes, 5000, 100, 1))
	waitFor(t, "two working orders", func() bool { s := eng.Stats(); return len(s.Working) == 2 })
	s := eng.Stats()
	if s.Working["yes"].(map[string]any)["price"] != "0.5000" || s.Working["no"].(map[string]any)["price"] != "0.4900" {
		t.Fatalf("unexpected quotes: %+v", s.Working)
	}
	if a := s.Working["yes"].(map[string]any)["ahead"]; a != 300.0 {
		t.Fatalf("paper queue position should be the level size, got %v", a)
	}

	// takers sell 350 YES at 50c: 300 ahead of us fill first, then 50 of ours
	eng.OnFeedEvent(trade(tk, 5000, 350*100, "no", 2))
	waitFor(t, "a fill", func() bool { return eng.Stats().Fills == 1 })
	s = eng.Stats()
	if s.Pos != "50.00" {
		t.Fatalf("position after fill = %s, want 50.00", s.Pos)
	}
	if s.Cash > -24.99 || s.Cash < -25.01 {
		t.Fatalf("cash after buying 50 at 50c = %v, want -25", s.Cash)
	}
	// the YES order still has 50 resting
	if q := s.Working["yes"].(map[string]any)["qty"]; q != "50.00" {
		t.Fatalf("remaining qty %v, want 50.00", q)
	}
	// tape/stats: one place per side, no errors
	if s.Placed != 2 || s.Errors != 0 {
		t.Fatalf("placed %d errors %d", s.Placed, s.Errors)
	}
}

func TestEngineRepricesWhenTouchMoves(t *testing.T) {
	tk := "KXBTC15M-TEST"
	src := &fakeSource{books: map[string]*book.Book{tk: mkBook(5000, 300*100, 4900, 300*100)}}
	mkt := &Market{Ticker: tk, Strike: 76000, CloseAt: time.Now().Add(10 * time.Minute)}
	eng, _, cancel := newTestEngine(t, src, mkt, testLimits())
	defer cancel()
	eng.OnFeedEvent(delta(tk, book.Yes, 5000, 100, 1))
	waitFor(t, "quotes", func() bool { return len(eng.Stats().Working) == 2 })
	// the touch drops to 49c bid / 50c ask (NO bid 50c): our 50c YES bid must be cancelled and re-placed at 49c
	src.set(tk, mkBook(4900, 300*100, 5000, 300*100))
	eng.OnFeedEvent(delta(tk, book.Yes, 5000, -300*100, 2))
	waitFor(t, "reprice", func() bool {
		w := eng.Stats().Working["yes"]
		return w != nil && w.(map[string]any)["price"] == "0.4900" && w.(map[string]any)["state"] == "resting"
	})
	if s := eng.Stats(); s.Canceled < 1 || s.Placed < 3 {
		t.Fatalf("expected a cancel and a re-place, got placed %d canceled %d", s.Placed, s.Canceled)
	}
}

func TestEngineHaltsOnLimitAndCancelsEverything(t *testing.T) {
	tk := "KXBTC15M-TEST"
	src := &fakeSource{books: map[string]*book.Book{tk: mkBook(5000, 100, 4900, 300*100)}} // one contract ahead on YES
	mkt := &Market{Ticker: tk, Strike: 76000, CloseAt: time.Now().Add(10 * time.Minute)}
	lim := testLimits()
	lim.MaxAbsPos = 60 * 100 // a 100-lot fill breaches it
	eng, _, cancel := newTestEngine(t, src, mkt, lim)
	defer cancel()
	eng.OnFeedEvent(delta(tk, book.No, 4900, 100, 1))
	waitFor(t, "quotes", func() bool { return len(eng.Stats().Working) == 2 })
	eng.OnFeedEvent(trade(tk, 5000, 101*100, "no", 2)) // 1 ahead, then our whole YES bid: pos 100 > 60
	waitFor(t, "halt", func() bool { return eng.Stats().Halted != "" })
	waitFor(t, "orders cancelled", func() bool { return len(eng.Stats().Working) == 0 })
	// after a halt no new quotes appear
	eng.OnFeedEvent(delta(tk, book.No, 4900, 100, 3))
	time.Sleep(150 * time.Millisecond)
	if s := eng.Stats(); len(s.Working) != 0 {
		t.Fatalf("halted engine placed orders: %+v", s.Working)
	}
}

func TestEnginePausesWhenBookGoesSilentAndResumes(t *testing.T) {
	tk := "KXBTC15M-TEST"
	src := &fakeSource{books: map[string]*book.Book{tk: mkBook(5000, 100, 4900, 100)}}
	mkt := &Market{Ticker: tk, Strike: 76000, CloseAt: time.Now().Add(10 * time.Minute)}
	lim := testLimits()
	lim.MaxBookAge = 200 * time.Millisecond
	eng, _, cancel := newTestEngine(t, src, mkt, lim)
	defer cancel()
	eng.OnFeedEvent(delta(tk, book.Yes, 5000, 100, 1))
	waitFor(t, "quotes", func() bool { return len(eng.Stats().Working) == 2 })
	waitFor(t, "silence pause", func() bool { return eng.Stats().Paused != "" })
	waitFor(t, "orders cancelled", func() bool { return len(eng.Stats().Working) == 0 })
	if eng.Stats().Halted != "" {
		t.Fatal("silence must pause, not halt")
	}
	// the book comes back: quoting resumes on its own
	eng.OnFeedEvent(delta(tk, book.Yes, 5000, 100, 2))
	waitFor(t, "resume", func() bool { s := eng.Stats(); return s.Paused == "" && len(s.Working) == 2 })
}

func TestEngineRollsMarketAndCancelsOld(t *testing.T) {
	a, b := "KXBTC15M-A", "KXBTC15M-B"
	src := &fakeSource{books: map[string]*book.Book{a: mkBook(5000, 100, 4900, 100), b: mkBook(6000, 100, 3900, 100)}}
	var mu sync.Mutex
	cur := &Market{Ticker: a, Strike: 76000, CloseAt: time.Now().Add(10 * time.Minute)}
	var eng *Engine
	paper := NewPaperExecutor(0, 0, func(tk string) (*book.Book, bool) { bv, ok := src.Book(tk); return bv.Book, ok }, func(id string, f Fill) { eng.PaperFill(id, f) })
	lim := testLimits()
	eng = NewEngine(EngineConfig{
		Params: Params{Size: 100 * 100, MaxPos: 200 * 100, StopBefore: 5 * time.Minute}, Limits: lim, Mode: "paper", Exec: paper, Paper: paper, Feed: src, Capital: -1,
		PickMarket: func(context.Context) (*Market, error) { mu.Lock(); defer mu.Unlock(); return cur, nil },
	})
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go func() { _ = eng.Run(ctx) }()
	eng.OnFeedEvent(delta(a, book.Yes, 5000, 100, 1))
	waitFor(t, "quotes on A", func() bool { s := eng.Stats(); return s.Market == a && len(s.Working) == 2 })
	mu.Lock()
	cur = &Market{Ticker: b, Strike: 76500, CloseAt: time.Now().Add(20 * time.Minute)}
	mu.Unlock()
	eng.rollMarket(ctx)
	waitFor(t, "switched to B", func() bool { return eng.Stats().Market == b })
	// old orders were cancelled on the paper executor; B gets fresh quotes on its own touch
	eng.OnFeedEvent(delta(b, book.Yes, 6000, 100, 2))
	waitFor(t, "quotes on B", func() bool {
		s := eng.Stats()
		w := s.Working["yes"]
		return len(s.Working) == 2 && w.(map[string]any)["price"] == "0.6000"
	})
	if src.markets[0] != b {
		t.Fatalf("feed should be subscribed to %s, got %v", b, src.markets)
	}
}

func TestEngineNeedsCoinbaseBeforeQuoting(t *testing.T) {
	tk := "KXBTC15M-TEST"
	src := &fakeSource{books: map[string]*book.Book{tk: mkBook(5000, 100, 4900, 100)}}
	mkt := &Market{Ticker: tk, Strike: 76000, CloseAt: time.Now().Add(10 * time.Minute)}
	lim := DefaultLimits()
	lim.MaxSpotAge = 100 * time.Millisecond
	eng, _, cancel := newTestEngine(t, src, mkt, lim)
	defer cancel()
	// one quote, then silence beyond the limit: pause
	eng.Quotes() <- CoinbaseQuote{Rx: time.Now(), Bid: 76000, Ask: 76001}
	waitFor(t, "spot-silence pause", func() bool { return eng.Stats().Paused != "" })
}

func TestEngineSignalCancelsStaleSide(t *testing.T) {
	tk := "KXBTC15M-TEST"
	src := &fakeSource{books: map[string]*book.Book{tk: mkBook(5000, 300*100, 4900, 300*100)}}
	mkt := &Market{Ticker: tk, Strike: 76000, CloseAt: time.Now().Add(10 * time.Minute)}
	eng, _, cancel := newTestEngine(t, src, mkt, testLimits())
	defer cancel()
	now := time.Now()
	eng.Quotes() <- CoinbaseQuote{Rx: now.Add(-500 * time.Millisecond), Bid: 76000, Ask: 76001, BidSz: 1, AskSz: 1}
	eng.OnFeedEvent(delta(tk, book.Yes, 5000, 100, 1))
	waitFor(t, "quotes", func() bool { return len(eng.Stats().Working) == 2 })
	eng.Quotes() <- CoinbaseQuote{Rx: now, Bid: 76005, Ask: 76006, BidSz: 1, AskSz: 1} // +$5: our NO bid (YES ask) is stale
	waitFor(t, "NO side pulled", func() bool { w := eng.Stats().Working; return w["no"] == nil && w["yes"] != nil })
}

func TestEngineSizesToPaperCapital(t *testing.T) {
	tk := "KXBTC15M-TEST"
	src := &fakeSource{books: map[string]*book.Book{tk: mkBook(5000, 300*100, 4900, 300*100)}}
	var eng *Engine
	paper := NewPaperExecutor(0, 0, func(tk string) (*book.Book, bool) { bv, ok := src.Book(tk); return bv.Book, ok }, func(id string, f Fill) { eng.PaperFill(id, f) })
	eng = NewEngine(EngineConfig{
		Params: Params{Size: 100 * 100, MaxPos: 200 * 100, StopBefore: 5 * time.Minute}, Limits: testLimits(), Mode: "paper", Exec: paper, Paper: paper, Feed: src,
		Capital: 5.0, // $5: $2.50 per side -> 5 YES at 50c, 5 NO at 49c
		PickMarket: func(context.Context) (*Market, error) {
			return &Market{Ticker: tk, Strike: 76000, CloseAt: time.Now().Add(10 * time.Minute)}, nil
		},
	})
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go func() { _ = eng.Run(ctx) }()
	eng.OnFeedEvent(delta(tk, book.Yes, 5000, 100, 1))
	waitFor(t, "sized quotes", func() bool {
		w := eng.Stats().Working
		return len(w) == 2 && w["yes"].(map[string]any)["qty"] == "5.00" && w["no"].(map[string]any)["qty"] == "5.00"
	})
}

func TestEngineLiveFillUsesYesPriceForNoOrders(t *testing.T) {
	tk := "KXBTC15M-TEST"
	src := &fakeSource{books: map[string]*book.Book{tk: mkBook(5000, 300*100, 2700, 300*100)}}
	ex := &fakeExec{}
	var eng *Engine
	eng = NewEngine(EngineConfig{
		Params: Params{Size: 5 * 100, MaxPos: 10 * 100, StopBefore: 5 * time.Minute}, Limits: testLimits(), Mode: "live", Exec: ex, Feed: src, Capital: -1,
		PickMarket: func(context.Context) (*Market, error) {
			return &Market{Ticker: tk, Strike: 76000, CloseAt: time.Now().Add(10 * time.Minute)}, nil
		},
	})
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go func() { _ = eng.Run(ctx) }()
	eng.OnFeedEvent(delta(tk, book.Yes, 5000, 100, 1))
	waitFor(t, "quotes", func() bool { return len(eng.Stats().Working) == 2 })
	no := eng.ledger.Working(book.No)
	// a taker buys YES at 0.73: our NO bid at 0.27 is filled; the fill message carries the YES price only
	eng.OnFeedEvent(feed.Event{Rx: time.Now(), Type: kalshi.TypeFill, Ticker: tk,
		Fill: &kalshi.FillMsg{TradeID: "t1", OrderID: no.ID, MarketTicker: tk, Side: "yes", YesPriceDollars: "0.7300", CountFP: "5.00", Action: "sell"}})
	waitFor(t, "fill applied", func() bool { return eng.Stats().Fills == 1 })
	s := eng.Stats()
	if s.Pos != "-5.00" || s.Cash < 3.64 || s.Cash > 3.66 {
		t.Fatalf("selling 5 YES at 0.73 should give pos -5 and cash +3.65, got pos %s cash %v", s.Pos, s.Cash)
	}
}

type rejectingExec struct {
	fakeExec
	msg string
}

func (r *rejectingExec) Place(context.Context, string, book.Side, book.Price, book.Qty, string) (string, time.Time, error) {
	return "", time.Time{}, fmt.Errorf("create order: HTTP 400 {\"error\":{\"code\":\"%s\"}}", r.msg)
}

func TestEngineBalanceRejectionDoesNotHalt(t *testing.T) {
	tk := "KXBTC15M-TEST"
	src := &fakeSource{books: map[string]*book.Book{tk: mkBook(5000, 300*100, 4900, 300*100)}}
	ex := &rejectingExec{msg: "insufficient_balance"}
	eng := NewEngine(EngineConfig{
		Params: Params{Size: 5 * 100, MaxPos: 10 * 100, StopBefore: 5 * time.Minute}, Limits: testLimits(), Mode: "live", Exec: ex, Feed: src,
		Balance: func(context.Context) (float64, error) { return 5, nil },
		PickMarket: func(context.Context) (*Market, error) {
			return &Market{Ticker: tk, Strike: 76000, CloseAt: time.Now().Add(10 * time.Minute)}, nil
		},
	})
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go func() { _ = eng.Run(ctx) }()
	for i := 0; i < 12; i++ {
		eng.OnFeedEvent(delta(tk, book.Yes, 5000, 100, int64(i)))
		time.Sleep(20 * time.Millisecond)
	}
	s := eng.Stats()
	if s.Halted != "" {
		t.Fatalf("insufficient balance must not halt, got %q", s.Halted)
	}
	if s.Rejections == 0 || s.Errors != 0 {
		t.Fatalf("rejections %d errors %d", s.Rejections, s.Errors)
	}
	if s.Available != 5 {
		t.Fatalf("polled balance should be reported, got %v", s.Available)
	}
}
