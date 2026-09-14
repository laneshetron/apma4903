// Package status serves a small JSON API for inspecting the live collector.
package status

import (
	"encoding/json"
	"net/http"
	"strconv"
	"time"

	"github.com/laneshetron/kalshi/internal/book"
	"github.com/laneshetron/kalshi/internal/feed"
)

// Handler returns the status mux:
//
//	GET /status          counters and subscription state
//	GET /markets         tracked tickers
//	GET /book/{ticker}   top of book and depth (?depth=N, default 10, 0 = all)
func Handler(f *feed.Feed, started time.Time, recorded func() uint64) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /status", func(w http.ResponseWriter, r *http.Request) {
		s := f.Stats()
		writeJSON(w, map[string]any{
			"uptime_s": int(time.Since(started).Seconds()),
			"recorded": recorded(),
			"feed":     s,
		})
	})
	mux.HandleFunc("GET /markets", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, f.Markets())
	})
	mux.HandleFunc("GET /book/{ticker}", func(w http.ResponseWriter, r *http.Request) {
		v, ok := f.Book(r.PathValue("ticker"))
		if !ok {
			http.Error(w, "unknown market", http.StatusNotFound)
			return
		}
		depth := 10
		if d := r.URL.Query().Get("depth"); d != "" {
			if n, err := strconv.Atoi(d); err == nil {
				depth = n
			}
		}
		if depth == 0 {
			depth = -1
		}
		writeJSON(w, View(v, depth))
	})
	return mux
}

// LevelJSON is one price level in dollar strings.
type LevelJSON struct {
	Price string `json:"price"`
	Qty   string `json:"qty"`
}

// TopJSON is the YES top of book.
type TopJSON struct {
	Bid    *LevelJSON `json:"bid"`
	Ask    *LevelJSON `json:"ask"`
	Mid    *string    `json:"mid"`
	Spread *string    `json:"spread"`
}

// BookJSON is the /book response.
type BookJSON struct {
	Ticker  string      `json:"ticker"`
	Stale   bool        `json:"stale"`
	LastRx  time.Time   `json:"last_rx"`
	LastTs  int64       `json:"last_ts_ms"`
	Top     TopJSON     `json:"top"`
	YesBids []LevelJSON `json:"yes_bids"`
	NoBids  []LevelJSON `json:"no_bids"`
	YesAsks []LevelJSON `json:"yes_asks"` // implied from NO bids
}

// View renders a BookView for JSON output.
func View(v feed.BookView, depth int) BookJSON {
	yes, no := v.Book.Depth(depth)
	out := BookJSON{Ticker: v.Ticker, Stale: v.Stale, LastRx: v.LastRx, LastTs: v.LastTs,
		YesBids: levels(yes), NoBids: levels(no), YesAsks: make([]LevelJSON, 0, len(no))}
	for _, l := range no {
		out.YesAsks = append(out.YesAsks, LevelJSON{l.Price.Complement().String(), l.Qty.String()})
	}
	top := v.Book.Top()
	if top.HasBid {
		out.Top.Bid = &LevelJSON{top.Bid.Price.String(), top.Bid.Qty.String()}
	}
	if top.HasAsk {
		out.Top.Ask = &LevelJSON{top.Ask.Price.String(), top.Ask.Qty.String()}
	}
	if m, ok := top.Mid(); ok {
		s := m.String()
		out.Top.Mid = &s
	}
	if sp, ok := top.Spread(); ok {
		s := sp.String()
		out.Top.Spread = &s
	}
	return out
}

func levels(in []book.Level) []LevelJSON {
	out := make([]LevelJSON, 0, len(in))
	for _, l := range in {
		out = append(out, LevelJSON{l.Price.String(), l.Qty.String()})
	}
	return out
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	enc := json.NewEncoder(w)
	enc.SetIndent("", "  ")
	_ = enc.Encode(v)
}
