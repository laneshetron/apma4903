package quoter

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/json"
	"encoding/pem"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/laneshetron/kalshi/internal/book"
	"github.com/laneshetron/kalshi/internal/kalshi"
	"github.com/laneshetron/kalshi/internal/kalshi/gen"
)

// fakeKalshi is a minimal REST stand-in for the order endpoints.
type fakeKalshi struct {
	mu       sync.Mutex
	orders   []map[string]any // create requests seen
	resting  map[string]bool
	cancels  []string
	balance  float64 // per-order collateral budget; 400 insufficient_balance when exceeded
	position string
}

func (f *fakeKalshi) handler() http.Handler {
	mux := http.NewServeMux()
	jsonMW := func(h http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json") // the generated client only decodes JSON responses
			h.ServeHTTP(w, r)
		})
	}
	mux.HandleFunc("POST /trade-api/v2/portfolio/events/orders", func(w http.ResponseWriter, r *http.Request) {
		var req map[string]any
		_ = json.NewDecoder(r.Body).Decode(&req)
		f.mu.Lock()
		defer f.mu.Unlock()
		f.orders = append(f.orders, req)
		var price, count float64
		json.Unmarshal([]byte(req["price"].(string)), &price)
		json.Unmarshal([]byte(req["count"].(string)), &count)
		if req["side"] == "ask" {
			price = 1 - price
		}
		if price*count > f.balance {
			w.WriteHeader(400)
			_, _ = w.Write([]byte(`{"error":{"code":"insufficient_balance","message":"insufficient balance"}}`))
			return
		}
		id := "ord-" + req["client_order_id"].(string)
		f.resting[id] = true
		w.WriteHeader(201)
		_ = json.NewEncoder(w).Encode(map[string]any{"order_id": id, "ts_ms": time.Now().UnixMilli(), "fill_count": "0.00", "remaining_count": req["count"]})
	})
	mux.HandleFunc("DELETE /trade-api/v2/portfolio/events/orders/{id}", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		f.mu.Lock()
		defer f.mu.Unlock()
		if !f.resting[id] {
			w.WriteHeader(404)
			_, _ = w.Write([]byte(`{"error":{"code":"not_found","message":"not found"}}`))
			return
		}
		delete(f.resting, id)
		f.cancels = append(f.cancels, id)
		_ = json.NewEncoder(w).Encode(map[string]any{"order_id": id, "ts_ms": time.Now().UnixMilli(), "reduced_by": "5.00"})
	})
	mux.HandleFunc("GET /trade-api/v2/portfolio/orders", func(w http.ResponseWriter, r *http.Request) {
		f.mu.Lock()
		defer f.mu.Unlock()
		var os []map[string]any
		for id := range f.resting {
			os = append(os, map[string]any{"order_id": id, "ticker": r.URL.Query().Get("ticker"), "status": "resting"})
		}
		_ = json.NewEncoder(w).Encode(map[string]any{"orders": os, "cursor": ""})
	})
	mux.HandleFunc("GET /trade-api/v2/portfolio/positions", func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{"market_positions": []map[string]any{{"ticker": r.URL.Query().Get("ticker"), "position_fp": f.position}}, "event_positions": []any{}})
	})
	mux.HandleFunc("GET /trade-api/v2/exchange/status", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write([]byte(`{}`)) })
	return jsonMW(mux)
}

