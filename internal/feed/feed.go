// Package feed keeps a set of Kalshi market subscriptions alive and applies
// their orderbook messages to local books. It owns reconnection, per-sid
// sequence tracking, gap recovery, and raw recording.
package feed

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"math/rand/v2"
	"sort"
	"sync"
	"sync/atomic"
	"time"

	"github.com/laneshetron/kalshi/internal/book"
	"github.com/laneshetron/kalshi/internal/kalshi"
	"github.com/laneshetron/kalshi/internal/recorder"
)

// marketScoped lists channels that take a market_tickers parameter and so
// participate in add/delete updates.
var marketScoped = map[string]bool{
	kalshi.ChannelOrderbookDelta: true,
	kalshi.ChannelTicker:         true,
	kalshi.ChannelTrade:          true,
}

// Config configures a Feed.
type Config struct {
	Env      kalshi.Env
	Signer   *kalshi.Signer
	Recorder *recorder.Recorder
	Channels []string
	IndexIDs []string // for cfbenchmarks channels
	Logger   *slog.Logger

	// Reconnect backoff bounds.
	MinBackoff, MaxBackoff time.Duration
	// CommandTimeout bounds each subscribe/update round trip.
	CommandTimeout time.Duration
}

type marketState struct {
	book   *book.Book
	stale  bool // true until a snapshot arrives after connect/gap
	lastRx time.Time
	lastTs int64 // exchange ts_ms of the last applied delta
	sid    int
}

type subState struct {
	channel string
	sid     int
	lastSeq uint64
	hasSeq  bool
}

// Feed is safe for concurrent use.
type Feed struct {
	cfg Config
	log *slog.Logger

	mu      sync.RWMutex
	desired map[string]struct{} // tickers we want subscribed
	markets map[string]*marketState
	subs    map[int]*subState // by sid
	conn    *kalshi.Conn
	connGen uint64
	indexes map[string]IndexValue // latest value per index id

	// stats
	connected   atomic.Bool
	msgCount    atomic.Uint64
	gapCount    atomic.Uint64
	reconnects  atomic.Uint64
	lastMsgNs   atomic.Int64
	connectedAt atomic.Int64
}

// New creates a feed; call Run to start it.
func New(cfg Config) *Feed {
	if cfg.Logger == nil {
		cfg.Logger = slog.Default()
	}
	if cfg.MinBackoff == 0 {
		cfg.MinBackoff = time.Second
	}
	if cfg.MaxBackoff == 0 {
		cfg.MaxBackoff = 30 * time.Second
	}
	if cfg.CommandTimeout == 0 {
		cfg.CommandTimeout = 10 * time.Second
	}
	return &Feed{
		cfg:     cfg,
		log:     cfg.Logger,
		desired: map[string]struct{}{},
		markets: map[string]*marketState{},
		subs:    map[int]*subState{},
		indexes: map[string]IndexValue{},
	}
}

// IndexValue is the latest tick of a CF Benchmarks index.
type IndexValue struct {
	Value  string    `json:"value"`
	Avg60s string    `json:"avg_60s,omitempty"`
	Time   time.Time `json:"time"`
	Rx     time.Time `json:"rx"`
}

// Run connects and processes messages until ctx is cancelled, reconnecting
// with backoff on failure.
func (f *Feed) Run(ctx context.Context) error {
	backoff := f.cfg.MinBackoff
	for {
		err := f.runOnce(ctx)
		if ctx.Err() != nil {
			return ctx.Err()
		}
		f.log.Warn("connection ended", "err", err, "retry_in", backoff)
		select {
		case <-time.After(jitter(backoff)):
		case <-ctx.Done():
			return ctx.Err()
		}
		backoff = min(backoff*2, f.cfg.MaxBackoff)
		f.reconnects.Add(1)
	}
}

func jitter(d time.Duration) time.Duration {
	return d/2 + time.Duration(rand.Int64N(int64(d)))
}

