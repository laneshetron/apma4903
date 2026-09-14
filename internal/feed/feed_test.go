package feed

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/json"
	"encoding/pem"
	"net/http"
	"net/http/httptest"
	"sort"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/coder/websocket"

	"github.com/laneshetron/kalshi/internal/book"
	"github.com/laneshetron/kalshi/internal/kalshi"
)

// fakeServer speaks enough of the Kalshi WS protocol to drive a Feed.
type fakeServer struct {
	t *testing.T

	mu     sync.Mutex
	conns  []*websocket.Conn
	cmds   []kalshi.Command // every command received, in order
	gotCmd chan kalshi.Command
	authOK bool
	seq    map[int]uint64 // last seq the server has emitted per sid (for ok responses)
}

func newFakeServer(t *testing.T) (*fakeServer, *httptest.Server) {
	fs := &fakeServer{t: t, gotCmd: make(chan kalshi.Command, 64), seq: map[int]uint64{}}
	srv := httptest.NewServer(http.HandlerFunc(fs.handle))
	t.Cleanup(srv.Close)
	return fs, srv
}

func (fs *fakeServer) handle(w http.ResponseWriter, r *http.Request) {
	if r.Header.Get(kalshi.HeaderKey) == "" || r.Header.Get(kalshi.HeaderSignature) == "" || r.Header.Get(kalshi.HeaderTimestamp) == "" {
		http.Error(w, "unauthorized", http.StatusUnauthorized)
		return
	}
	fs.mu.Lock()
	fs.authOK = true
	fs.mu.Unlock()
	c, err := websocket.Accept(w, r, nil)
	if err != nil {
		return
	}
	fs.mu.Lock()
	fs.conns = append(fs.conns, c)
	fs.mu.Unlock()
	ctx := context.Background()
	sid := 0
	for {
		_, data, err := c.Read(ctx)
		if err != nil {
			return
		}
		var cmd kalshi.Command
		var raw struct {
			ID     int             `json:"id"`
			Cmd    string          `json:"cmd"`
			Params json.RawMessage `json:"params"`
		}
		if err := json.Unmarshal(data, &raw); err != nil {
			fs.t.Errorf("bad command %s: %v", data, err)
			continue
		}
		cmd = kalshi.Command{ID: raw.ID, Cmd: raw.Cmd, Params: raw.Params}
		fs.mu.Lock()
		fs.cmds = append(fs.cmds, cmd)
		fs.mu.Unlock()
		switch raw.Cmd {
		case "subscribe":
			var p kalshi.SubscribeParams
			_ = json.Unmarshal(raw.Params, &p)
			sid++
			fs.send(c, map[string]any{"id": raw.ID, "type": "subscribed", "msg": map[string]any{"channel": p.Channels[0], "sid": sid}})
		case "update_subscription":
			var p kalshi.UpdateSubscriptionParams
			_ = json.Unmarshal(raw.Params, &p)
			if p.Action == kalshi.ActionGetSnapshot {
				break // Kalshi answers with snapshots only, no ok
			}
			// The ok consumes a seq on the sid, like the real server.
			fs.mu.Lock()
			fs.seq[p.Sids[0]]++
			seq := fs.seq[p.Sids[0]]
			fs.mu.Unlock()
			fs.send(c, map[string]any{"id": raw.ID, "type": "ok", "sid": p.Sids[0], "seq": seq, "msg": map[string]any{"market_tickers": []string{}}})
		case "unsubscribe":
			fs.send(c, map[string]any{"id": raw.ID, "type": "unsubscribed"})
		}
		fs.gotCmd <- cmd
	}
}

func (fs *fakeServer) send(c *websocket.Conn, v any) {
	b, _ := json.Marshal(v)
	b = append(b, '\n') // Kalshi frames end with a newline
	if err := c.Write(context.Background(), websocket.MessageText, b); err != nil {
		fs.t.Logf("server write: %v", err)
	}
}

func (fs *fakeServer) latest() *websocket.Conn {
	fs.mu.Lock()
	defer fs.mu.Unlock()
	return fs.conns[len(fs.conns)-1]
}

