// Package book maintains a Kalshi binary-market order book from
// orderbook_snapshot / orderbook_delta messages.
//
// Kalshi books are bids-only on both sides: a YES bid at price p is the same
// resting order as a NO ask at (1 - p). Prices are dollar strings with up to
// four decimals and quantities are fixed-point contract counts with two
// decimals; both are parsed into integers so the book never touches floats.
package book

import (
	"errors"
	"fmt"
	"strings"
)

// Price is a dollar price in units of 1/10000 dollar (so $1.00 == 10000).
type Price int32

// Qty is a contract count in units of 1/100 contract (so 1 contract == 100).
type Qty int64

// Side is one of the two outcome sides of a binary market.
type Side uint8

const (
	Yes Side = iota
	No
)

// OneDollar is the price of a contract that pays out.
const OneDollar Price = 10000

func (s Side) String() string {
	if s == Yes {
		return "yes"
	}
	return "no"
}

// ParseSide parses "yes" or "no".
func ParseSide(s string) (Side, error) {
	switch s {
	case "yes":
		return Yes, nil
	case "no":
		return No, nil
	}
	return 0, fmt.Errorf("book: unknown side %q", s)
}

// Complement returns the price of the opposite side's equivalent order.
func (p Price) Complement() Price { return OneDollar - p }

// String formats the price as a dollar string with four decimals.
func (p Price) String() string { return formatFixed(int64(p), 4) }

// String formats the quantity with two decimals.
func (q Qty) String() string { return formatFixed(int64(q), 2) }

// ParsePrice parses a dollar string such as "0.0800" or "0.960".
func ParsePrice(s string) (Price, error) {
	v, err := parseFixed(s, 4)
	if err != nil {
		return 0, fmt.Errorf("book: bad price %q: %w", s, err)
	}
	if v < 0 || v > int64(OneDollar) {
		return 0, fmt.Errorf("book: price %q out of range", s)
	}
	return Price(v), nil
}

// ParseQty parses a fixed-point contract count such as "300.00" or "-54.00".
func ParseQty(s string) (Qty, error) {
	v, err := parseFixed(s, 2)
	if err != nil {
		return 0, fmt.Errorf("book: bad quantity %q: %w", s, err)
	}
	return Qty(v), nil
}

var errTooManyDecimals = errors.New("too many decimal places")

// parseFixed parses a decimal string into an integer scaled by 10^decimals.
// It rejects more fractional digits than decimals rather than rounding.
func parseFixed(s string, decimals int) (int64, error) {
	if s == "" {
		return 0, errors.New("empty")
	}
	neg := false
	if s[0] == '-' || s[0] == '+' {
		neg = s[0] == '-'
		s = s[1:]
	}
	intPart, fracPart, _ := strings.Cut(s, ".")
	if intPart == "" && fracPart == "" {
		return 0, errors.New("no digits")
	}
	if len(fracPart) > decimals {
		return 0, errTooManyDecimals
	}
	var v int64
	for _, c := range intPart {
		if c < '0' || c > '9' {
			return 0, fmt.Errorf("invalid character %q", c)
		}
		v = v*10 + int64(c-'0')
	}
	for i := 0; i < decimals; i++ {
		d := int64(0)
		if i < len(fracPart) {
			c := fracPart[i]
			if c < '0' || c > '9' {
				return 0, fmt.Errorf("invalid character %q", c)
			}
			d = int64(c - '0')
		}
		v = v*10 + d
	}
	if neg {
		v = -v
	}
	return v, nil
}

func formatFixed(v int64, decimals int) string {
	neg := v < 0
	if neg {
		v = -v
	}
	scale := int64(1)
	for i := 0; i < decimals; i++ {
		scale *= 10
	}
	s := fmt.Sprintf("%d.%0*d", v/scale, decimals, v%scale)
	if neg {
		return "-" + s
	}
	return s
}
