package book

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/laneshetron/kalshi/internal/kalshi"
)

func TestParseFixed(t *testing.T) {
	cases := []struct {
		in       string
		decimals int
		want     int64
		wantErr  bool
	}{
		{"0.0800", 4, 800, false},
		{"0.960", 4, 9600, false},
		{"1", 4, 10000, false},
		{"1.0000", 4, 10000, false},
		{".5", 4, 5000, false},
		{"0.5025", 4, 5025, false},
		{"300.00", 2, 30000, false},
		{"-54.00", 2, -5400, false},
		{"5.5", 2, 550, false},
		{"0.12345", 4, 0, true}, // too many decimals
		{"", 4, 0, true},
		{"abc", 4, 0, true},
		{"1e3", 4, 0, true},
	}
	for _, c := range cases {
		got, err := parseFixed(c.in, c.decimals)
		if (err != nil) != c.wantErr {
			t.Errorf("parseFixed(%q,%d) err=%v wantErr=%v", c.in, c.decimals, err, c.wantErr)
			continue
		}
		if !c.wantErr && got != c.want {
			t.Errorf("parseFixed(%q,%d)=%d want %d", c.in, c.decimals, got, c.want)
		}
	}
}

func TestPriceRoundTrip(t *testing.T) {
	for _, s := range []string{"0.0800", "0.9600", "1.0000", "0.0000", "0.5025"} {
		p, err := ParsePrice(s)
		if err != nil {
			t.Fatal(err)
		}
		if p.String() != s {
			t.Errorf("ParsePrice(%q).String()=%q", s, p.String())
		}
	}
	if _, err := ParsePrice("1.0001"); err == nil {
		t.Error("price above $1 should fail")
	}
	if _, err := ParsePrice("-0.01"); err == nil {
		t.Error("negative price should fail")
	}
	if Qty(-5400).String() != "-54.00" {
		t.Errorf("Qty(-5400).String()=%q", Qty(-5400).String())
	}
}

func TestComplement(t *testing.T) {
	p, _ := ParsePrice("0.5600")
	if p.Complement().String() != "0.4400" {
		t.Errorf("complement of 0.56 = %s", p.Complement())
	}
}

func TestDeltaLeavesBookUnchangedOnError(t *testing.T) {
	b := New()
	b.ApplySnapshot([]Level{{5000, 1000}}, nil)
	err := b.ApplyDelta(Yes, 5000, -1001)
	if !errors.Is(err, ErrNegativeQty) {
		t.Fatalf("want ErrNegativeQty, got %v", err)
	}
	if got := b.Bids(Yes); len(got) != 1 || got[0].Qty != 1000 {
		t.Errorf("book mutated on error: %+v", got)
	}
}

func TestBidsSortedBestFirst(t *testing.T) {
	b := New()
	b.ApplySnapshot([]Level{{100, 1}, {5000, 2}, {2500, 3}}, []Level{{4000, 4}, {4500, 5}})
	yes := b.Bids(Yes)
	if yes[0].Price != 5000 || yes[1].Price != 2500 || yes[2].Price != 100 {
		t.Errorf("yes not sorted: %+v", yes)
	}
	ask, ok := b.BestAsk(Yes)
	if !ok || ask.Price != 5500 || ask.Qty != 5 {
		t.Errorf("best yes ask = %+v ok=%v", ask, ok)
	}
	y, n := b.Depth(2)
	if len(y) != 2 || len(n) != 2 {
		t.Errorf("Depth(2) = %d,%d", len(y), len(n))
	}
}

func TestDiffAndEqual(t *testing.T) {
	a := New()
	a.ApplySnapshot([]Level{{5000, 100}, {4900, 50}}, []Level{{4000, 10}})
	b := a.Clone()
	if !a.Equal(b) || len(a.Diff(b)) != 0 {
		t.Fatal("clone should be equal")
	}
	_ = b.ApplyDelta(Yes, 4900, -50)
	_ = b.ApplyDelta(No, 3000, 7)
	if a.Equal(b) {
		t.Fatal("should differ")
	}
	d := a.Diff(b)
	if len(d) != 2 {
		t.Fatalf("diff = %+v", d)
	}
	if d[0] != (LevelDiff{Yes, 4900, 50, 0}) || d[1] != (LevelDiff{No, 3000, 0, 7}) {
		t.Errorf("diff = %+v", d)
	}
}

// Shared fixtures, also consumed by python/tests/test_book.py.

type fixtureFile struct {
	Cases []fixtureCase `json:"cases"`
}

type fixtureCase struct {
	Name     string            `json:"name"`
	Messages []kalshi.Envelope `json:"messages"`
	Expected *struct {
		Yes []kalshi.PriceLevel `json:"yes"`
		No  []kalshi.PriceLevel `json:"no"`
	} `json:"expected"`
	Top *struct {
		Bid, Ask, Spread, Mid *string
	} `json:"top"`
	ExpectError string `json:"expect_error"`
}

func TestSharedFixtures(t *testing.T) {
	raw, err := os.ReadFile(filepath.Join("..", "..", "testdata", "book_cases.json"))
	if err != nil {
		t.Fatal(err)
	}
	var f fixtureFile
	if err := json.Unmarshal(raw, &f); err != nil {
		t.Fatal(err)
	}
	for _, c := range f.Cases {
		t.Run(c.Name, func(t *testing.T) {
			b := New()
			var applyErr error
			for _, env := range c.Messages {
				switch env.Type {
				case kalshi.TypeOrderbookSnapshot:
					var m kalshi.OrderbookSnapshotMsg
					if err := env.Decode(&m); err != nil {
						t.Fatal(err)
					}
					applyErr = b.ApplySnapshotMsg(&m)
				case kalshi.TypeOrderbookDelta:
					var m kalshi.OrderbookDeltaMsg
					if err := env.Decode(&m); err != nil {
						t.Fatal(err)
					}
					applyErr = b.ApplyDeltaMsg(&m)
				default:
					t.Fatalf("unexpected message type %q", env.Type)
				}
				if applyErr != nil {
					break
				}
			}
			if c.ExpectError != "" {
				if c.ExpectError == "negative" && !errors.Is(applyErr, ErrNegativeQty) {
					t.Fatalf("want ErrNegativeQty, got %v", applyErr)
				}
				return
			}
			if applyErr != nil {
				t.Fatal(applyErr)
			}
			want, err := FromLevels(c.Expected.Yes, c.Expected.No)
			if err != nil {
				t.Fatal(err)
			}
			if !b.Equal(want) {
				t.Errorf("book mismatch: %+v", b.Diff(want))
			}
			if c.Top != nil {
				top := b.Top()
				checkOpt(t, "bid", c.Top.Bid, top.HasBid, top.Bid.Price)
				checkOpt(t, "ask", c.Top.Ask, top.HasAsk, top.Ask.Price)
				sp, ok := top.Spread()
				checkOpt(t, "spread", c.Top.Spread, ok, sp)
				mid, ok := top.Mid()
				checkOpt(t, "mid", c.Top.Mid, ok, mid)
			}
		})
	}
}

func checkOpt(t *testing.T, name string, want *string, ok bool, got Price) {
	t.Helper()
	if want == nil {
		if ok {
			t.Errorf("%s: want none, got %s", name, got)
		}
		return
	}
	if !ok {
		t.Errorf("%s: want %s, got none", name, *want)
		return
	}
	if got.String() != *want {
		t.Errorf("%s: want %s, got %s", name, *want, got)
	}
}
