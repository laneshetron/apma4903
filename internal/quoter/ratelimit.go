package quoter

import (
	"sync"
	"time"
)

// TokenBucket mirrors Kalshi's write budget: refill tokens/second up to
// capacity; an order costs 10 tokens, a cancel 2.
type TokenBucket struct {
	mu       sync.Mutex
	tokens   float64
	capacity float64
	refill   float64 // per second
	last     time.Time
	now      func() time.Time
}

const (
	CostOrder  = 10
	CostCancel = 2
)

// NewTokenBucket returns a full bucket.
func NewTokenBucket(refillPerSec, capacity float64) *TokenBucket {
	return &TokenBucket{tokens: capacity, capacity: capacity, refill: refillPerSec, last: time.Now(), now: time.Now}
}

func (b *TokenBucket) top() {
	now := b.now()
	b.tokens += b.refill * now.Sub(b.last).Seconds()
	if b.tokens > b.capacity {
		b.tokens = b.capacity
	}
	b.last = now
}

// Take spends cost tokens if available and reports whether it did.
func (b *TokenBucket) Take(cost float64) bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.top()
	if b.tokens < cost {
		return false
	}
	b.tokens -= cost
	return true
}

// Available returns the current token balance.
func (b *TokenBucket) Available() float64 {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.top()
	return b.tokens
}