func (f *Feed) runOnce(ctx context.Context) error {
	dialCtx, cancel := context.WithTimeout(ctx, 20*time.Second)
	conn, err := kalshi.Dial(dialCtx, f.cfg.Env, f.cfg.Signer, kalshi.DialOptions{})
	cancel()
	if err != nil {
		return err
	}
	defer conn.Close()

	f.mu.Lock()
	f.conn = conn
	f.connGen++
	gen := f.connGen
	f.subs = map[int]*subState{}
	for _, m := range f.markets {
		m.stale = true
	}
	tickers := f.desiredLocked()
	f.mu.Unlock()

	f.connected.Store(true)
	f.connectedAt.Store(time.Now().UnixNano())
	defer func() {
		f.connected.Store(false)
		f.mu.Lock()
		if f.connGen == gen {
			f.conn = nil
		}
		for _, m := range f.markets {
			m.stale = true
		}
		f.mu.Unlock()
		f.record(recorder.EventDisconnect, map[string]any{"gen": gen, "err": errString(conn.Err())})
	}()
	f.record(recorder.EventConnect, map[string]any{"gen": gen, "url": f.cfg.Env.WSURL()})
	f.log.Info("connected", "env", f.cfg.Env, "markets", len(tickers))

	// Subscribe. The read loop below handles the messages these commands
	// produce because Conn delivers responses on both paths.
	go func() {
		if err := f.subscribeAll(ctx, conn, tickers); err != nil {
			f.log.Error("subscribe failed; dropping connection", "err", err)
			conn.Close()
		}
	}()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case m, ok := <-conn.Messages():
			if !ok {
				return fmt.Errorf("read: %w", conn.Err())
			}
			f.handle(ctx, conn, m)
		}
	}
}

func errString(err error) string {
	if err == nil {
		return ""
	}
	return err.Error()
}

func (f *Feed) subscribeAll(ctx context.Context, conn *kalshi.Conn, tickers []string) error {
	for _, ch := range f.cfg.Channels {
		var t []string
		p := kalshi.SubscribeParams{Channels: []string{ch}}
		switch {
		case marketScoped[ch]:
			if len(tickers) == 0 {
				continue // nothing to subscribe yet; SetMarkets will handle it
			}
			t = tickers
			p.MarketTickers = t
		case kalshi.IndexChannels[ch]:
			p.IndexIDs = f.cfg.IndexIDs
		}
		cctx, cancel := context.WithTimeout(ctx, f.cfg.CommandTimeout)
		sid, err := conn.Subscribe(cctx, p)
		cancel()
		if err != nil {
			return fmt.Errorf("subscribe %s: %w", ch, err)
		}
		f.mu.Lock()
		if existing := f.subs[sid]; existing != nil {
			existing.channel = ch // data arrived before the subscribed response
		} else {
			f.subs[sid] = &subState{channel: ch, sid: sid}
		}
		if ch == kalshi.ChannelOrderbookDelta {
			for _, tk := range t {
				f.marketLocked(tk).sid = sid
			}
		}
		f.mu.Unlock()
		f.record(recorder.EventSubscribed, map[string]any{"channel": ch, "sid": sid, "markets": len(t)})
		f.log.Info("subscribed", "channel", ch, "sid", sid, "markets", len(t))
	}
	return nil
}

func (f *Feed) desiredLocked() []string {
	out := make([]string, 0, len(f.desired))
	for t := range f.desired {
		out = append(out, t)
	}
	sort.Strings(out)
	return out
}

func (f *Feed) marketLocked(ticker string) *marketState {
	m := f.markets[ticker]
	if m == nil {
		m = &marketState{book: book.New(), stale: true}
		f.markets[ticker] = m
	}
	return m
}

func (f *Feed) record(event string, fields map[string]any) {
	if f.cfg.Recorder == nil {
		return
	}
	if err := f.cfg.Recorder.WriteLocal(event, fields); err != nil {
		f.log.Error("record local event", "event", event, "err", err)
	}
}

