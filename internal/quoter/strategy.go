// Package quoter is the market-making engine: the strategy decisions ported
// from python/kalshi_data/research/sim.py, an order state machine, and
// executors for paper and live trading.
package quoter

import (
	"fmt"
	"time"

	"github.com/laneshetron/kalshi/internal/book"
)

// Tick is one cent, the touch increment the strategy quotes in.
const Tick book.Price = 100

// Params are the strategy settings (the sim's Params, standing config).
type Params struct {
	Size       book.Qty      // contracts per quote (qty units: contracts * 100)
	MaxPos     book.Qty      // absolute position limit (qty units)
	StopBefore time.Duration // stop quoting this long before close
	SignalMove float64       // $ Coinbase mid move over 1s that pulls the stale side; 0 disables
	Cooldown   time.Duration // no re-quote on the stale side for this long after a signal
	JoinTheta  *float64      // join gate: refuse to join when expected edge < -theta (cents); nil disables
	GreeksCap  *float64      // don't quote when a 1-sigma 10s spot move is worth >= cap (fraction of $1); nil disables
	MinPrice   book.Price    // don't quote below this (default 1c)
	MaxPrice   book.Price    // don't quote above this (default 99c)
}

// OrderState is where an order is in its lifecycle.
type OrderState int

const (
	PendingNew OrderState = iota
	Resting
	PendingCancel
	Done
)

func (s OrderState) String() string {
	return [...]string{"pending_new", "resting", "pending_cancel", "done"}[s]
}

// OrderView is what the strategy sees of a working order.
type OrderView struct {
	ID    string
	Side  book.Side
	Price book.Price
	Qty   book.Qty // remaining
	State OrderState
}

// Collateral is the dollars Kalshi reserves for a resting bid: price x contracts.
func Collateral(price book.Price, qty book.Qty) float64 {
	return float64(price) / float64(book.OneDollar) * float64(qty) / 100
}

// AffordableQty is the largest whole-contract quantity <= want whose collateral fits in available.
func AffordableQty(want book.Qty, price book.Price, available float64) book.Qty {
	if available < 0 {
		return want
	}
	per := float64(price) / float64(book.OneDollar)
	if per <= 0 {
		return 0
	}
	n := int64(available / per) // whole contracts
	q := book.Qty(n * 100)
	if q > want {
		return want
	}
	return q
}

// Inputs is the market and account state at a decision point.
type Inputs struct {
	Now     time.Time
	Book    *book.Book
	Stale   bool // book not trustworthy (waiting for snapshot)
	Pos     book.Qty
	Orders  map[book.Side]*OrderView // at most one working order per side
	CloseAt time.Time
	Strike  float64
	Spot    *SpotState
	Edge    *EdgeModel
	// Available is the collateral ($) free for new orders; a negative value means unknown (no sizing).
	Available float64
}

// ActionKind is Place or Cancel.
type ActionKind int

const (
	Place ActionKind = iota
	Cancel
)

// Action is a decision the executor should carry out.
type Action struct {
	Kind   ActionKind
	Side   book.Side
	Price  book.Price
	Qty    book.Qty
	Reason string
}

func (a Action) String() string {
	if a.Kind == Cancel {
		return fmt.Sprintf("cancel %s (%s)", a.Side, a.Reason)
	}
	return fmt.Sprintf("place %s %s x %s (%s)", a.Side, a.Price, a.Qty, a.Reason)
}

// Strategy holds the small amount of state the decisions need between calls.
type Strategy struct {
	P       Params
	blocked map[book.Side]time.Time // side -> quote allowed again at
	Vetoes  map[string]int
}

// NewStrategy returns a strategy with p (defaults filled in).
func NewStrategy(p Params) *Strategy {
	if p.MinPrice == 0 {
		p.MinPrice = Tick
	}
	if p.MaxPrice == 0 {
		p.MaxPrice = book.OneDollar - Tick
	}
	if p.Cooldown == 0 {
		p.Cooldown = time.Second
	}
	return &Strategy{P: p, blocked: map[book.Side]time.Time{}, Vetoes: map[string]int{}}
}

