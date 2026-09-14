package book

import (
	"fmt"

	"github.com/laneshetron/kalshi/internal/kalshi"
)

// ParseLevels converts wire [price, qty] tuples into Levels.
func ParseLevels(in []kalshi.PriceLevel) ([]Level, error) {
	out := make([]Level, 0, len(in))
	for _, pl := range in {
		p, err := ParsePrice(pl.Price())
		if err != nil {
			return nil, err
		}
		q, err := ParseQty(pl.Qty())
		if err != nil {
			return nil, err
		}
		out = append(out, Level{p, q})
	}
	return out, nil
}

// ApplySnapshotMsg replaces the book with the contents of a snapshot message.
func (b *Book) ApplySnapshotMsg(m *kalshi.OrderbookSnapshotMsg) error {
	yes, err := ParseLevels(m.YesDollarsFP)
	if err != nil {
		return fmt.Errorf("snapshot yes: %w", err)
	}
	no, err := ParseLevels(m.NoDollarsFP)
	if err != nil {
		return fmt.Errorf("snapshot no: %w", err)
	}
	b.ApplySnapshot(yes, no)
	return nil
}

// ApplyDeltaMsg applies a delta message. ErrNegativeQty is returned unwrapped
// so callers can detect divergence with errors.Is.
func (b *Book) ApplyDeltaMsg(m *kalshi.OrderbookDeltaMsg) error {
	side, err := ParseSide(m.Side)
	if err != nil {
		return err
	}
	p, err := ParsePrice(m.PriceDollars)
	if err != nil {
		return err
	}
	d, err := ParseQty(m.DeltaFP)
	if err != nil {
		return err
	}
	return b.ApplyDelta(side, p, d)
}

// FromLevels builds a book from wire-format sides (used for REST snapshots).
func FromLevels(yes, no []kalshi.PriceLevel) (*Book, error) {
	y, err := ParseLevels(yes)
	if err != nil {
		return nil, err
	}
	n, err := ParseLevels(no)
	if err != nil {
		return nil, err
	}
	b := New()
	b.ApplySnapshot(y, n)
	return b, nil
}