// handle records then applies one message.
func (f *Feed) handle(ctx context.Context, conn *kalshi.Conn, m kalshi.RawMessage) {
	f.msgCount.Add(1)
	f.lastMsgNs.Store(m.Rx.UnixNano())
	if f.cfg.Recorder != nil {
		if err := f.cfg.Recorder.Write(m.Rx, m.Data); err != nil {
			f.log.Error("record message", "err", err)
		}
	}
	var env kalshi.Envelope
	if err := env.UnmarshalFrom(m.Data); err != nil {
		f.log.Warn("undecodable message", "err", err)
		return
	}
	if env.Sid == 0 {
		return // subscribed/error responses without a sid; handled by Conn.Do
	}

	f.mu.Lock()
	defer f.mu.Unlock()
	sub := f.subs[env.Sid]
	if sub == nil {
		// Data for a sid we haven't registered yet (subscribe response still
		// in flight). Register it so seq tracking starts now.
		sub = &subState{channel: env.Type, sid: env.Sid}
		if env.Type == kalshi.TypeOrderbookSnapshot || env.Type == kalshi.TypeOrderbookDelta {
			sub.channel = kalshi.ChannelOrderbookDelta
		}
		f.subs[env.Sid] = sub
	}
	// Every message on a sid consumes a seq, including ok/unsubscribed
	// responses to update_subscription.
	if env.Seq != 0 {
		if sub.hasSeq && env.Seq != sub.lastSeq+1 {
			f.onGapLocked(ctx, conn, sub, env)
		}
		sub.lastSeq, sub.hasSeq = env.Seq, true
	}

	switch env.Type {
	case kalshi.TypeOrderbookSnapshot:
		var s kalshi.OrderbookSnapshotMsg
		if err := env.Decode(&s); err != nil {
			f.log.Warn("bad snapshot", "err", err)
			return
		}
		ms := f.marketLocked(s.MarketTicker)
		if err := ms.book.ApplySnapshotMsg(&s); err != nil {
			f.log.Warn("apply snapshot", "ticker", s.MarketTicker, "err", err)
			return
		}
		ms.stale, ms.lastRx, ms.sid = false, m.Rx, env.Sid
	case kalshi.TypeOrderbookDelta:
		var d kalshi.OrderbookDeltaMsg
		if err := env.Decode(&d); err != nil {
			f.log.Warn("bad delta", "err", err)
			return
		}
		ms := f.marketLocked(d.MarketTicker)
		if ms.stale {
			return // waiting for a snapshot
		}
		if err := ms.book.ApplyDeltaMsg(&d); err != nil {
			if errors.Is(err, book.ErrNegativeQty) {
				f.log.Warn("book diverged", "ticker", d.MarketTicker, "price", d.PriceDollars, "delta", d.DeltaFP)
				f.resyncLocked(ctx, conn, sub, []string{d.MarketTicker}, "negative_qty")
				return
			}
			f.log.Warn("apply delta", "ticker", d.MarketTicker, "err", err)
			return
		}
		ms.lastRx, ms.lastTs = m.Rx, d.TsMs
	case kalshi.TypeCFBenchmarksValue, kalshi.TypeCFBenchmarks5Hz:
		var iv kalshi.IndexValueMsg
		if err := env.Decode(&iv); err != nil {
			return
		}
		var tick kalshi.IndexTick
		if json.Unmarshal([]byte(iv.Data), &tick) != nil {
			return
		}
		v := IndexValue{Value: tick.Value, Time: time.UnixMilli(tick.Time), Rx: m.Rx}
		if iv.Avg60s != nil {
			v.Avg60s = iv.Avg60s.Value
		} else if prev, ok := f.indexes[iv.IndexID]; ok {
			v.Avg60s = prev.Avg60s // keep the 1/s channel's average alongside 5hz ticks
		}
		f.indexes[iv.IndexID] = v
	}
}

