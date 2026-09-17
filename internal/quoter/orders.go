package quoter

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/laneshetron/kalshi/internal/book"
)

// Executor sends orders somewhere: Kalshi (live) or the paper simulator.
type Executor interface {
	// Place submits a resting bid on side at price for qty and returns the
	// exchange order id. clientID is the idempotency key.
	Place(ctx context.Context, ticker string, side book.Side, price book.Price, qty book.Qty, clientID string) (orderID string, engineTs time.Time, err error)
	// Cancel cancels orderID (market ticker given for routing).
	Cancel(ctx context.Context, ticker, orderID string) (engineTs time.Time, err error)
}

// Order is a working or finished order.
type Order struct {
	ClientID string
	ID       string
	Ticker   string
	Side     book.Side
	Price    book.Price
	Qty      book.Qty // original
	Filled   book.Qty
	State    OrderState
	Placed   time.Time
	Acked    time.Time
	Reason   string
}

// Fill is one execution against our order.
type Fill struct {
	Rx      time.Time
	Ticker  string
	OrderID string
	Side    book.Side
	Price   book.Price
	Qty     book.Qty
	Taker   bool
}

// Ledger is the order state machine and position book for one market. It is
// safe for concurrent use: the executor's async acks and the WS order/fill
// events land from other goroutines.
type Ledger struct {
	mu      sync.Mutex
	ticker  string
	orders  map[string]*Order // by client id
	byID    map[string]*Order
	working map[book.Side]*Order
	pos     book.Qty
	cash    float64 // dollars, signed (YES-sale convention: a NO fill at p credits 1-p)
	paid    float64 // collateral actually paid for fills: YES fills at the YES price, NO fills at the NO price
	fills   []Fill
	seen    map[string]bool // fill ids applied
	onEvent func(kind string, fields map[string]any)
}

// NewLedger returns an empty ledger for ticker. onEvent (optional) receives
// every state change for the tape.
func NewLedger(ticker string, onEvent func(kind string, fields map[string]any)) *Ledger {
	if onEvent == nil {
		onEvent = func(string, map[string]any) {}
	}
	return &Ledger{ticker: ticker, orders: map[string]*Order{}, byID: map[string]*Order{}, working: map[book.Side]*Order{}, seen: map[string]bool{}, onEvent: onEvent}
}

// Seed sets a position inherited from a previous process, marked at mid so
// the session P&L starts at zero.
func (l *Ledger) Seed(pos book.Qty, mid book.Price) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.pos = pos
	l.cash = -float64(pos) / 100 * float64(mid) / float64(book.OneDollar)
	if pos > 0 {
		l.paid = Collateral(mid, pos)
	} else {
		l.paid = Collateral(book.OneDollar-mid, -pos)
	}
}

// Views returns the strategy's view of working orders and the position.
func (l *Ledger) Views() (map[book.Side]*OrderView, book.Qty) {
	l.mu.Lock()
	defer l.mu.Unlock()
	out := map[book.Side]*OrderView{}
	for s, o := range l.working {
		out[s] = &OrderView{ID: o.ID, Side: o.Side, Price: o.Price, Qty: o.Qty - o.Filled, State: o.State}
	}
	return out, l.pos
}

// Position returns the signed YES position (qty units) and cash ($).
func (l *Ledger) Position() (book.Qty, float64) {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.pos, l.cash
}

// Fills returns a copy of all fills so far.
func (l *Ledger) Fills() []Fill {
	l.mu.Lock()
	defer l.mu.Unlock()
	return append([]Fill(nil), l.fills...)
}

// byOrderID looks up an order by exchange id (nil if unknown).
func (l *Ledger) byOrderID(id string) *Order {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.byID[id]
}

// WorkingOrders returns copies of the working orders.
func (l *Ledger) WorkingOrders() []Order {
	l.mu.Lock()
	defer l.mu.Unlock()
	out := make([]Order, 0, len(l.working))
	for _, o := range l.working {
		out = append(out, *o)
	}
	return out
}

// Working returns the working order on side, if any.
func (l *Ledger) Working(side book.Side) *Order {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.working[side]
}

// Place records a new order as pending and sends it through ex. On rejection
// the order is dropped so the side frees up immediately.
func (l *Ledger) Place(ctx context.Context, ex Executor, side book.Side, price book.Price, qty book.Qty, clientID, reason string, now time.Time) error {
	l.mu.Lock()
	if w := l.working[side]; w != nil {
		l.mu.Unlock()
		return fmt.Errorf("ledger: %s side already has a working order (%s)", side, w.State)
	}
	o := &Order{ClientID: clientID, Ticker: l.ticker, Side: side, Price: price, Qty: qty, State: PendingNew, Placed: now, Reason: reason}
	l.orders[clientID] = o
	l.working[side] = o
	l.mu.Unlock()
	l.onEvent("place", map[string]any{"client_id": clientID, "side": side.String(), "price": price.String(), "qty": qty.String(), "reason": reason})

	id, engineTs, err := ex.Place(ctx, l.ticker, side, price, qty, clientID)
	l.mu.Lock()
	defer l.mu.Unlock()
	if err != nil {
		o.State = Done
		if l.working[side] == o {
			delete(l.working, side)
		}
		l.onEvent("place_rejected", map[string]any{"client_id": clientID, "err": err.Error()})
		return err
	}
	o.ID, o.Acked = id, time.Now()
	l.byID[id] = o
	if o.State == PendingNew {
		o.State = Resting
	}
	l.onEvent("place_ack", map[string]any{"client_id": clientID, "order_id": id, "engine_ts": engineTs.UnixMilli(), "ack_ms": float64(o.Acked.Sub(o.Placed).Microseconds()) / 1e3})
	return nil
}