func (fs *fakeServer) waitCmd(t *testing.T, name string) kalshi.Command {
	t.Helper()
	deadline := time.After(5 * time.Second)
	for {
		select {
		case c := <-fs.gotCmd:
			if c.Cmd == name {
				return c
			}
		case <-deadline:
			t.Fatalf("timed out waiting for %s command", name)
		}
	}
}

func testSigner(t *testing.T) *kalshi.Signer {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal(err)
	}
	pemBytes := pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(key)})
	s, err := kalshi.NewSigner("test-key", pemBytes)
	if err != nil {
		t.Fatal(err)
	}
	return s
}

// track lets the fake server's ok responses continue the seq stream.
func (fs *fakeServer) track(m map[string]any) map[string]any {
	fs.mu.Lock()
	fs.seq[m["sid"].(int)] = m["seq"].(uint64)
	fs.mu.Unlock()
	return m
}

func snapshot(sid int, seq uint64, ticker string, yes, no [][2]string) map[string]any {
	return map[string]any{"type": "orderbook_snapshot", "sid": sid, "seq": seq, "msg": map[string]any{
		"market_ticker": ticker, "yes_dollars_fp": yes, "no_dollars_fp": no}}
}

func delta(sid int, seq uint64, ticker, side, price, d string) map[string]any {
	return map[string]any{"type": "orderbook_delta", "sid": sid, "seq": seq, "msg": map[string]any{
		"market_ticker": ticker, "price_dollars": price, "delta_fp": d, "side": side, "ts_ms": 1700000000000}}
}

func waitFor(t *testing.T, what string, cond func() bool) {
	t.Helper()
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		if cond() {
			return
		}
		time.Sleep(5 * time.Millisecond)
	}
	t.Fatalf("timed out waiting for %s", what)
}

