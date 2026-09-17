package quoter

import (
	"testing"
	"time"

	"github.com/laneshetron/kalshi/internal/book"
)

var t0 = time.Date(2026, 9, 16, 18, 0, 0, 0, time.UTC)

func mkBook(yesPx, yesQty, noPx, noQty int) *book.Book {
	b := book.New()
	b.ApplySnapshot(
		[]book.Level{{Price: book.Price(yesPx), Qty: book.Qty(yesQty)}},
		[]book.Level{{Price: book.Price(noPx), Qty: book.Qty(noQty)}},
	)
	return b
}

func base() (Params, Inputs) {
	p := Params{Size: 100 * 100, MaxPos: 200 * 100, StopBefore: 5 * time.Minute, SignalMove: 2}
	in := Inputs{
		Now:       t0,
		Book:      mkBook(5000, 300000, 4900, 250000), // 50c bid, 51c ask (NO bid at 49c), 1c spread
		Orders:    map[book.Side]*OrderView{},
		CloseAt:   t0.Add(10 * time.Minute),
		Strike:    76000,
		Spot:      &SpotState{},
		Available: -1, // unknown: no capital sizing
	}
	return p, in
}

func kinds(as []Action) (places, cancels int) {
	for _, a := range as {
		if a.Kind == Place {
			places++
		} else {
			cancels++
		}
	}
	return
}

func TestJoinsBothSidesAtTouch(t *testing.T) {
	p, in := base()
	s := NewStrategy(p)
	as := s.Decide(in)
	if pl, ca := kinds(as); pl != 2 || ca != 0 {
		t.Fatalf("want 2 places, got %v", as)
	}
	for _, a := range as {
		want := book.Price(5000)
		if a.Side == book.No {
			want = 4900
		}
		if a.Price != want || a.Qty != 10000 || a.Reason != "join" {
			t.Errorf("bad action %v", a)
		}
	}
}

func TestImprovesWhenSpreadWide(t *testing.T) {
	p, in := base()
	in.Book = mkBook(5000, 1000, 4800, 1000) // 50 bid / 52 ask: 2c spread
	as := NewStrategy(p).Decide(in)
	for _, a := range as {
		want := book.Price(5100)
		if a.Side == book.No {
			want = 4900
		}
		if a.Kind != Place || a.Price != want || a.Reason != "improve" {
			t.Errorf("bad action %v", a)
		}
	}
}

func TestHoldsWhenStaleOrEmpty(t *testing.T) {
	p, in := base()
	in.Stale = true
	if as := NewStrategy(p).Decide(in); len(as) != 0 {
		t.Errorf("stale book should hold, got %v", as)
	}
	in.Stale = false
	in.Book = book.New()
	if as := NewStrategy(p).Decide(in); len(as) != 0 {
		t.Errorf("empty book should hold, got %v", as)
	}
}

func TestEndgameCancelsAndStops(t *testing.T) {
	p, in := base()
	in.Orders[book.Yes] = &OrderView{ID: "a", Side: book.Yes, Price: 5000, Qty: 10000, State: Resting}
	in.Now = in.CloseAt.Add(-4 * time.Minute)
	as := NewStrategy(p).Decide(in)
	if pl, ca := kinds(as); pl != 0 || ca != 1 || as[0].Reason != "endgame" {
		t.Fatalf("want one endgame cancel, got %v", as)
	}
}

func TestPositionLimitBlocksOneSide(t *testing.T) {
	p, in := base()
	in.Pos = 150 * 100 // long 150 with max 200 and size 100: no more buying YES
	as := NewStrategy(p).Decide(in)
	if len(as) != 1 || as[0].Side != book.No || as[0].Kind != Place {
		t.Fatalf("want only a NO place, got %v", as)
	}
	in.Pos = -150 * 100
	as = NewStrategy(p).Decide(in)
	if len(as) != 1 || as[0].Side != book.Yes {
		t.Fatalf("want only a YES place, got %v", as)
	}
}

