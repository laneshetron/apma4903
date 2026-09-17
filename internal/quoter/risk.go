package quoter

import (
	"fmt"
	"sync"
	"time"

	"github.com/laneshetron/kalshi/internal/book"
)

// Limits are the hard stops. Any breach halts quoting and cancels everything.
type Limits struct {
	MaxAbsPos       book.Qty      // absolute position, qty units
	MaxLoss         float64       // $ mark-to-market loss for the session
	MaxBookAge      time.Duration // Kalshi book silence before we consider the feed dead
	MaxSpotAge      time.Duration // Coinbase silence before we stop (the cancel signal is blind)
	MaxErrors       int           // consecutive executor errors
	MaxOrdersPerMin int           // runaway-loop guard
}

// DefaultLimits are conservative settings for the first live runs.
func DefaultLimits() Limits {
	return Limits{MaxAbsPos: 200 * 100, MaxLoss: 50, MaxBookAge: 3 * time.Second, MaxSpotAge: 5 * time.Second, MaxErrors: 5, MaxOrdersPerMin: 600}
}

// Risk evaluates the limits and remembers the first breach (the halt is sticky).
type Risk struct {
	L          Limits
	mu         sync.Mutex
	halted     string
	errors     int
	orderTimes []time.Time
}

// NewRisk returns a risk monitor with limits l.
func NewRisk(l Limits) *Risk { return &Risk{L: l} }

// Halted returns the reason quoting is halted, or "".
func (r *Risk) Halted() string {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.halted
}

// Halt stops quoting for reason (idempotent; the first reason sticks).
func (r *Risk) Halt(reason string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.haltLocked(reason)
}

func (r *Risk) haltLocked(reason string) {
	if r.halted == "" {
		r.halted = reason
	}
}

// RecordError counts an executor failure; RecordOK resets the streak.
func (r *Risk) RecordError() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.errors++
	if r.errors >= r.L.MaxErrors {
		r.haltLocked(fmt.Sprintf("%d consecutive executor errors", r.errors))
	}
}

// RecordOK resets the consecutive-error count.
func (r *Risk) RecordOK() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.errors = 0
}

// RecordOrder counts an order for the runaway guard.
func (r *Risk) RecordOrder(now time.Time) {
	r.mu.Lock()
	defer r.mu.Unlock()
	cut := now.Add(-time.Minute)
	i := 0
	for i < len(r.orderTimes) && r.orderTimes[i].Before(cut) {
		i++
	}
	r.orderTimes = append(r.orderTimes[i:], now)
	if len(r.orderTimes) > r.L.MaxOrdersPerMin {
		r.haltLocked(fmt.Sprintf("%d orders in the last minute", len(r.orderTimes)))
	}
}

// Check evaluates the state limits; returns the halt reason if any (also sticky).
func (r *Risk) Check(now time.Time, pos book.Qty, pnl float64, bookAge, spotAge time.Duration, seqGap bool) string {
	r.mu.Lock()
	defer r.mu.Unlock()
	switch {
	case pos > r.L.MaxAbsPos || pos < -r.L.MaxAbsPos:
		r.haltLocked(fmt.Sprintf("position %s beyond limit", pos))
	case pnl < -r.L.MaxLoss:
		r.haltLocked(fmt.Sprintf("session loss %.2f beyond limit", -pnl))
	case bookAge > r.L.MaxBookAge:
		r.haltLocked(fmt.Sprintf("kalshi book silent for %s", bookAge.Round(time.Millisecond)))
	case spotAge > r.L.MaxSpotAge:
		r.haltLocked(fmt.Sprintf("coinbase feed silent for %s", spotAge.Round(time.Millisecond)))
	case seqGap:
		r.haltLocked("sequence gap on the book feed")
	}
	return r.halted
}