func TestFeedSnapshotDeltaGapAndReconnect(t *testing.T) {
	fs, srv := newFakeServer(t)
	restore := kalshi.SetWSURLForTest(kalshi.Demo, "ws"+strings.TrimPrefix(srv.URL, "http"))
	defer restore()

	f := New(Config{
		Env: kalshi.Demo, Signer: testSigner(t),
		Channels:   []string{kalshi.ChannelOrderbookDelta},
		MinBackoff: 10 * time.Millisecond, MaxBackoff: 20 * time.Millisecond,
	})
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	if err := f.SetMarkets(ctx, []string{"A", "B"}); err != nil {
		t.Fatal(err)
	}
	go f.Run(ctx)

	sub := fs.waitCmd(t, "subscribe")
	var p kalshi.SubscribeParams
	_ = json.Unmarshal(sub.Params.(json.RawMessage), &p)
	if len(p.MarketTickers) != 2 || p.Channels[0] != "orderbook_delta" {
		t.Fatalf("subscribe params = %+v", p)
	}
	if !fs.authOK {
		t.Fatal("auth headers missing")
	}

	c := fs.latest()
	fs.send(c, fs.track(snapshot(1, 1, "A", [][2]string{{"0.5000", "10.00"}}, [][2]string{{"0.4000", "5.00"}})))
	fs.send(c, fs.track(delta(1, 2, "A", "yes", "0.5100", "3.00")))
	fs.send(c, fs.track(delta(1, 3, "A", "no", "0.4000", "-5.00")))

	waitFor(t, "deltas applied", func() bool {
		v, ok := f.Book("A")
		return ok && !v.Stale && v.Book.Levels(book.Yes) == 2 && v.Book.Levels(book.No) == 0
	})
	v, _ := f.Book("A")
	if top := v.Book.Top(); top.Bid.Price.String() != "0.5100" || top.HasAsk {
		t.Errorf("top = %+v", top)
	}

	// Gap: seq jumps 3 -> 5. Feed must mark A stale, request get_snapshot,
	// ignore deltas until the snapshot, then resume.
	fs.send(c, fs.track(delta(1, 5, "A", "yes", "0.5100", "100.00")))
	upd := fs.waitCmd(t, "update_subscription")
	var up kalshi.UpdateSubscriptionParams
	_ = json.Unmarshal(upd.Params.(json.RawMessage), &up)
	sort.Strings(up.MarketTickers)
	if up.Action != kalshi.ActionGetSnapshot || up.Sids[0] != 1 || strings.Join(up.MarketTickers, ",") != "A,B" {
		t.Fatalf("resync params = %+v", up)
	}
	waitFor(t, "stale after gap", func() bool { v, _ := f.Book("A"); return v.Stale })
	if f.Stats().Gaps != 1 {
		t.Errorf("gaps = %d", f.Stats().Gaps)
	}
	fs.send(c, fs.track(delta(1, 6, "A", "yes", "0.5100", "100.00"))) // must be ignored while stale
	fs.send(c, fs.track(snapshot(1, 7, "A", [][2]string{{"0.6000", "1.00"}}, nil)))
	fs.send(c, fs.track(delta(1, 8, "A", "yes", "0.6000", "1.00")))
	waitFor(t, "resynced", func() bool {
		v, ok := f.Book("A")
		return ok && !v.Stale && v.Book.Levels(book.Yes) == 1
	})
	v, _ = f.Book("A")
	if l, _ := v.Book.BestBid(book.Yes); l.Price.String() != "0.6000" || l.Qty.String() != "2.00" {
		t.Errorf("after resync best bid = %+v", l)
	}

	// Negative quantity also triggers a resync.
	fs.send(c, fs.track(delta(1, 9, "A", "yes", "0.6000", "-5.00")))
	fs.waitCmd(t, "update_subscription")
	waitFor(t, "stale after negative", func() bool { v, _ := f.Book("A"); return v.Stale })

	// Bring A back with a snapshot so the next checks start from a clean book.
	fs.send(c, fs.track(snapshot(1, 10, "A", [][2]string{{"0.6000", "1.00"}}, nil)))
	waitFor(t, "clean again", func() bool { v, _ := f.Book("A"); return !v.Stale })

	// Market set change on a live connection -> add/delete updates. The ok
	// responses carry seq 11 and 12 on sid 1; they must not count as gaps.
	gapsBefore := f.Stats().Gaps
	if err := f.SetMarkets(ctx, []string{"A", "C"}); err != nil {
		t.Fatal(err)
	}
	seen := map[string][]string{}
	for i := 0; i < 2; i++ {
		u := fs.waitCmd(t, "update_subscription")
		var p kalshi.UpdateSubscriptionParams
		_ = json.Unmarshal(u.Params.(json.RawMessage), &p)
		seen[p.Action] = p.MarketTickers
	}
	if len(seen["add_markets"]) != 1 || seen["add_markets"][0] != "C" || len(seen["delete_markets"]) != 1 || seen["delete_markets"][0] != "B" {
		t.Errorf("market sync = %v", seen)
	}
	fs.send(c, fs.track(delta(1, 13, "A", "yes", "0.6000", "1.00")))
	waitFor(t, "delta after oks", func() bool {
		v, _ := f.Book("A")
		l, _ := v.Book.BestBid(book.Yes)
		return l.Qty.String() == "2.00"
	})
	if g := f.Stats().Gaps; g != gapsBefore {
		t.Errorf("ok responses counted as gaps: %d -> %d", gapsBefore, g)
	}
	if v, _ := f.Book("A"); v.Stale {
		t.Error("A stale after ok responses")
	}

	// Server drops the connection: feed reconnects and resubscribes with the
	// current market set; books are stale until new snapshots.
	c.Close(websocket.StatusGoingAway, "restart")
	sub = fs.waitCmd(t, "subscribe")
	_ = json.Unmarshal(sub.Params.(json.RawMessage), &p)
	if len(p.MarketTickers) != 2 || p.MarketTickers[0] != "A" || p.MarketTickers[1] != "C" {
		t.Fatalf("resubscribe params = %+v", p)
	}
	waitFor(t, "reconnect", func() bool { return f.Stats().Connected && f.Stats().Reconnects == 1 })
	c = fs.latest()
	fs.send(c, fs.track(snapshot(1, 1, "A", [][2]string{{"0.7000", "1.00"}}, nil)))
	waitFor(t, "fresh snapshot", func() bool {
		v, ok := f.Book("A")
		l, _ := v.Book.BestBid(book.Yes)
		return ok && !v.Stale && l.Price.String() == "0.7000"
	})
}
