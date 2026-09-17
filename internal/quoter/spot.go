package quoter

import (
	"math"
	"time"
)

// SpotState tracks the upstream inputs the strategy reads: the Coinbase BTC
// top of book (signal and microprice) and the BRTI 5hz index (Greeks).
// Mirrors alpha.SpotState / sim.Context in the Python research code.
type SpotState struct {
	cbBid, cbAsk     float64
	cbBidSz, cbAskSz float64
	cbLastRx         time.Time
	cbLastLagMs      float64
	mids             []tick // Coinbase mids, trailing window
	brti             []tick // BRTI values, trailing 300s
	brtiLast         float64
	nBrti            int
	vol              float64 // realized vol per sqrt(second), cached
	haveVol          bool
}

type tick struct {
	rx time.Time
	v  float64
}

const (
	midWindow  = 35 * time.Second
	volWindow  = 300 * time.Second
	volRefresh = 25 // BRTI ticks between vol refreshes (~5s at 5hz)
)

// OnCoinbaseQuote records a top-of-book update. exchTs is the exchange
// timestamp (for feed-lag accounting); sizes may be zero if unknown.
func (s *SpotState) OnCoinbaseQuote(rx time.Time, exchTs time.Time, bid, ask, bidSz, askSz float64) {
	s.cbBid, s.cbAsk = bid, ask
	if bidSz > 0 || askSz > 0 {
		s.cbBidSz, s.cbAskSz = bidSz, askSz
	}
	s.cbLastRx = rx
	if !exchTs.IsZero() {
		s.cbLastLagMs = float64(rx.Sub(exchTs).Microseconds()) / 1e3
	}
	s.mids = append(s.mids, tick{rx, (bid + ask) / 2})
	cut := rx.Add(-midWindow)
	i := 0
	for i < len(s.mids) && s.mids[i].rx.Before(cut) {
		i++
	}
	s.mids = s.mids[i:]
}

// CoinbaseMid returns the current mid, ok=false before the first quote.
func (s *SpotState) CoinbaseMid() (float64, bool) {
	if s.cbBid == 0 || s.cbAsk == 0 {
		return 0, false
	}
	return (s.cbBid + s.cbAsk) / 2, true
}

// MidAgo returns the mid as of d before rx (the oldest tick inside the window), ok=false if none.
func (s *SpotState) MidAgo(rx time.Time, d time.Duration) (float64, bool) {
	cut := rx.Add(-d)
	for _, t := range s.mids {
		if !t.rx.Before(cut) {
			return t.v, true
		}
	}
	return 0, false
}

// Move1s is the signed Coinbase mid move over the trailing second ($), ok=false without history.
func (s *SpotState) Move1s(rx time.Time) (float64, bool) {
	mid, ok := s.CoinbaseMid()
	if !ok {
		return 0, false
	}
	ago, ok := s.MidAgo(rx, time.Second)
	if !ok {
		return 0, false
	}
	return mid - ago, true
}

// MicroUnsigned is the Coinbase microprice minus mid ($): positive = pressure up. nil if sizes unknown.
func (s *SpotState) MicroUnsigned() *float64 {
	if s.cbBidSz+s.cbAskSz <= 0 || s.cbBid == 0 {
		return nil
	}
	mid := (s.cbBid + s.cbAsk) / 2
	m := (s.cbBid*s.cbAskSz+s.cbAsk*s.cbBidSz)/(s.cbBidSz+s.cbAskSz) - mid
	return &m
}

// CoinbaseLagMs is the delivery lag of the last Coinbase message (rx - exchange ts).
func (s *SpotState) CoinbaseLagMs() float64 { return s.cbLastLagMs }

// CoinbaseAge is how long since the last Coinbase message.
func (s *SpotState) CoinbaseAge(now time.Time) time.Duration {
	if s.cbLastRx.IsZero() {
		return time.Hour
	}
	return now.Sub(s.cbLastRx)
}

// OnBRTI records a 5hz index tick.
func (s *SpotState) OnBRTI(rx time.Time, v float64) {
	s.brti = append(s.brti, tick{rx, v})
	s.brtiLast = v
	cut := rx.Add(-volWindow)
	i := 0
	for i < len(s.brti) && s.brti[i].rx.Before(cut) {
		i++
	}
	s.brti = s.brti[i:]
	s.nBrti++
	if s.nBrti%volRefresh == 0 {
		s.vol, s.haveVol = s.realizedVol()
	}
}

// realizedVol is the std of log returns of the 5hz ticks in the window, per sqrt(second).
func (s *SpotState) realizedVol() (float64, bool) {
	if len(s.brti) < 30 {
		return 0, false
	}
	n := len(s.brti) - 1
	if n <= 10 {
		return 0, false
	}
	rets := make([]float64, n)
	mean := 0.0
	for i := 0; i < n; i++ {
		rets[i] = math.Log(s.brti[i+1].v / s.brti[i].v)
		mean += rets[i]
	}
	mean /= float64(n)
	ss := 0.0
	for _, r := range rets {
		ss += (r - mean) * (r - mean)
	}
	return math.Sqrt(ss/float64(n)) * math.Sqrt(5), true // population std, ticks are 5hz
}

// DeltaSigma10 is the contract price change (fraction of $1) for a 1-sigma
// spot move over 10s: phi(d) * sqrt(10/tau), with d = ln(S/K) / (sigma sqrt(tau)).
// ok=false without a strike, index value or vol estimate.
func (s *SpotState) DeltaSigma10(strike float64, closeAt time.Time) (float64, bool) {
	if strike <= 0 || s.brtiLast <= 0 || !s.haveVol || s.vol <= 0 || len(s.brti) == 0 {
		return 0, false
	}
	tau := closeAt.Sub(s.brti[len(s.brti)-1].rx).Seconds()
	if tau < 1 {
		tau = 1
	}
	d := math.Log(s.brtiLast/strike) / (s.vol * math.Sqrt(tau))
	return math.Exp(-d*d/2) / math.Sqrt(2*math.Pi) * math.Sqrt(10/tau), true
}