// OnSpotTick applies the cancel-on-signal rule after a Coinbase quote update
// and returns the cancels it wants.
func (s *Strategy) OnSpotTick(in Inputs) []Action {
	if s.P.SignalMove <= 0 || in.Spot == nil {
		return nil
	}
	d, ok := in.Spot.Move1s(in.Now)
	if !ok || d > -s.P.SignalMove && d < s.P.SignalMove {
		return nil
	}
	// spot up -> our YES ask (a NO bid) is stale; spot down -> our YES bid is stale
	stale := book.Yes
	if d > 0 {
		stale = book.No
	}
	s.blocked[stale] = in.Now.Add(s.P.Cooldown)
	if o := in.Orders[stale]; o != nil && (o.State == Resting || o.State == PendingNew) {
		return []Action{{Kind: Cancel, Side: stale, Reason: "signal"}}
	}
	return nil
}

// Decide returns the actions that move the working orders toward the desired quotes.
func (s *Strategy) Decide(in Inputs) []Action {
	var out []Action
	cancelAll := func(reason string) {
		for _, side := range []book.Side{book.Yes, book.No} {
			if o := in.Orders[side]; o != nil && (o.State == Resting || o.State == PendingNew) {
				out = append(out, Action{Kind: Cancel, Side: side, Reason: reason})
			}
		}
	}
	if !in.Now.Before(in.CloseAt.Add(-s.P.StopBefore)) {
		cancelAll("endgame")
		return out
	}
	if in.Stale || in.Book == nil {
		return nil // hold; nothing trustworthy to act on
	}
	bestYes, okY := in.Book.BestBid(book.Yes)
	bestNo, okN := in.Book.BestBid(book.No)
	if !okY || !okN {
		return nil
	}
	spread := (book.OneDollar - bestNo.Price) - bestYes.Price
	improve := spread > Tick
	want := map[book.Side]book.Price{book.Yes: bestYes.Price, book.No: bestNo.Price}
	if improve {
		want[book.Yes] += Tick
		want[book.No] += Tick
	}
	depth := map[book.Side]book.Qty{book.Yes: bestYes.Qty, book.No: bestNo.Qty}

	lim := s.P.MaxPos - s.P.Size
	allow := map[book.Side]bool{book.Yes: in.Pos <= lim, book.No: in.Pos >= -lim}
	if s.P.GreeksCap != nil && in.Spot != nil {
		if g, ok := in.Spot.DeltaSigma10(in.Strike, in.CloseAt); ok && g >= *s.P.GreeksCap {
			allow[book.Yes], allow[book.No] = false, false
			s.Vetoes["greeks"]++
		}
	}
	for side, until := range s.blocked {
		if in.Now.Before(until) {
			allow[side] = false
		}
	}
	for _, side := range []book.Side{book.Yes, book.No} {
		if want[side] < s.P.MinPrice || want[side] > s.P.MaxPrice {
			allow[side] = false
		}
	}

	// capital: split what is free evenly across the sides that need a new order
	budget := in.Available
	if budget >= 0 {
		n := 0
		for _, side := range []book.Side{book.Yes, book.No} {
			o := in.Orders[side]
			working := o != nil && (o.State == Resting || o.State == PendingNew) && allow[side] && o.Price == want[side]
			if allow[side] && !working {
				n++
			}
		}
		if n > 1 {
			budget /= float64(n)
		}
	}
	for _, side := range []book.Side{book.Yes, book.No} {
		o := in.Orders[side]
		working := o != nil && (o.State == Resting || o.State == PendingNew)
		if working && (!allow[side] || o.Price != want[side]) {
			reason := "reprice"
			if !allow[side] {
				reason = "disallowed"
			}
			out = append(out, Action{Kind: Cancel, Side: side, Reason: reason})
			continue // the replacement is placed once the cancel lands
		}
		if !allow[side] || working || (o != nil && o.State == PendingCancel) {
			continue
		}
		if s.P.JoinTheta != nil && in.Edge != nil && in.Spot != nil {
			other := side.Opposite()
			imb := 0.0
			if depth[other]+depth[side] > 0 {
				imb = float64(depth[other]-depth[side]) / float64(depth[other]+depth[side])
			}
			qJoin := 0.0
			if !improve {
				qJoin = float64(depth[side]) / 100
			}
			ttx := in.CloseAt.Sub(in.Now).Minutes()
			if e, ok := in.Edge.Edge(side.String(), imb, in.Spot.MicroUnsigned(), ttx, qJoin); ok && e < -*s.P.JoinTheta {
				s.Vetoes["join"]++
				continue
			}
		}
		reason := "join"
		if improve {
			reason = "improve"
		}
		qty := AffordableQty(s.P.Size, want[side], budget)
		if qty < 100 {
			s.Vetoes["capital"]++
			continue
		}
		out = append(out, Action{Kind: Place, Side: side, Price: want[side], Qty: qty, Reason: reason})
	}
	return out
}
