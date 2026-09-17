// quoter runs the market-making engine on one series, in paper or live mode.
//
//	quoter -config config.yaml -mode paper -tables quoter_tables.json
//	quoter -config config.yaml -mode live  -size 5 -max-pos 10 -tables quoter_tables.json
//
// Paper mode simulates fills against the live public book with the sim's
// queue model; live mode sends real post-only orders with explicit shard
// routing. Both write a tape to <data_dir>/quoter/<mode>/ in the collector's
// format (every feed frame plus quoter decisions as _local events).
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
	"path/filepath"
	"syscall"
	"time"

	"github.com/laneshetron/kalshi/internal/book"
	"github.com/laneshetron/kalshi/internal/config"
	"github.com/laneshetron/kalshi/internal/feed"
	"github.com/laneshetron/kalshi/internal/kalshi"
	"github.com/laneshetron/kalshi/internal/kalshi/gen"
	"github.com/laneshetron/kalshi/internal/quoter"
	"github.com/laneshetron/kalshi/internal/recorder"
)

func main() {
	if err := run(); err != nil && !errors.Is(err, context.Canceled) {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run() error {
	cfgPath := flag.String("config", "config.yaml", "collector config (env, credentials, data_dir)")
	mode := flag.String("mode", "paper", "paper | live")
	series := flag.String("series", "KXBTC15M", "series to quote")
	tables := flag.String("tables", "quoter_tables.json", "edge model JSON from export_tables.py (empty disables the join gate)")
	size := flag.Int("size", 100, "contracts per quote")
	maxPos := flag.Int("max-pos", 200, "absolute position limit, contracts")
	stopBefore := flag.Duration("stop-before", 5*time.Minute, "stop quoting this long before close")
	signalMove := flag.Float64("signal-move", 2.0, "$ Coinbase 1s move that pulls the stale side")
	greeksCap := flag.Float64("greeks-cap", 0.05, "don't quote when a 1-sigma 10s move is worth >= this (fraction of $1); 0 disables")
	minDepth := flag.Int("min-depth", 0, "don't rest on a touch level thinner than this many contracts (ours excluded); 0 disables")
	joinTheta := flag.Float64("join-theta", 0, "join gate threshold in cents (edge < -theta vetoes); needs -tables")
	noJoinGate := flag.Bool("no-join-gate", false, "disable the join gate")
	flatten := flag.Bool("flatten-at-stop", true, "cross the spread to close the position at the endgame stop instead of carrying it to settlement")
	shard := flag.Int("shard", 2, "exchange_index for live orders (crypto = 2)")
	maxLoss := flag.Float64("max-loss", 50, "halt when session mark-to-market loss exceeds this ($)")
	placeLat := flag.Duration("paper-place-latency", 9*time.Millisecond, "paper: simulated place latency")
	cancelLat := flag.Duration("paper-cancel-latency", 5*time.Millisecond, "paper: simulated cancel latency")
	feedLag := flag.Duration("paper-feed-lag", 7*time.Millisecond, "paper: engine -> public feed delay (orders seen within it were ahead of us)")
	paperCapital := flag.Float64("paper-capital", -1, "paper: fixed collateral budget ($); <0 = unlimited")
	statusAddr := flag.String("status", "127.0.0.1:8082", "status HTTP address")
	flag.Parse()

	log := slog.New(slog.NewTextHandler(os.Stderr, nil))
	cfg, err := config.Load(*cfgPath)
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
	if *mode != "paper" && *mode != "live" {
		return fmt.Errorf("mode must be paper or live")
	}

	var edge *quoter.EdgeModel
	if *tables != "" && !*noJoinGate {
		if edge, err = quoter.LoadEdgeModel(*tables); err != nil {
			return err
		}
		log.Info("edge model", "fitted_on", edge.FittedOn)
	}
	params := quoter.Params{
		Size: book.Qty(*size * 100), MaxPos: book.Qty(*maxPos * 100), StopBefore: *stopBefore, SignalMove: *signalMove, FlattenAtStop: *flatten,
	}
	if edge != nil {
		th := *joinTheta
		params.JoinTheta = &th
	}
	if *greeksCap > 0 {
		gc := *greeksCap
		params.GreeksCap = &gc
	}
	params.MinDepth = book.Qty(*minDepth * 100)
	limits := quoter.DefaultLimits()
	limits.MaxAbsPos = book.Qty(*maxPos * 100)
	limits.MaxLoss = *maxLoss

	rec, err := recorder.Open(filepath.Join(cfg.DataDir, "quoter", *mode), time.Second)
	if err != nil {
		return err
	}
	defer rec.Close()

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	var eng *quoter.Engine
	fd := feed.New(feed.Config{
		Env: env, Signer: signer, Recorder: rec, Logger: log,
		Channels: []string{kalshi.ChannelOrderbookDelta, kalshi.ChannelTrade, kalshi.ChannelCFBenchmarks5Hz, kalshi.ChannelUserOrders, kalshi.ChannelFill},
		IndexIDs: []string{"BRTI"},
		OnEvent:  func(ev feed.Event) { eng.OnFeedEvent(ev) },
	})

	var exec quoter.Executor
	var paper *quoter.PaperExecutor
	if *mode == "paper" {
		paper = quoter.NewPaperExecutor(*placeLat, *cancelLat, func(tk string) (*book.Book, bool) {
			bv, ok := fd.Book(tk)
			return bv.Book, ok
		}, func(id string, f quoter.Fill) { eng.PaperFill(id, f) })
		paper.FeedLag = *feedLag
		exec = paper
	} else {
		bucket := quoter.NewTokenBucket(300, 600) // Advanced tier write budget
		live, err := quoter.NewLiveExecutor(env, signer, *shard, bucket)
		if err != nil {
			return err
		}
		live.Warm(ctx)
		exec = live
	}

	pick := func(ctx context.Context) (*quoter.Market, error) {
		ms, err := rest.ListOpenMarkets(ctx, *series)
		if err != nil {
			return nil, err
		}
		var best *quoter.Market
		for _, m := range ms {
			if m.FloorStrike == nil || m.ExchangeIndex != *shard && *mode == "live" {
				continue
			}
			if best == nil || m.CloseTime.After(best.CloseAt) {
				best = &quoter.Market{Ticker: m.Ticker, Strike: *m.FloorStrike, CloseAt: m.CloseTime}
			}
		}
		return best, nil
	}

	var balance func(context.Context) (float64, error)
	var recover func(context.Context, string) (book.Qty, error)
	if *mode == "live" {
		recover = exec.(*quoter.LiveExecutor).Recover
		balance = func(ctx context.Context) (float64, error) {
			ex := gen.ExchangeIndex(*shard)
			resp, err := rest.Raw().GetBalanceWithResponse(ctx, &gen.GetBalanceParams{ExchangeIndex: &ex})
			if err != nil {
				return 0, err
			}
			if resp.JSON200 == nil {
				return 0, fmt.Errorf("balance: HTTP %d", resp.StatusCode())
			}
			var v float64
			_, err = fmt.Sscanf(resp.JSON200.BalanceDollars, "%g", &v)
			return v, err
		}
	}
	eng = quoter.NewEngine(quoter.EngineConfig{
		Params: params, Limits: limits, Series: *series, Mode: *mode, Exec: exec, Paper: paper, Feed: fd,
		Recorder: rec, Edge: edge, Logger: log, PickMarket: pick, Balance: balance, Capital: *paperCapital, Recover: recover,
	})

	go func() {
		if err := fd.Run(ctx); err != nil && !errors.Is(err, context.Canceled) {
			log.Error("feed stopped", "err", err)
		}
	}()
	go quoter.RunCoinbase(ctx, "BTC-USD", eng.Quotes(), func(rx time.Time, raw []byte) {
		_ = rec.Write(rx, raw)
	}, eng.SetCoinbaseState)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /status", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		enc := json.NewEncoder(w)
		enc.SetIndent("", "  ")
		_ = enc.Encode(map[string]any{"quoter": eng.Stats(), "feed": fd.Stats(), "params": paramsJSON(params)})
	})
	srv := &http.Server{Addr: *statusAddr, Handler: mux}
	go func() {
		log.Info("status server", "addr", "http://"+*statusAddr)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Error("status server", "err", err)
		}
	}()

	log.Info("quoter starting", "mode", *mode, "series", *series, "size", *size, "max_pos", *maxPos, "shard", *shard)
	err = eng.Run(ctx)
	sctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	_ = srv.Shutdown(sctx)
	return err
}

func paramsJSON(p quoter.Params) map[string]any {
	out := map[string]any{"size": p.Size.String(), "max_pos": p.MaxPos.String(), "stop_before": p.StopBefore.String(), "signal_move_$": p.SignalMove}
	if p.JoinTheta != nil {
		out["join_theta_c"] = *p.JoinTheta
	}
	if p.GreeksCap != nil {
		out["greeks_cap"] = *p.GreeksCap
	}
	if p.MinDepth > 0 {
		out["min_depth"] = p.MinDepth.String()
	}
	return out
}