// onGapLocked handles a sequence gap on sub: every market on that sid is
// stale until a fresh snapshot arrives.
func (f *Feed) onGapLocked(ctx context.Context, conn *kalshi.Conn, sub *subState, env kalshi.Envelope) {
	f.gapCount.Add(1)
	f.log.Warn("sequence gap", "channel", sub.channel, "sid", sub.sid, "expected", sub.lastSeq+1, "got", env.Seq)
	f.record(recorder.EventGap, map[string]any{"sid": sub.sid, "channel": sub.channel, "expected": sub.lastSeq + 1, "got": env.Seq})
	if sub.channel != kalshi.ChannelOrderbookDelta {
		return
	}
	var tickers []string
	for t, m := range f.markets {
		if m.sid == sub.sid {
			tickers = append(tickers, t)
		}
	}
	f.resyncLocked(ctx, conn, sub, tickers, "seq_gap")
}

// resyncLocked marks tickers stale and asks the server for fresh snapshots on
// the same subscription. If that fails the connection is dropped so Run
// rebuilds everything from scratch.
func (f *Feed) resyncLocked(ctx context.Context, conn *kalshi.Conn, sub *subState, tickers []string, reason string) {
	for _, t := range tickers {
		f.marketLocked(t).stale = true
	}
	f.record(recorder.EventResync, map[string]any{"sid": sub.sid, "reason": reason, "markets": tickers})
	sid := sub.sid
	go func() {
		cctx, cancel := context.WithTimeout(ctx, f.cfg.CommandTimeout)
		defer cancel()
		if err := conn.RequestSnapshot(cctx, sid, tickers); err != nil {
			f.log.Error("get_snapshot failed; dropping connection", "sid", sid, "err", err)
			conn.Close()
		}
	}()
}

// SetMarkets replaces the desired market set, issuing add/delete updates on
// the live connection. Markets that are no longer desired keep their last
// book but are marked stale.
func (f *Feed) SetMarkets(ctx context.Context, tickers []string) error {
	want := make(map[string]struct{}, len(tickers))
	for _, t := range tickers {
		want[t] = struct{}{}
	}
	f.mu.Lock()
	add, del := []string{}, []string{}
	for t := range want {
		if _, ok := f.desired[t]; !ok {
			add = append(add, t)
		}
	}
	for t := range f.desired {
		if _, ok := want[t]; !ok {
			del = append(del, t)
			if m := f.markets[t]; m != nil {
				m.stale = true
			}
		}
	}
	sort.Strings(add)
	sort.Strings(del)
	f.desired = want
	conn := f.conn
	subs := make([]*subState, 0, len(f.subs))
	for _, s := range f.subs {
		if marketScoped[s.channel] {
			subs = append(subs, s)
		}
	}
	f.mu.Unlock()

	if len(add)+len(del) > 0 {
		f.record(recorder.EventMarketsSync, map[string]any{"add": add, "delete": del, "total": len(want)})
		f.log.Info("markets changed", "add", len(add), "delete", len(del), "total", len(want))
	}
	if conn == nil || len(add)+len(del) == 0 {
		return nil
	}
	if len(subs) == 0 {
		// Market-scoped channels were skipped at connect (no markets then).
		return f.subscribeAll(ctx, conn, f.snapshotDesired())
	}
	var errs []error
	for _, s := range subs {
		for action, list := range map[string][]string{kalshi.ActionAddMarkets: add, kalshi.ActionDeleteMarkets: del} {
			if len(list) == 0 {
				continue
			}
			cctx, cancel := context.WithTimeout(ctx, f.cfg.CommandTimeout)
			err := conn.UpdateSubscription(cctx, s.sid, action, list)
			cancel()
			if err != nil {
				errs = append(errs, fmt.Errorf("%s %s sid %d: %w", action, s.channel, s.sid, err))
				continue
			}
			if s.channel == kalshi.ChannelOrderbookDelta && action == kalshi.ActionAddMarkets {
				f.mu.Lock()
				for _, t := range list {
					f.marketLocked(t).sid = s.sid
				}
				f.mu.Unlock()
			}
		}
	}
	return errors.Join(errs...)
}

func (f *Feed) snapshotDesired() []string {
	f.mu.RLock()
	defer f.mu.RUnlock()
	return f.desiredLocked()
}

// BookView is a read-only copy of one market's state.
type BookView struct {
	Ticker string
	Book   *book.Book
	Stale  bool
	LastRx time.Time
	LastTs int64
}