func newLive(t *testing.T, fk *fakeKalshi) *LiveExecutor {
	t.Helper()
	srv := httptest.NewServer(fk.handler())
	t.Cleanup(srv.Close)
	signer := testSigner(t)
	cl, err := gen.NewClientWithResponses(srv.URL+"/trade-api/v2", gen.WithHTTPClient(srv.Client()),
		gen.WithRequestEditorFn(func(_ context.Context, req *http.Request) error { return signer.SignRequest(req) }))
	if err != nil {
		t.Fatal(err)
	}
	return &LiveExecutor{cl: cl, shard: 2, bucket: NewTokenBucket(300, 600)}
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

func TestLiveExecutorPlaceMapsSidesAndRoutesExplicitly(t *testing.T) {
	fk := &fakeKalshi{resting: map[string]bool{}, balance: 100}
	ex := newLive(t, fk)
	ctx := context.Background()
	if _, _, err := ex.Place(ctx, "M", book.Yes, 5000, 500, "c-yes-1"); err != nil {
		t.Fatal(err)
	}
	if _, _, err := ex.Place(ctx, "M", book.No, 2700, 500, "c-no-1"); err != nil {
		t.Fatal(err)
	}
	y, n := fk.orders[0], fk.orders[1]
	if y["side"] != "bid" || y["price"] != "0.5000" || y["count"] != "5.00" || y["post_only"] != true || y["exchange_index"].(float64) != 2 || y["self_trade_prevention_type"] != "maker" {
		t.Fatalf("YES bid request wrong: %v", y)
	}
	if n["side"] != "ask" || n["price"] != "0.7300" { // NO bid at 27c is a YES ask at 73c
		t.Fatalf("NO bid must be sent as a YES ask at 1-p: %v", n)
	}
}

func TestLiveExecutorRejectionsAndCancelSemantics(t *testing.T) {
	fk := &fakeKalshi{resting: map[string]bool{}, balance: 2.0}
	ex := newLive(t, fk)
	ctx := context.Background()
	_, _, err := ex.Place(ctx, "M", book.Yes, 5000, 500, "c-big-1") // $2.50 > $2 budget
	if err == nil || !strings.Contains(err.Error(), "insufficient_balance") {
		t.Fatalf("want insufficient_balance in the error, got %v", err)
	}
	id, _, err := ex.Place(ctx, "M", book.Yes, 3000, 500, "c-ok-1") // $1.50 fits
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ex.Cancel(ctx, "M", id); err != nil {
		t.Fatal(err)
	}
	if _, err := ex.Cancel(ctx, "M", id); !errors.Is(err, ErrOrderDone) {
		t.Fatalf("second cancel (404) must be ErrOrderDone, got %v", err)
	}
	// the token bucket refuses before the request goes out
	ex.bucket = NewTokenBucket(300, 5)
	if _, _, err := ex.Place(ctx, "M", book.Yes, 3000, 500, "c-rl-1"); err == nil || !strings.Contains(err.Error(), "rate limit") {
		t.Fatalf("empty bucket should refuse locally, got %v", err)
	}
}

func TestLiveExecutorRecoverCancelsStraysAndReturnsPosition(t *testing.T) {
	fk := &fakeKalshi{resting: map[string]bool{"ord-stale1": true, "ord-stale2": true}, balance: 100, position: "-7.00"}
	ex := newLive(t, fk)
	pos, err := ex.Recover(context.Background(), "M")
	if err != nil {
		t.Fatal(err)
	}
	if pos != -7*100 {
		t.Fatalf("position = %v, want -700", pos)
	}
	if len(fk.cancels) != 2 || len(fk.resting) != 0 {
		t.Fatalf("stray orders not cancelled: cancels=%v resting=%v", fk.cancels, fk.resting)
	}
}

func TestLiveExecutorTakeIsIOCNotPostOnly(t *testing.T) {
	fk := &fakeKalshi{resting: map[string]bool{}, balance: 100}
	ex := newLive(t, fk)
	if _, _, err := ex.Take(context.Background(), "M", book.No, 5000, 60*100, "t-1"); err != nil {
		t.Fatal(err)
	}
	r := fk.orders[0]
	if r["side"] != "ask" || r["price"] != "0.5000" || r["count"] != "60.00" || r["post_only"] != false || r["time_in_force"] != "immediate_or_cancel" {
		t.Fatalf("take request wrong: %v", r)
	}
	if _, _, err := ex.Take(context.Background(), "M", book.Yes, 5100, 30*100, "t-2"); err != nil {
		t.Fatal(err)
	}
	if r := fk.orders[1]; r["side"] != "bid" || r["price"] != "0.5100" {
		t.Fatalf("buying YES at the ask should be a bid at the ask price: %v", r)
	}
}
