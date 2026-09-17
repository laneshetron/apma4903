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
	now := t0
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
	p.OnTrade(t0, "M", 5000, 100*100, "yes", 1) // taker bought YES: hits NO bids at 50c, not our YES bid
	if len(*fills) != 0 {
		t.Fatalf("wrong side filled: %v", *fills)
	}
	p.OnTrade(t0, "M", 4900, 100*100, "no", 2) // YES bids at 49c, not ours at 50c
	if len(*fills) != 0 {
		t.Fatalf("wrong price filled: %v", *fills)
	}
	if _, ok := p.Ahead(id); !ok {
		t.Fatal("order should still be live")
	}
}

func TestPaperCancelsAheadMoveUsUpProRata(t *testing.T) {
	p, _, id := paperSetup(t, 400)
	// a -100 delta with no matching trade: after the grace period it counts as cancels ahead of us,
	// pro rata: we had 400 ahead of a 400 level -> 100 cancels remove 100 from ahead
	p.OnDelta(t0, "M", book.Yes, 5000, -100*100, 5, 400*100)
	if a, _ := p.Ahead(id); a != 400 {
		t.Fatalf("pending delta must not apply immediately, ahead=%v", a)
	}
	p.OnDelta(t0.Add(time.Second), "M", book.Yes, 5000, -1, 6, 300*100) // any later delta flushes the old one
	if a, _ := p.Ahead(id); a < 299 || a > 301 {
		t.Fatalf("ahead after 100 cancels = %v, want ~300", a)
	}
}

func TestPaperTradeExplainsDelta(t *testing.T) {
	p, fills, id := paperSetup(t, 100)
	// the exchange emits the negative delta and the trade with the same ts: not a cancel
	p.OnDelta(t0, "M", book.Yes, 5000, -60*100, 7, 100*100)
	p.OnTrade(t0, "M", 5000, 60*100, "no", 7)
	if a, _ := p.Ahead(id); a != 40 {
		t.Fatalf("ahead = %v, want 40 (trade consumed 60)", a)
	}
	p.OnDelta(t0.Add(2*time.Second), "M", book.Yes, 5000, -1, 8, 40*100) // flush: nothing pending should remain as cancels
	if a, _ := p.Ahead(id); a < 39.5 {
		t.Fatalf("explained delta must not also count as cancels, ahead=%v", a)
	}
	if len(*fills) != 0 {
		t.Fatalf("no fill expected, got %v", *fills)
	}
}

func TestPaperCancelRemovesOrder(t *testing.T) {
	p, fills, id := paperSetup(t, 0)
	if _, err := p.Cancel(context.Background(), "M", id); err != nil {
		t.Fatal(err)
	}
	p.OnTrade(t0, "M", 5000, 100*100, "no", 1)
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
	p.OnTrade(t0, "M", 5000, 10*100, "no", 42) // two trades with the same exchange ts (one sweep)
	p.OnTrade(t0, "M", 5000, 10*100, "no", 42)
	if len(ids) != 2 || ids[0] == ids[1] {
		t.Fatalf("fill ids must be unique across trades sharing ts_ms, got %v", ids)
	}
}