// Cancel moves the side's working order to pending-cancel and sends the
// cancel. A cancel requested while the place is still unacknowledged is
// deferred: the caller should call Cancel again once the order is Resting.
func (l *Ledger) Cancel(ctx context.Context, ex Executor, side book.Side, reason string) error {
	l.mu.Lock()
	o := l.working[side]
	if o == nil || o.State != Resting {
		l.mu.Unlock()
		if o != nil && o.State == PendingNew {
			return errPendingNew
		}
		return nil
	}
	o.State = PendingCancel
	l.mu.Unlock()
	l.onEvent("cancel", map[string]any{"order_id": o.ID, "reason": reason})
	engineTs, err := ex.Cancel(ctx, l.ticker, o.ID)
	l.mu.Lock()
	defer l.mu.Unlock()
	if errors.Is(err, ErrOrderDone) {
		l.onEvent("cancel_ack", map[string]any{"order_id": o.ID, "already_done": true})
		l.finishLocked(o, "already_done")
		return nil
	}
	if err != nil {
		// unknown outcome: keep it pending-cancel so we never double-quote; the
		// user_orders stream will settle it
		l.onEvent("cancel_error", map[string]any{"order_id": o.ID, "err": err.Error()})
		return err
	}
	l.onEvent("cancel_ack", map[string]any{"order_id": o.ID, "engine_ts": engineTs.UnixMilli()})
	l.finishLocked(o, "canceled")
	return nil
}

var errPendingNew = fmt.Errorf("ledger: order not yet acknowledged")

// ErrOrderDone is returned by an executor when a cancel targets an order that
// no longer exists (already filled or cancelled); the ledger finishes it.
var ErrOrderDone = fmt.Errorf("order already done")

// IsPendingNew reports whether err means the cancel must be retried after the ack.
func IsPendingNew(err error) bool { return err == errPendingNew }

func (l *Ledger) finishLocked(o *Order, how string) {
	if o.State == Done {
		return
	}
	o.State = Done
	if l.working[o.Side] == o {
		delete(l.working, o.Side)
	}
	l.onEvent("done", map[string]any{"order_id": o.ID, "how": how, "filled": o.Filled.String()})
}

// OnOrderUpdate applies a user_orders event: status is Kalshi's
// (resting|canceled|executed|...). Unknown orders are ignored.
func (l *Ledger) OnOrderUpdate(orderID, clientID, status string, remaining book.Qty) {
	l.mu.Lock()
	defer l.mu.Unlock()
	o := l.byID[orderID]
	if o == nil && clientID != "" {
		o = l.orders[clientID]
		if o != nil && o.ID == "" {
			o.ID = orderID
			l.byID[orderID] = o
		}
	}
	if o == nil {
		return
	}
	switch status {
	case "resting":
		if o.State == PendingNew {
			o.State = Resting
		}
	case "canceled", "cancelled", "expired", "executed", "filled":
		if status == "executed" || status == "filled" {
			o.Filled = o.Qty
		}
		l.finishLocked(o, status)
	}
}

// OnFill applies an execution. Duplicate fill ids are ignored.
func (l *Ledger) OnFill(fillID string, f Fill) {
	l.mu.Lock()
	defer l.mu.Unlock()
	if fillID != "" && l.seen[fillID] {
		return
	}
	if fillID != "" {
		l.seen[fillID] = true
	}
	o := l.byID[f.OrderID]
	if o != nil {
		o.Filled += f.Qty
		if o.Filled >= o.Qty {
			l.finishLocked(o, "filled")
		}
	}
	// a YES bid fill is +qty YES at price; a NO bid fill is -qty YES at (1 - price)
	contracts := float64(f.Qty) / 100
	l.paid += Collateral(f.Price, f.Qty)
	if f.Side == book.Yes {
		l.pos += f.Qty
		l.cash -= contracts * float64(f.Price) / 10000
	} else {
		l.pos -= f.Qty
		l.cash += contracts * float64(book.OneDollar-f.Price) / 10000
	}
	l.fills = append(l.fills, f)
	l.onEvent("fill", map[string]any{"order_id": f.OrderID, "side": f.Side.String(), "price": f.Price.String(), "qty": f.Qty.String(), "pos": l.pos.String()})
}

// CollateralUsed is the dollars paid for the position so far (what Kalshi holds against it).
func (l *Ledger) CollateralUsed() float64 {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.paid
}

// MarkPnL is cash plus the position marked at mid ($).
func (l *Ledger) MarkPnL(mid book.Price) float64 {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.cash + float64(l.pos)/100*float64(mid)/10000
}
