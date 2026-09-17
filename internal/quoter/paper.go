package quoter

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/laneshetron/kalshi/internal/book"
)

// PaperExecutor simulates order entry against the live public book with the
// sim's pro-rata queue model: an order joins behind the level's resting
// quantity, moves up as trades consume the level and as other orders cancel
// (cancels are assumed spread evenly through the queue), and fills when
// trades reach it. Place/Cancel block for the configured latencies so the
// caller experiences the same timing as the live executor.
type PaperExecutor struct {
	PlaceLatency  time.Duration
	CancelLatency time.Duration
	Book          func(ticker string) (*book.Book, bool) // current public book
	OnFill        func(fillID string, f Fill)

	mu       sync.Mutex
	nextID   int
	nextFill int
	orders   map[string]*paperOrder
	// negative deltas at a level awaiting the trade that explains them
	pending map[levelKey][]pendingDelta
}

type levelKey struct {
	ticker string
	side   book.Side
	price  book.Price
}

type pendingDelta struct {
	rx          time.Time
	ts          int64
	qty         book.Qty
	levelBefore book.Qty // level size before this delta, for the pro-rata share
}

type paperOrder struct {
	id     string
	key    levelKey
	qty    book.Qty // remaining
	ahead  float64  // contracts-units ahead of us in the queue
	liveAt time.Time
	live   bool
}

// NewPaperExecutor returns a simulator using bookFn for level sizes.
func NewPaperExecutor(placeLat, cancelLat time.Duration, bookFn func(string) (*book.Book, bool), onFill func(string, Fill)) *PaperExecutor {
	return &PaperExecutor{PlaceLatency: placeLat, CancelLatency: cancelLat, Book: bookFn, OnFill: onFill,
		orders: map[string]*paperOrder{}, pending: map[levelKey][]pendingDelta{}}
}

// Place joins the queue at price after PlaceLatency.
func (p *PaperExecutor) Place(ctx context.Context, ticker string, side book.Side, price book.Price, qty book.Qty, clientID string) (string, time.Time, error) {
	select {
	case <-time.After(p.PlaceLatency):
	case <-ctx.Done():
		return "", time.Time{}, ctx.Err()
	}
	p.mu.Lock()
	defer p.mu.Unlock()
	p.nextID++
	id := fmt.Sprintf("paper-%d", p.nextID)
	o := &paperOrder{id: id, key: levelKey{ticker, side, price}, qty: qty, liveAt: time.Now(), live: true}
	if b, ok := p.Book(ticker); ok {
		for _, l := range b.Bids(side) {
			if l.Price == price {
				o.ahead = float64(l.Qty)
				break
			}
		}
	}
	p.orders[id] = o
	return id, o.liveAt, nil
}

// Cancel removes the order after CancelLatency.
func (p *PaperExecutor) Cancel(ctx context.Context, _ string, orderID string) (time.Time, error) {
	select {
	case <-time.After(p.CancelLatency):
	case <-ctx.Done():
		return time.Time{}, ctx.Err()
	}
	p.mu.Lock()
	defer p.mu.Unlock()
	if _, ok := p.orders[orderID]; !ok {
		return time.Time{}, ErrOrderDone
	}
	delete(p.orders, orderID)
	return time.Now(), nil
}

// Ahead returns the simulated queue position of orderID (contracts), for the tape.
func (p *PaperExecutor) Ahead(orderID string) (float64, bool) {
	p.mu.Lock()
	defer p.mu.Unlock()
	o, ok := p.orders[orderID]
	if !ok {
		return 0, false
	}
	return o.ahead / 100, true
}