func TestRepricesWhenTouchMoves(t *testing.T) {
	p, in := base()
	in.Orders[book.Yes] = &OrderView{ID: "a", Side: book.Yes, Price: 4900, Qty: 10000, State: Resting} // touch is now 50c
	as := NewStrategy(p).Decide(in)
	var sawCancel, sawNoPlace bool
	for _, a := range as {
		if a.Kind == Cancel && a.Side == book.Yes && a.Reason == "reprice" {
			sawCancel = true
		}
		if a.Kind == Place && a.Side == book.Yes {
			t.Errorf("must not place YES until the cancel lands: %v", a)
		}
		if a.Kind == Place && a.Side == book.No {
			sawNoPlace = true
		}
	}
	if !sawCancel || !sawNoPlace {
		t.Fatalf("want reprice cancel + NO place, got %v", as)
	}
	// once the cancel is pending, still no place on that side
	in.Orders[book.Yes].State = PendingCancel
	for _, a := range NewStrategy(p).Decide(in) {
		if a.Side == book.Yes {
			t.Errorf("no YES action while cancel pending, got %v", a)
		}
	}
}

func TestSignalPullsStaleSideAndCoolsDown(t *testing.T) {
	p, in := base()
	s := NewStrategy(p)
	in.Orders[book.No] = &OrderView{ID: "n", Side: book.No, Price: 4900, Qty: 10000, State: Resting}
	in.Orders[book.Yes] = &OrderView{ID: "y", Side: book.Yes, Price: 5000, Qty: 10000, State: Resting}
	sp := in.Spot
	sp.OnCoinbaseQuote(t0.Add(-900*time.Millisecond), time.Time{}, 76000, 76001, 1, 1)
	sp.OnCoinbaseQuote(t0, time.Time{}, 76003, 76004, 1, 1) // +$3 in under 1s: spot up
	as := s.OnSpotTick(in)
	if len(as) != 1 || as[0].Kind != Cancel || as[0].Side != book.No || as[0].Reason != "signal" {
		t.Fatalf("spot up should cancel the NO bid (our ask), got %v", as)
	}
	// during cooldown the NO side must not be re-quoted, YES untouched
	delete(in.Orders, book.No)
	in.Now = t0.Add(500 * time.Millisecond)
	for _, a := range s.Decide(in) {
		if a.Side == book.No {
			t.Errorf("NO side should be blocked during cooldown, got %v", a)
		}
	}
	in.Now = t0.Add(1100 * time.Millisecond)
	pl, _ := kinds(s.Decide(in))
	if pl != 1 { // YES already resting at the touch; NO re-quoted
		t.Errorf("after cooldown NO should be re-placed, got %v", s.Decide(in))
	}
	// a down move flags the YES side instead
	sp.OnCoinbaseQuote(t0.Add(1500*time.Millisecond), time.Time{}, 76003, 76004, 1, 1)
	sp.OnCoinbaseQuote(t0.Add(2*time.Second), time.Time{}, 75990, 75991, 1, 1)
	in.Now = t0.Add(2 * time.Second)
	as = s.OnSpotTick(in)
	if len(as) != 1 || as[0].Side != book.Yes {
		t.Fatalf("spot down should cancel the YES bid, got %v", as)
	}
}

func TestSmallMoveIsNotASignal(t *testing.T) {
	p, in := base()
	s := NewStrategy(p)
	in.Orders[book.No] = &OrderView{ID: "n", Side: book.No, Price: 4900, Qty: 10000, State: Resting}
	in.Spot.OnCoinbaseQuote(t0.Add(-500*time.Millisecond), time.Time{}, 76000, 76001, 1, 1)
	in.Spot.OnCoinbaseQuote(t0, time.Time{}, 76001, 76002, 1, 1)
	if as := s.OnSpotTick(in); len(as) != 0 {
		t.Fatalf("$1 move must not trigger, got %v", as)
	}
}

func TestGreeksCapBlocksBothSides(t *testing.T) {
	p, in := base()
	cap := 0.05
	p.GreeksCap = &cap
	// a jittery BRTI series near the strike with 1 minute to close: delta*sigma10 is large
	in.CloseAt = t0.Add(6 * time.Minute) // > stop_before so the endgame rule doesn't fire
	for i := 0; i < 200; i++ {
		v := 76000.0
		if i%2 == 0 {
			v = 76040
		}
		in.Spot.OnBRTI(t0.Add(time.Duration(i-200)*200*time.Millisecond), v)
	}
	g, ok := in.Spot.DeltaSigma10(in.Strike, in.CloseAt)
	if !ok || g < cap {
		t.Fatalf("test setup: expected large greeks, got %v ok=%v", g, ok)
	}
	s := NewStrategy(p)
	if as := s.Decide(in); len(as) != 0 || s.Vetoes["greeks"] == 0 {
		t.Fatalf("greeks cap should block, got %v", as)
	}
	// far from the strike the cap does not bind
	in.Strike = 70000
	if pl, _ := kinds(s.Decide(in)); pl != 2 {
		t.Fatalf("far from strike should quote both sides")
	}
}

