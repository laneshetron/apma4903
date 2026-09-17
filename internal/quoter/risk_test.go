package quoter

import (
	"testing"
	"time"
)

func TestTokenBucket(t *testing.T) {
	b := NewTokenBucket(100, 100)
	now := t0
	b.now = func() time.Time { return now }
	b.last = now
	for i := 0; i < 10; i++ {
		if !b.Take(CostOrder) {
			t.Fatalf("order %d should fit in a full bucket", i)
		}
	}
	if b.Take(CostOrder) {
		t.Fatal("11th order must be refused")
	}
	if !b.Take(0) {
		t.Fatal("zero-cost always fits")
	}
	now = now.Add(20 * time.Millisecond) // +2 tokens: a cancel fits, an order does not
	if !b.Take(CostCancel) || b.Take(CostOrder) {
		t.Fatal("refill accounting wrong")
	}
	now = now.Add(5 * time.Second)
	if b.Available() != 100 {
		t.Fatalf("bucket should cap at capacity, got %v", b.Available())
	}
}

func TestRiskLimitsAreStickyAndOrdered(t *testing.T) {
	r := NewRisk(DefaultLimits())
	if h := r.Check(t0, 100*100, -10, time.Second, time.Second, false); h != "" {
		t.Fatalf("healthy state halted: %q", h)
	}
	if h := r.Check(t0, 250*100, 0, 0, 0, false); h == "" {
		t.Fatal("position breach should halt")
	}
	first := r.Halted()
	r.Check(t0, 0, -1000, 0, 0, true) // later breaches do not overwrite the first reason
	if r.Halted() != first {
		t.Fatalf("halt reason changed from %q to %q", first, r.Halted())
	}
	for _, tc := range []struct {
		name string
		f    func(*Risk) string
	}{
		{"loss", func(r *Risk) string { return r.Check(t0, 0, -60, 0, 0, false) }},
		{"book silence", func(r *Risk) string { return r.Check(t0, 0, 0, 4*time.Second, 0, false) }},
		{"spot silence", func(r *Risk) string { return r.Check(t0, 0, 0, 0, 6*time.Second, false) }},
		{"seq gap", func(r *Risk) string { return r.Check(t0, 0, 0, 0, 0, true) }},
		{"errors", func(r *Risk) string {
			for i := 0; i < 5; i++ {
				r.RecordError()
			}
			return r.Halted()
		}},
		{"runaway", func(r *Risk) string {
			for i := 0; i < 601; i++ {
				r.RecordOrder(t0.Add(time.Duration(i) * 50 * time.Millisecond))
			}
			return r.Halted()
		}},
	} {
		if h := tc.f(NewRisk(DefaultLimits())); h == "" {
			t.Errorf("%s should halt", tc.name)
		}
	}
	r = NewRisk(DefaultLimits())
	for i := 0; i < 4; i++ {
		r.RecordError()
	}
	r.RecordOK()
	r.RecordError()
	if r.Halted() != "" {
		t.Fatal("an OK resets the error streak")
	}
}
