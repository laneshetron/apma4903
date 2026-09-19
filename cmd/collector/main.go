// Command collector records Kalshi market data and maintains live order books.
//
//	collector -config config.yaml
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"sort"
	"syscall"
	"time"

	"github.com/laneshetron/kalshi/internal/config"
	"github.com/laneshetron/kalshi/internal/feed"
	"github.com/laneshetron/kalshi/internal/kalshi"
	"github.com/laneshetron/kalshi/internal/recorder"
	"github.com/laneshetron/kalshi/internal/status"
)

func main() {
	cfgPath := flag.String("config", "config.yaml", "path to YAML config")
	flag.Parse()
	if err := run(*cfgPath); err != nil && !errors.Is(err, context.Canceled) {
		fmt.Fprintln(os.Stderr, "collector:", err)
		os.Exit(1)
	}
}

func run(cfgPath string) error {
	log := slog.New(slog.NewTextHandler(os.Stderr, nil))
	cfg, err := config.Load(cfgPath)
	if err != nil {
		return err
	}
	env, _ := kalshi.ParseEnv(cfg.Env)
	signer, err := kalshi.NewSignerFromFile(cfg.KeyID, cfg.PrivateKeyPath)
	if err != nil {
		return err
	}
	rest, err := kalshi.NewREST(env, signer, nil)
	if err != nil {
		return err
	}
	rec, err := recorder.Open(cfg.DataDir, time.Second)
	if err != nil {
		return err
	}
	defer func() {
		if err := rec.Close(); err != nil {
			log.Error("close recorder", "err", err)
		}
	}()

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	f := feed.New(feed.Config{Env: env, Signer: signer, Recorder: rec, Channels: cfg.Channels, IndexIDs: cfg.IndexIDs, Logger: log})

	// Resolve the initial market set before connecting so the first
	// subscribe carries every market.
	tickers, err := resolveMarkets(ctx, rest, cfg)
	if err != nil {
		return fmt.Errorf("resolve markets: %w", err)
	}
	log.Info("resolved markets", "count", len(tickers), "series", cfg.Markets.Series)
	if err := f.SetMarkets(ctx, tickers); err != nil {
		return err
	}

	srv := &http.Server{Addr: cfg.StatusAddr, Handler: status.Handler(f, time.Now(), rec.Lines)}
	go func() {
		log.Info("status server", "addr", "http://"+cfg.StatusAddr)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Error("status server", "err", err)
		}
	}()
	defer func() {
		sctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()
		_ = srv.Shutdown(sctx)
	}()

	if len(cfg.Markets.Series) > 0 || cfg.Markets.AllMinVolume24h > 0 {
		go every(ctx, cfg.Markets.RefreshInterval, func() {
			t, err := resolveMarkets(ctx, rest, cfg)
			if err != nil {
				log.Warn("refresh markets", "err", err)
				return
			}
			if err := f.SetMarkets(ctx, t); err != nil {
				log.Warn("update subscriptions", "err", err)
			}
		})
	}
	if cfg.RESTCheckInterval > 0 {
		go every(ctx, cfg.RESTCheckInterval, func() {
			bad, err := f.CrossCheck(ctx, rest)
			if err != nil {
				return
			}
			log.Info("rest cross-check", "markets", len(f.Markets()), "mismatched", len(bad))
		})
	}

	return f.Run(ctx)
}

// resolveMarkets expands configured series into open market tickers and
// merges them with explicit tickers.
func resolveMarkets(ctx context.Context, rest *kalshi.REST, cfg *config.Config) ([]string, error) {
	set := map[string]struct{}{}
	for _, t := range cfg.Markets.Tickers {
		set[t] = struct{}{}
	}
	for _, s := range cfg.Markets.Series {
		ms, err := rest.ListOpenMarkets(ctx, s)
		if err != nil {
			return nil, err
		}
		for _, m := range ms {
			set[m.Ticker] = struct{}{}
		}
	}
	if cfg.Markets.AllMinVolume24h > 0 {
		ms, err := rest.ListActiveMarkets(ctx, cfg.Markets.AllMinVolume24h, cfg.Markets.ExcludeSeries)
		if err != nil {
			return nil, err
		}
		for _, m := range ms {
			set[m.Ticker] = struct{}{}
		}
	}
	out := make([]string, 0, len(set))
	for t := range set {
		out = append(out, t)
	}
	sort.Strings(out)
	return out, nil
}

func every(ctx context.Context, d time.Duration, fn func()) {
	t := time.NewTicker(d)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			fn()
		}
	}
}