// OnDelta feeds a public book delta. Negative deltas are held until a trade
// with the same exchange timestamp explains them; unexplained ones become
// cancels ahead of us after a grace period. levelBefore is the level's
// quantity before the delta.
func (p *PaperExecutor) OnDelta(rx time.Time, ticker string, side book.Side, price book.Price, delta book.Qty, tsMs int64, levelBefore book.Qty) {
	if delta >= 0 {
		return
	}
	k := levelKey{ticker, side, price}
	p.mu.Lock()
	defer p.mu.Unlock()
	if !p.anyOrderAt(k) {
		return
	}
	p.pending[k] = append(p.pending[k], pendingDelta{rx: rx, ts: tsMs, qty: -delta, levelBefore: levelBefore})
	p.flushLocked(rx, k)
}

func (p *PaperExecutor) anyOrderAt(k levelKey) bool {
	for _, o := range p.orders {
		if o.key == k {
			return true
		}
	}
	return false
}

// flushLocked turns pending deltas older than the grace period into cancels ahead of us.
func (p *PaperExecutor) flushLocked(now time.Time, k levelKey) {
	const grace = 300 * time.Millisecond
	kept := p.pending[k][:0]
	for _, d := range p.pending[k] {
		if now.Sub(d.rx) < grace {
			kept = append(kept, d)
			continue
		}
		p.cancelAheadLocked(k, d.qty, d.levelBefore)
	}
	p.pending[k] = kept
}

// cancelAheadLocked applies qty of cancels at level k, pro rata to our position in the queue.
func (p *PaperExecutor) cancelAheadLocked(k levelKey, qty book.Qty, levelBefore book.Qty) {
	for _, o := range p.orders {
		if o.key != k || !o.live {
			continue
		}
		if levelBefore > 0 && o.ahead > 0 {
			o.ahead -= float64(qty) * (o.ahead / float64(levelBefore))
			if o.ahead < 0 {
				o.ahead = 0
			}
		}
	}
}

// OnTrade feeds a public trade: yesPrice is the YES price, takerSide the taker's side.
// A taker buying NO hits YES bids at yesPrice; a taker buying YES hits NO bids at 1-yesPrice.
func (p *PaperExecutor) OnTrade(rx time.Time, ticker string, yesPrice book.Price, qty book.Qty, takerSide string, tsMs int64) {
	var k levelKey
	if takerSide == "no" {
		k = levelKey{ticker, book.Yes, yesPrice}
	} else {
		k = levelKey{ticker, book.No, book.OneDollar - yesPrice}
	}
	p.mu.Lock()
	defer p.mu.Unlock()
	if !p.anyOrderAt(k) {
		return
	}
	// the trade explains pending negative deltas with the same ts (they are not cancels)
	remaining := qty
	kept := p.pending[k][:0]
	for _, d := range p.pending[k] {
		if d.ts == tsMs && remaining > 0 {
			if d.qty <= remaining {
				remaining -= d.qty
				continue
			}
			d.qty -= remaining
			remaining = 0
		}
		kept = append(kept, d)
	}
	p.pending[k] = kept
	// fills: trades consume the queue from the front
	var fills []Fill
	for _, o := range p.orders {
		if o.key != k || !o.live {
			continue
		}
		q := float64(qty)
		if o.ahead >= q {
			o.ahead -= q
			continue
		}
		avail := q - o.ahead
		o.ahead = 0
		fq := book.Qty(avail)
		if fq > o.qty {
			fq = o.qty
		}
		if fq <= 0 {
			continue
		}
		o.qty -= fq
		fills = append(fills, Fill{Rx: rx, Ticker: ticker, OrderID: o.id, Side: k.side, Price: k.price, Qty: fq})
		if o.qty == 0 {
			delete(p.orders, o.id)
		}
	}
	for _, f := range fills {
		p.nextFill++
		if p.OnFill != nil {
			p.OnFill(fmt.Sprintf("paperfill-%d", p.nextFill), f)
		}
	}
}

// Tick lets time-based flushes happen when no delta arrives (call every ~100ms).
func (p *PaperExecutor) Tick(now time.Time) {
	p.mu.Lock()
	defer p.mu.Unlock()
	for k := range p.pending {
		if len(p.pending[k]) > 0 {
			p.flushLocked(now, k)
		}
	}
}
