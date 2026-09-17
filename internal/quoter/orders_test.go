package quoter

import (
	"context"
	"errors"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/laneshetron/kalshi/internal/book"
)

// fakeExec records calls and returns scripted results.
type fakeExec struct {
	mu        sync.Mutex
	placed    []string
	canceled  []string
	rejectAll bool
	block     chan struct{} // if set, Place blocks until closed
	nextID    int
}

func (f *fakeExec) Place(_ context.Context, _ string, _ book.Side, _ book.Price, _ book.Qty, clientID string) (string, time.Time, error) {
	if f.block != nil {
		<-f.block
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	if f.rejectAll {
		return "", time.Time{}, errors.New("insufficient balance")
	}
	f.nextID++
	id := "ord-" + strings.TrimPrefix(clientID, "c-")
	f.placed = append(f.placed, id)
	return id, time.Now(), nil
}

func (f *fakeExec) Cancel(_ context.Context, _ string, orderID string) (time.Time, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.canceled = append(f.canceled, orderID)
	return time.Now(), nil
}

func TestLedgerPlaceCancelLifecycle(t *testing.T) {
	ex := &fakeExec{}
	var events []string
	l := NewLedger("M", func(k string, _ map[string]any) { events = append(events, k) })
	ctx := context.Background()
	if err := l.Place(ctx, ex, book.Yes, 5000, 10000, "c-1", "join", t0); err != nil {
		t.Fatal(err)
	}
	v, pos := l.Views()
	if pos != 0 || v[book.Yes] == nil || v[book.Yes].State != Resting || v[book.Yes].ID != "ord-1" {
		t.Fatalf("after place: %+v pos %v", v[book.Yes], pos)
	}
	if err := l.Place(ctx, ex, book.Yes, 5000, 10000, "c-2", "join", t0); err == nil {
		t.Fatal("second order on the same side must be refused")
	}
	if err := l.Cancel(ctx, ex, book.Yes, "reprice"); err != nil {
		t.Fatal(err)
	}
	v, _ = l.Views()
	if v[book.Yes] != nil {
		t.Fatalf("side should be free after cancel ack, got %+v", v[book.Yes])
	}
	if len(ex.canceled) != 1 || ex.canceled[0] != "ord-1" {
		t.Fatalf("cancel not sent: %v", ex.canceled)
	}
	want := "place place_ack cancel cancel_ack done"
	if got := strings.Join(events, " "); got != want {
		t.Fatalf("events %q, want %q", got, want)
	}
}

func TestLedgerRejectionFreesSide(t *testing.T) {
	ex := &fakeExec{rejectAll: true}
	l := NewLedger("M", nil)
	if err := l.Place(context.Background(), ex, book.No, 4900, 10000, "c-1", "join", t0); err == nil {
		t.Fatal("expected rejection")
	}
	if v, _ := l.Views(); v[book.No] != nil {
		t.Fatal("rejected order must not occupy the side")
	}
}

func TestLedgerCancelWhilePendingNewIsDeferred(t *testing.T) {
	ex := &fakeExec{block: make(chan struct{})}
	l := NewLedger("M", nil)
	done := make(chan error, 1)
	go func() { done <- l.Place(context.Background(), ex, book.Yes, 5000, 10000, "c-1", "join", t0) }()
	time.Sleep(20 * time.Millisecond)
	v, _ := l.Views()
	if v[book.Yes] == nil || v[book.Yes].State != PendingNew {
		t.Fatalf("expected pending_new, got %+v", v[book.Yes])
	}
	if err := l.Cancel(context.Background(), ex, book.Yes, "signal"); !IsPendingNew(err) {
		t.Fatalf("cancel before ack should report pending-new, got %v", err)
	}
	close(ex.block)
	if err := <-done; err != nil {
		t.Fatal(err)
	}
	if err := l.Cancel(context.Background(), ex, book.Yes, "signal"); err != nil {
		t.Fatal(err)
	}
	if v, _ := l.Views(); v[book.Yes] != nil {
		t.Fatal("side should be free")
	}
}

func TestLedgerFillsAndPosition(t *testing.T) {
	ex := &fakeExec{}
	l := NewLedger("M", nil)
	ctx := context.Background()
	_ = l.Place(ctx, ex, book.Yes, 5000, 10000, "c-1", "join", t0) // ord-1: buy 100 YES at 50c
	_ = l.Place(ctx, ex, book.No, 4900, 10000, "c-2", "join", t0)  // ord-2: buy 100 NO at 49c == sell YES at 51c
	l.OnFill("f1", Fill{OrderID: "ord-1", Side: book.Yes, Price: 5000, Qty: 4000})
	l.OnFill("f1", Fill{OrderID: "ord-1", Side: book.Yes, Price: 5000, Qty: 4000}) // duplicate ignored
	pos, cash := l.Position()
	if pos != 4000 || cash != -20.0 {
		t.Fatalf("after partial YES fill: pos %v cash %v", pos, cash)
	}
	v, _ := l.Views()
	if v[book.Yes].Qty != 6000 || v[book.Yes].State != Resting {
		t.Fatalf("partial fill should leave 60 resting, got %+v", v[book.Yes])
	}
	l.OnFill("f2", Fill{OrderID: "ord-2", Side: book.No, Price: 4900, Qty: 10000})
	pos, cash = l.Position()
	if pos != -6000 || cash != -20.0+51.0 {
		t.Fatalf("after full NO fill: pos %v cash %v", pos, cash)
	}
	if v, _ := l.Views(); v[book.No] != nil {
		t.Fatal("fully filled order must leave the side")
	}
	// mark: -60 YES at mid 50c => cash 31 - 30 = +1
	if pnl := l.MarkPnL(5000); pnl < 0.99 || pnl > 1.01 {
		t.Fatalf("mark pnl %v", pnl)
	}
	// net short 60: the 40 YES/NO pairs are settled by the exchange; collateral held is 60 NO at 49c = $29.40
	if c := l.CollateralUsed(); c < 29.39 || c > 29.41 {
		t.Fatalf("collateral used %v, want 29.40", c)
	}
}

func TestLedgerOrderUpdatesFromStream(t *testing.T) {
	ex := &fakeExec{}
	l := NewLedger("M", nil)
	_ = l.Place(context.Background(), ex, book.Yes, 5000, 10000, "c-1", "join", t0)
	l.OnOrderUpdate("ord-1", "c-1", "canceled", 0) // e.g. exchange-side cancel on pause
	if v, _ := l.Views(); v[book.Yes] != nil {
		t.Fatal("stream cancel must free the side")
	}
	l.OnOrderUpdate("unknown", "", "resting", 10000)  // ignored
	l.OnOrderUpdate("ord-1", "c-1", "resting", 10000) // late/dup: stays done
	if v, _ := l.Views(); v[book.Yes] != nil {
		t.Fatal("done orders do not resurrect")
	}
}

type doneExec struct{ fakeExec }

func (d *doneExec) Cancel(context.Context, string, string) (time.Time, error) {
	return time.Time{}, ErrOrderDone
}

func TestLedgerCancelOfFinishedOrderFreesSide(t *testing.T) {
	ex := &doneExec{}
	l := NewLedger("M", nil)
	_ = l.Place(context.Background(), ex, book.Yes, 5000, 10000, "c-1", "join", t0)
	if err := l.Cancel(context.Background(), ex, book.Yes, "reprice"); err != nil {
		t.Fatalf("ErrOrderDone should not surface as an error: %v", err)
	}
	if v, _ := l.Views(); v[book.Yes] != nil {
		t.Fatal("an already-done order must free the side")
	}
}
