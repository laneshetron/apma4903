// Command spot records public spot-exchange feeds alongside the Kalshi collector.
//
//	spot -data ./data -venues coinbase,kraken,bitstamp,gemini:BTC,gemini:ETH -assets BTC,ETH
package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/laneshetron/kalshi/internal/spot"
)

func main() {
	dataDir := flag.String("data", "./data", "data directory")
	venues := flag.String("venues", "coinbase,kraken,bitstamp,gemini:BTC,gemini:ETH", "comma-separated venues (binance is geo-blocked from the US)")
	assets := flag.String("assets", "BTC,ETH", "comma-separated base assets")
	addr := flag.String("status", "127.0.0.1:8081", "status HTTP address")
	flag.Parse()

	log := slog.New(slog.NewTextHandler(os.Stderr, nil))
	vs, err := spot.Venues(strings.Split(*venues, ","), strings.Split(*assets, ","))
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	stats := map[string]*spot.Stats{}
	var wg sync.WaitGroup
	for _, v := range vs {
		st := &spot.Stats{}
		stats[v.Name] = st
		wg.Add(1)
		go func() {
			defer wg.Done()
			if err := spot.Run(ctx, v, *dataDir, log, st); err != nil && !errors.Is(err, context.Canceled) {
				log.Error("venue stopped", "venue", v.Name, "err", err)
			}
		}()
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /status", func(w http.ResponseWriter, r *http.Request) {
		out := map[string]any{}
		for name, st := range stats {
			out[name] = map[string]any{
				"connected": st.Connected.Load(), "messages": st.Messages.Load(),
				"reconnects": st.Reconnects.Load(), "last_message": time.Unix(0, st.LastMsgNs.Load()),
			}
		}
		w.Header().Set("Content-Type", "application/json")
		enc := json.NewEncoder(w)
		enc.SetIndent("", "  ")
		_ = enc.Encode(out)
	})
	srv := &http.Server{Addr: *addr, Handler: mux}
	go func() {
		log.Info("status server", "addr", "http://"+*addr)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Error("status server", "err", err)
		}
	}()
	wg.Wait()
	sctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	_ = srv.Shutdown(sctx)
}
