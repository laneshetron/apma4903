package quoter

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/laneshetron/kalshi/internal/book"
)

func paperSetup(t *testing.T, levelQty int) (*PaperExecutor, *[]Fill, string) {
	t.Helper()
	b := mkBook(5000, levelQty*100, 4900, 100000)
	var fills []Fill
	p := NewPaperExecutor(0, 0, func(string) (*book.Book, bool) { return b, true }, func(_ string, f Fill) { fills = append(fills, f) })
	id, _, err := p.Place(context.Background(), "M", book.Yes, 5000, 100*100, "c1")
	if err != nil {
		t.Fatal(err)
	}
	if a, _ := p.Ahead(id); a != float64(levelQty) {
		t.Fatalf("ahead at placement = %v, want %v", a, levelQty)
	}
	return p, &fills, id
}

func TestPaperFillsAfterQueueAhead(t *testing.T) {
	p, fills, id := paperSetup(t, 300)
	now := time.Now()
	// taker sells 200 YES (buys NO) at 50c: consumes the 300 ahead of us partially
	p.OnTrade(now, "M", 5000, 200*100, "no", 1)
	if a, _ := p.Ahead(id); a != 100 {
		t.Fatalf("ahead after 200 traded = %v, want 100", a)
	}
	if len(*fills) != 0 {
		t.Fatalf("no fill yet, got %v", *fills)
	}
	// another 150: 100 clears the queue, 50 fills us
	p.OnTrade(now, "M", 5000, 150*100, "no", 2)
	if len(*fills) != 1 || (*fills)[0].Qty != 50*100 || (*fills)[0].Side != book.Yes || (*fills)[0].Price != 5000 {
		t.Fatalf("want a 50-lot fill, got %v", *fills)
	}
	// 80 more: 50 remaining fills, order done
	p.OnTrade(now, "M", 5000, 80*100, "no", 3)
	if len(*fills) != 2 || (*fills)[1].Qty != 50*100 {
		t.Fatalf("want the remaining 50, got %v", *fills)
	}
	if _, ok := p.Ahead(id); ok {
		t.Fatal("filled order should be gone")
	}
}

func TestPaperTradesOnOtherSideDoNotFill(t *testing.T) {
	p, fills, id := paperSetup(t, 0)
	now := time.Now()
	p.OnTrade(now, "M", 5000, 100*100, "yes", 1) // taker bought YES: hits NO bids at 50c, not our YES bid
	if len(*fills) != 0 {
		t.Fatalf("wrong side filled: %v", *fills)
	}
	p.OnTrade(now, "M", 4900, 100*100, "no", 2) // YES bids at 49c, not ours at 50c
	if len(*fills) != 0 {
		t.Fatalf("wrong price filled: %v", *fills)
	}
	if _, ok := p.Ahead(id); !ok {
		t.Fatal("order should still be live")
	}
}

func TestPaperCancelsAheadMoveUsUpProRata(t *testing.T) {
	p, _, id := paperSetup(t, 400)
	now := time.Now()
	// a -100 delta with no matching trade: after the grace period it counts as cancels ahead of us,
	// pro rata: we had 400 ahead of a 400 level -> 100 cancels remove 100 from ahead
	p.OnDelta(now, "M", book.Yes, 5000, -100*100, 5, 400*100)
	if a, _ := p.Ahead(id); a != 400 {
		t.Fatalf("pending delta must not apply immediately, ahead=%v", a)
	}
	p.OnDelta(now.Add(time.Second), "M", book.Yes, 5000, -1, 6, 300*100) // any later delta flushes the old one
	if a, _ := p.Ahead(id); a < 299 || a > 301 {
		t.Fatalf("ahead after 100 cancels = %v, want ~300", a)
	}
}

func TestPaperTradeExplainsDelta(t *testing.T) {
	p, fills, id := paperSetup(t, 100)
	now := time.Now()
	// the exchange emits the negative delta and the trade with the same ts: not a cancel
	p.OnDelta(now, "M", book.Yes, 5000, -60*100, 7, 100*100)
	p.OnTrade(now, "M", 5000, 60*100, "no", 7)
	if a, _ := p.Ahead(id); a != 40 {
		t.Fatalf("ahead = %v, want 40 (trade consumed 60)", a)
	}
	p.OnDelta(now.Add(2*time.Second), "M", book.Yes, 5000, -1, 8, 40*100) // flush: nothing pending should remain as cancels
	if a, _ := p.Ahead(id); a < 39.5 {
		t.Fatalf("explained delta must not also count as cancels, ahead=%v", a)
	}
	if len(*fills) != 0 {
		t.Fatalf("no fill expected, got %v", *fills)
	}
}

func TestPaperCancelRemovesOrder(t *testing.T) {
	p, fills, id := paperSetup(t, 0)
	now := time.Now()
	if _, err := p.Cancel(context.Background(), "M", id); err != nil {
		t.Fatal(err)
	}
	p.OnTrade(now, "M", 5000, 100*100, "no", 1)
	if len(*fills) != 0 {
		t.Fatal("canceled order must not fill")
	}
	if _, err := p.Cancel(context.Background(), "M", id); !errors.Is(err, ErrOrderDone) {
		t.Fatalf("double cancel should report ErrOrderDone, got %v", err)
	}
}

