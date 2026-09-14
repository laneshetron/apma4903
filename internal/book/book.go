package book

import (
	"errors"
	"sort"
)

// ErrNegativeQty is returned by ApplyDelta when a delta would take a price
// level below zero. It means the local book has diverged from the exchange
// and must be rebuilt from a fresh snapshot.
var ErrNegativeQty = errors.New("book: delta drives level negative")

// Level is one resting price level.
type Level struct {
	Price Price
	Qty   Qty
}

// Book is the resting bids for one market. It is not safe for concurrent use.
type Book struct {
	yes map[Price]Qty
	no  map[Price]Qty

	// sorted best-first caches, rebuilt lazily after mutation
	yesSorted, noSorted []Level
	dirty               bool
}

// New returns an empty book.
func New() *Book {
	return &Book{yes: map[Price]Qty{}, no: map[Price]Qty{}}
}

func (b *Book) side(s Side) map[Price]Qty {
	if s == Yes {
		return b.yes
	}
	return b.no
}

// ApplySnapshot replaces the whole book. Levels with zero quantity are dropped.
func (b *Book) ApplySnapshot(yes, no []Level) {
	clear(b.yes)
	clear(b.no)
	for _, l := range yes {
		if l.Qty != 0 {
			b.yes[l.Price] = l.Qty
		}
	}
	for _, l := range no {
		if l.Qty != 0 {
			b.no[l.Price] = l.Qty
		}
	}
	b.dirty = true
}

// ApplyDelta adds delta to the level at price on side, deleting it at zero.
// On ErrNegativeQty the book is left unchanged.
func (b *Book) ApplyDelta(s Side, price Price, delta Qty) error {
	m := b.side(s)
	q := m[price] + delta
	switch {
	case q < 0:
		return ErrNegativeQty
	case q == 0:
		delete(m, price)
	default:
		m[price] = q
	}
	b.dirty = true
	return nil
}

func (b *Book) refresh() {
	if !b.dirty {
		return
	}
	b.yesSorted = sortedLevels(b.yes, b.yesSorted[:0])
	b.noSorted = sortedLevels(b.no, b.noSorted[:0])
	b.dirty = false
}

func sortedLevels(m map[Price]Qty, buf []Level) []Level {
	for p, q := range m {
		buf = append(buf, Level{p, q})
	}
	sort.Slice(buf, func(i, j int) bool { return buf[i].Price > buf[j].Price })
	return buf
}

// Bids returns the resting bids on side, best (highest price) first.
// The returned slice is owned by the book and valid until the next mutation.
func (b *Book) Bids(s Side) []Level {
	b.refresh()
	if s == Yes {
		return b.yesSorted
	}
	return b.noSorted
}

// Depth returns up to n levels per side, best first.
func (b *Book) Depth(n int) (yes, no []Level) {
	yes, no = b.Bids(Yes), b.Bids(No)
	if n >= 0 && len(yes) > n {
		yes = yes[:n]
	}
	if n >= 0 && len(no) > n {
		no = no[:n]
	}
	return yes, no
}

// BestBid returns the best bid on side, or ok=false if that side is empty.
func (b *Book) BestBid(s Side) (Level, bool) {
	bids := b.Bids(s)
	if len(bids) == 0 {
		return Level{}, false
	}
	return bids[0], true
}

// BestAsk returns the best ask on side, derived from the opposite side's best
// bid: a NO bid at p is a YES ask at 1-p. Qty is the resting NO quantity.
func (b *Book) BestAsk(s Side) (Level, bool) {
	l, ok := b.BestBid(s.Opposite())
	if !ok {
		return Level{}, false
	}
	return Level{Price: l.Price.Complement(), Qty: l.Qty}, true
}

// Opposite returns the other side.
func (s Side) Opposite() Side {
	if s == Yes {
		return No
	}
	return Yes
}

// TopOfBook is the best YES bid/ask with derived mid and spread.
type TopOfBook struct {
	Bid, Ask       Level
	HasBid, HasAsk bool
}

// Top returns the YES top of book.
func (b *Book) Top() TopOfBook {
	t := TopOfBook{}
	t.Bid, t.HasBid = b.BestBid(Yes)
	t.Ask, t.HasAsk = b.BestAsk(Yes)
	return t
}

// Spread returns ask - bid in price units, or ok=false if either side is empty.
func (t TopOfBook) Spread() (Price, bool) {
	if !t.HasBid || !t.HasAsk {
		return 0, false
	}
	return t.Ask.Price - t.Bid.Price, true
}

// Mid returns (bid+ask)/2 in price units (truncated), or ok=false if either side is empty.
func (t TopOfBook) Mid() (Price, bool) {
	if !t.HasBid || !t.HasAsk {
		return 0, false
	}
	return (t.Ask.Price + t.Bid.Price) / 2, true
}

// Crossed reports whether the best YES bid is at or above the best YES ask,
// which never happens on a consistent exchange book.
func (t TopOfBook) Crossed() bool {
	return t.HasBid && t.HasAsk && t.Bid.Price >= t.Ask.Price
}

// Levels returns the number of resting levels on side.
func (b *Book) Levels(s Side) int { return len(b.side(s)) }

// Equal reports whether both books hold identical levels.
func (b *Book) Equal(o *Book) bool {
	return mapsEqual(b.yes, o.yes) && mapsEqual(b.no, o.no)
}

func mapsEqual(a, b map[Price]Qty) bool {
	if len(a) != len(b) {
		return false
	}
	for p, q := range a {
		if b[p] != q {
			return false
		}
	}
	return true
}

// Diff returns the levels that differ between b and o, as (price, qty in b, qty in o).
type LevelDiff struct {
	Side       Side
	Price      Price
	Have, Want Qty
}

// Diff lists every level whose quantity differs between b (have) and o (want).
func (b *Book) Diff(o *Book) []LevelDiff {
	var out []LevelDiff
	for _, s := range []Side{Yes, No} {
		have, want := b.side(s), o.side(s)
		for p, q := range have {
			if want[p] != q {
				out = append(out, LevelDiff{s, p, q, want[p]})
			}
		}
		for p, q := range want {
			if _, ok := have[p]; !ok {
				out = append(out, LevelDiff{s, p, 0, q})
			}
		}
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Side != out[j].Side {
			return out[i].Side < out[j].Side
		}
		return out[i].Price > out[j].Price
	})
	return out
}

// Clone returns a deep copy.
func (b *Book) Clone() *Book {
	c := New()
	for p, q := range b.yes {
		c.yes[p] = q
	}
	for p, q := range b.no {
		c.no[p] = q
	}
	c.dirty = true
	return c
}