func TestJoinGateVetoesNegativeEdge(t *testing.T) {
	m, err := LoadEdgeModel("testdata/tables.json")
	if err != nil {
		t.Fatal(err)
	}
	p, in := base()
	theta := 0.0
	p.JoinTheta = &theta
	in.Edge = m
	// find a touch state the fitted tables score negative for a YES join, and one they score positive
	var neg, pos *book.Book
	for _, yq := range []int{50, 300, 1500, 6000} {
		for _, nq := range []int{50, 300, 1500, 6000} {
			imb := float64(nq-yq) / float64(nq+yq)
			e, ok := m.Edge("yes", imb, nil, 10, float64(yq))
			if !ok {
				continue
			}
			if e < 0 && neg == nil {
				neg = mkBook(5000, yq*100, 4900, nq*100)
			}
			if e > 0 && pos == nil {
				pos = mkBook(5000, yq*100, 4900, nq*100)
			}
		}
	}
	if neg == nil || pos == nil {
		t.Fatalf("test setup: need both a negative and a positive YES-join state (neg=%v pos=%v)", neg != nil, pos != nil)
	}
	in.Book = neg
	s := NewStrategy(p)
	for _, a := range s.Decide(in) {
		if a.Side == book.Yes {
			t.Errorf("negative-edge YES join should be vetoed, got %v", a)
		}
	}
	if s.Vetoes["join"] == 0 {
		t.Errorf("expected a join veto")
	}
	in.Book = pos
	var placedYes bool
	for _, a := range NewStrategy(p).Decide(in) {
		if a.Side == book.Yes && a.Kind == Place {
			placedYes = true
		}
	}
	if !placedYes {
		t.Errorf("positive-edge YES join should be placed")
	}
	// improving (q ahead = 0) is the front of the queue: allowed
	in.Book = mkBook(5000, 6000*100, 4800, 500*100)
	if pl, _ := kinds(NewStrategy(p).Decide(in)); pl != 2 {
		t.Errorf("improving quotes should pass the gate")
	}
}

func TestPriceBounds(t *testing.T) {
	p, in := base()
	in.Book = mkBook(100, 1000, 9800, 1000) // YES bid 1c, NO bid 98c (YES ask 2c): improving would be 2c bid / 99c NO... bounds ok
	as := NewStrategy(p).Decide(in)
	for _, a := range as {
		if a.Price < Tick || a.Price > book.OneDollar-Tick {
			t.Errorf("out of bounds %v", a)
		}
	}
	in.Book = mkBook(100, 1000, 9900, 1000) // 1c bid, NO bid 99c: 0 spread... crossed-ish; joining at 1c and 99c is allowed
	as = NewStrategy(p).Decide(in)
	if len(as) != 2 {
		t.Errorf("expected joins at the bounds, got %v", as)
	}
}

func TestCapitalSizing(t *testing.T) {
	if q := AffordableQty(100*100, 5000, 4.0); q != 8*100 { // $4 at 50c = 8 contracts
		t.Fatalf("affordable = %v, want 8.00", q)
	}
	if q := AffordableQty(100*100, 5000, 1000); q != 100*100 {
		t.Fatalf("plenty of capital should return the wanted size, got %v", q)
	}
	if q := AffordableQty(100*100, 5000, 0.3); q != 0 {
		t.Fatalf("less than one contract's collateral should return 0, got %v", q)
	}
	p, in := base()
	in.Available = 5.0 // $5 split across both sides: $2.50 each -> 5 YES at 50c, 5 NO at 49c
	as := NewStrategy(p).Decide(in)
	if len(as) != 2 || as[0].Qty != 5*100 || as[1].Qty != 5*100 {
		t.Fatalf("with $5 want 5 + 5, got %v", as)
	}
	// with YES already resting at the touch, all the free capital goes to the NO side
	in.Orders[book.Yes] = &OrderView{ID: "y", Side: book.Yes, Price: 5000, Qty: 500, State: Resting}
	as = NewStrategy(p).Decide(in)
	if len(as) != 1 || as[0].Side != book.No || as[0].Qty != 10*100 {
		t.Fatalf("with YES resting, $5 should buy 10 NO at 49c, got %v", as)
	}
	delete(in.Orders, book.Yes)
	in.Available = 0.2
	s := NewStrategy(p)
	if as := s.Decide(in); len(as) != 0 || s.Vetoes["capital"] == 0 {
		t.Fatalf("no capital: no orders, got %v", as)
	}
}