// Book returns a copy of the market's current book.
func (f *Feed) Book(ticker string) (BookView, bool) {
	f.mu.RLock()
	defer f.mu.RUnlock()
	m := f.markets[ticker]
	if m == nil {
		return BookView{}, false
	}
	return BookView{Ticker: ticker, Book: m.book.Clone(), Stale: m.stale, LastRx: m.lastRx, LastTs: m.lastTs}, true
}

// Markets lists tracked tickers, sorted.
func (f *Feed) Markets() []string {
	f.mu.RLock()
	defer f.mu.RUnlock()
	out := make([]string, 0, len(f.markets))
	for t := range f.markets {
		out = append(out, t)
	}
	sort.Strings(out)
	return out
}

// Stats is a point-in-time summary for the status endpoint.
type Stats struct {
	Connected   bool                  `json:"connected"`
	ConnectedAt time.Time             `json:"connected_at,omitempty"`
	Reconnects  uint64                `json:"reconnects"`
	Messages    uint64                `json:"messages"`
	Gaps        uint64                `json:"gaps"`
	LastMessage time.Time             `json:"last_message,omitempty"`
	Markets     int                   `json:"markets"`
	Stale       []string              `json:"stale_markets"`
	Subs        map[int]SubStats      `json:"subscriptions"`
	Indexes     map[string]IndexValue `json:"indexes"`
}

// SubStats describes one subscription.
type SubStats struct {
	Channel string `json:"channel"`
	LastSeq uint64 `json:"last_seq"`
}

// Stats returns current counters.
func (f *Feed) Stats() Stats {
	f.mu.RLock()
	defer f.mu.RUnlock()
	s := Stats{
		Connected:  f.connected.Load(),
		Reconnects: f.reconnects.Load(),
		Messages:   f.msgCount.Load(),
		Gaps:       f.gapCount.Load(),
		Markets:    len(f.markets),
		Stale:      []string{},
		Subs:       map[int]SubStats{},
		Indexes:    map[string]IndexValue{},
	}
	for k, v := range f.indexes {
		s.Indexes[k] = v
	}
	if ns := f.connectedAt.Load(); ns != 0 && s.Connected {
		s.ConnectedAt = time.Unix(0, ns)
	}
	if ns := f.lastMsgNs.Load(); ns != 0 {
		s.LastMessage = time.Unix(0, ns)
	}
	for t, m := range f.markets {
		if m.stale {
			s.Stale = append(s.Stale, t)
		}
	}
	sort.Strings(s.Stale)
	for sid, sub := range f.subs {
		s.Subs[sid] = SubStats{Channel: sub.channel, LastSeq: sub.lastSeq}
	}
	return s
}

// CrossCheck fetches the REST orderbook for every non-stale market, records
// it as a rest_snapshot event, and returns the tickers whose live book
// differs. Small transient differences are expected because REST and the
// stream are not atomically consistent.
func (f *Feed) CrossCheck(ctx context.Context, rest *kalshi.REST) (mismatched []string, err error) {
	for _, t := range f.Markets() {
		ob, err := rest.GetOrderbook(ctx, t)
		if err != nil {
			f.log.Warn("rest orderbook", "ticker", t, "err", err)
			continue
		}
		f.record(recorder.EventRESTSnapshot, map[string]any{"market_ticker": t, "yes": ob.Yes, "no": ob.No})
		want, err := book.FromLevels(ob.Yes, ob.No)
		if err != nil {
			f.log.Warn("rest orderbook parse", "ticker", t, "err", err)
			continue
		}
		v, ok := f.Book(t)
		if !ok || v.Stale {
			continue
		}
		if diff := v.Book.Diff(want); len(diff) > 0 {
			mismatched = append(mismatched, t)
			f.log.Warn("rest/live mismatch", "ticker", t, "levels", len(diff), "first", fmt.Sprintf("%s %s have=%s want=%s", diff[0].Side, diff[0].Price, diff[0].Have, diff[0].Want))
		}
	}
	return mismatched, ctx.Err()
}