func TestPaperLatencyIsHonoured(t *testing.T) {
	b := mkBook(5000, 1000, 4900, 1000)
	p := NewPaperExecutor(30*time.Millisecond, 10*time.Millisecond, func(string) (*book.Book, bool) { return b, true }, nil)
	start := time.Now()
	id, _, _ := p.Place(context.Background(), "M", book.Yes, 5000, 100, "c")
	if d := time.Since(start); d < 30*time.Millisecond {
		t.Fatalf("place returned after %v, want >= 30ms", d)
	}
	start = time.Now()
	_, _ = p.Cancel(context.Background(), "M", id)
	if d := time.Since(start); d < 10*time.Millisecond {
		t.Fatalf("cancel returned after %v, want >= 10ms", d)
	}
}

func TestPaperFillIDsAreUniqueWithinOneMillisecond(t *testing.T) {
	b := mkBook(5000, 0, 4900, 1000)
	var ids []string
	p := NewPaperExecutor(0, 0, func(string) (*book.Book, bool) { return b, true }, func(id string, _ Fill) { ids = append(ids, id) })
	_, _, _ = p.Place(context.Background(), "M", book.Yes, 5000, 100*100, "c")
	now := time.Now()
	p.OnTrade(now, "M", 5000, 10*100, "no", 42) // two trades with the same exchange ts (one sweep)
	p.OnTrade(now, "M", 5000, 10*100, "no", 42)
	if len(ids) != 2 || ids[0] == ids[1] {
		t.Fatalf("fill ids must be unique across trades sharing ts_ms, got %v", ids)
	}
}

func TestPaperFeedLagOrdersAheadAndTradesBeforeCancel(t *testing.T) {
	b := mkBook(5000, 100*100, 4900, 1000)
	var fills []Fill
	p := NewPaperExecutor(0, 0, func(string) (*book.Book, bool) { return b, true }, func(_ string, f Fill) { fills = append(fills, f) })
	p.FeedLag = 7 * time.Millisecond
	id, live, _ := p.Place(context.Background(), "M", book.Yes, 5000, 100*100, "c")
	// an add at our level seen 3ms after we went live reached the engine before us: it is ahead
	p.OnDelta(live.Add(3*time.Millisecond), "M", book.Yes, 5000, 50*100, 1, 100*100)
	if a, _ := p.Ahead(id); a != 150 {
		t.Fatalf("ahead = %v, want 150 (100 at placement + 50 seen within the feed lag)", a)
	}
	// an add seen after the lag window joined behind us
	p.OnDelta(live.Add(20*time.Millisecond), "M", book.Yes, 5000, 50*100, 2, 150*100)
	if a, _ := p.Ahead(id); a != 150 {
		t.Fatalf("ahead = %v, want 150 (later adds are behind us)", a)
	}
	// a trade we see 2ms after going live happened before we were live: no fill for us
	p.OnTrade(live.Add(2*time.Millisecond), "M", 5000, 160*100, "no", 3)
	if len(fills) != 0 {
		t.Fatalf("trade from before we were live must not fill us: %v", fills)
	}
	if a, _ := p.Ahead(id); a != 150 {
		t.Fatalf("queue untouched by a pre-live trade, ahead=%v", a)
	}
	// cancel: a trade seen 4ms after the cancel took effect happened 3ms before it -> still fills us
	time.Sleep(20 * time.Millisecond) // so the cancel is clearly after we went live
	cancelAt, _ := p.Cancel(context.Background(), "M", id)
	p.OnTrade(cancelAt.Add(4*time.Millisecond), "M", 5000, 160*100, "no", 4)
	if len(fills) != 1 || fills[0].Qty != 10*100 {
		t.Fatalf("trade from before the cancel should fill 10, got %v", fills)
	}
	// a trade seen well after the cancel does not
	p.OnTrade(cancelAt.Add(20*time.Millisecond), "M", 5000, 160*100, "no", 5)
	if len(fills) != 1 {
		t.Fatalf("post-cancel trade must not fill: %v", fills)
	}
}

func TestPaperTakeFillsAtPriceWithFee(t *testing.T) {
	b := mkBook(5000, 1000, 4900, 1000)
	var fills []Fill
	p := NewPaperExecutor(0, 0, func(string) (*book.Book, bool) { return b, true }, func(_ string, f Fill) { fills = append(fills, f) })
	// sell 60 YES into the 50c bid
	if _, _, err := p.Take(context.Background(), "M", book.No, 5000, 60*100, "t1"); err != nil {
		t.Fatal(err)
	}
	if len(fills) != 1 || fills[0].Side != book.No || fills[0].Price != 5000 || fills[0].Qty != 60*100 || !fills[0].Taker {
		t.Fatalf("bad take fill %+v", fills)
	}
	want := 0.07 * 0.5 * 0.5 * 60 // fee at p=0.5 on 60 contracts = $1.05
	if f := fills[0].Fee; f < want-1e-9 || f > want+1e-9 {
		t.Fatalf("fee %v, want %v", f, want)
	}
	l := NewLedger("M", nil)
	l.OnFill("f1", fills[0])
	pos, cash := l.Position()
	if pos != -60*100 || cash < 30-1.05-1e-9 || cash > 30-1.05+1e-9 {
		t.Fatalf("selling 60 YES at 50c less the fee: pos %v cash %v", pos, cash)
	}
}
