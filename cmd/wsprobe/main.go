// wsprobe opens several WebSocket connections to Kalshi (optionally pinned to
// specific load-balancer IPs), subscribes each to the same market's
// orderbook_delta channel, and measures how much earlier the first copy of
// each delta arrives compared with any single connection.
//
//	wsprobe -config config.yaml -n 3 -dur 3m
//	wsprobe -config config.yaml -ips <exchange edge ips, comma separated> -dur 3m
package main

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"flag"
	"fmt"
	"net"
	"net/http"
	"os"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/laneshetron/kalshi/internal/config"
	"github.com/laneshetron/kalshi/internal/kalshi"
)

type key struct {
	ts    int64
	price string
	side  string
	delta string
	ord   int
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func pinnedClient(ip string) *http.Client {
	tr := &http.Transport{
		TLSClientConfig: &tls.Config{ServerName: "external-api-ws.kalshi.com", MinVersion: tls.VersionTLS12},
		DialContext: func(ctx context.Context, network, addr string) (net.Conn, error) {
			d := net.Dialer{Timeout: 10 * time.Second}
			c, err := d.DialContext(ctx, network, net.JoinHostPort(ip, "443"))
			if err == nil {
				if tc, ok := c.(*net.TCPConn); ok {
					_ = tc.SetNoDelay(true)
				}
			}
			return c, err
		},
	}
	return &http.Client{Transport: tr}
}

func run() error {
	cfgPath := flag.String("config", "config.yaml", "collector config")
	n := flag.Int("n", 3, "connections (when -ips is empty: resolved DNS answers, one per IP)")
	ips := flag.String("ips", "", "comma-separated LB IPs to pin connections to")
	series := flag.String("series", "KXBTC15M", "series")
	dur := flag.Duration("dur", 3*time.Minute, "measurement duration")
	flag.Parse()

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
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// the open market with the most time left
	ms, err := rest.ListOpenMarkets(ctx, *series)
	if err != nil {
		return err
	}
	ticker, best := "", time.Time{}
	for _, m := range ms {
		if m.CloseTime.After(best) {
			ticker, best = m.Ticker, m.CloseTime
		}
	}
	if ticker == "" {
		return fmt.Errorf("no open market")
	}

	var addrs []string
	if *ips != "" {
		addrs = strings.Split(*ips, ",")
	} else {
		res, err := net.LookupHost("external-api-ws.kalshi.com")
		if err != nil {
			return err
		}
		sort.Strings(res)
		for _, a := range res {
			if len(addrs) < *n {
				addrs = append(addrs, a)
			}
		}
	}
	fmt.Fprintf(os.Stderr, "market %s, %d connections: %v\n", ticker, len(addrs), addrs)

	var mu sync.Mutex
	seen := map[key][]int64{} // rx per connection index (0 = missing)
	tsOf := map[key]int64{}
	var wg sync.WaitGroup
	for i, ip := range addrs {
		conn, err := kalshi.Dial(ctx, env, signer, kalshi.DialOptions{HTTPClient: pinnedClient(ip)})
		if err != nil {
			return fmt.Errorf("conn %d (%s): %w", i, ip, err)
		}
		if _, err := conn.Subscribe(ctx, kalshi.SubscribeParams{Channels: []string{"orderbook_delta"}, MarketTickers: []string{ticker}}); err != nil {
			return err
		}
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			ord := map[key]int{}
			for m := range conn.Messages() {
				var e kalshi.Envelope
				if json.Unmarshal(m.Data, &e) != nil || e.Type != "orderbook_delta" {
					continue
				}
				var d struct {
					Price string `json:"price_dollars"`
					Delta string `json:"delta_fp"`
					Side  string `json:"side"`
					TsMs  int64  `json:"ts_ms"`
				}
				if json.Unmarshal(e.Msg, &d) != nil {
					continue
				}
				k := key{d.TsMs, d.Price, d.Side, d.Delta, 0}
				k.ord = ord[k]
				ord[k]++
				mu.Lock()
				if _, ok := seen[k]; !ok {
					seen[k] = make([]int64, len(addrs))
					tsOf[k] = d.TsMs
				}
				seen[k][i] = m.Rx.UnixNano()
				mu.Unlock()
			}
		}(i)
	}
	time.Sleep(*dur)
	cancel()

	mu.Lock()
	defer mu.Unlock()
	var complete int
	behind := make([][]float64, len(addrs)) // per conn: rx - min rx, ms
	engine := make([][]float64, len(addrs)) // per conn: rx - engine ts, ms
	var gain []float64                      // conn0 rx - min rx
	for k, rxs := range seen {
		ok := true
		for _, r := range rxs {
			if r == 0 {
				ok = false
			}
		}
		if !ok {
			continue
		}
		complete++
		mn := rxs[0]
		for _, r := range rxs {
			if r < mn {
				mn = r
			}
		}
		for i, r := range rxs {
			behind[i] = append(behind[i], float64(r-mn)/1e6)
			engine[i] = append(engine[i], float64(r)/1e6-float64(tsOf[k]))
		}
		gain = append(gain, float64(rxs[0]-mn)/1e6)
	}
	pct := func(xs []float64, p float64) float64 {
		if len(xs) == 0 {
			return -1
		}
		sort.Float64s(xs)
		return xs[int(p*float64(len(xs)-1))]
	}
	fmt.Printf("\n%d deltas seen on all %d connections over %s\n\n", complete, len(addrs), *dur)
	fmt.Printf("| conn | ip | engine ts -> rx p10 / p50 / p90 (ms) | behind the earliest copy p50 / p90 / p99 (ms) | first %% |\n|---|---|---|---|---|\n")
	for i, ip := range addrs {
		first := 0
		for _, b := range behind[i] {
			if b == 0 {
				first++
			}
		}
		fmt.Printf("| %d | %s | %.2f / %.2f / %.2f | %.2f / %.2f / %.2f | %.0f%% |\n", i, ip,
			pct(engine[i], .1), pct(engine[i], .5), pct(engine[i], .9),
			pct(behind[i], .5), pct(behind[i], .9), pct(behind[i], .99), float64(first)/float64(len(behind[i]))*100)
	}
	fmt.Printf("\ngain from taking the earliest of %d vs connection 0 alone: mean %.2f ms, p50 %.2f, p90 %.2f, p99 %.2f\n",
		len(addrs), mean(gain), pct(gain, .5), pct(gain, .9), pct(gain, .99))
	return nil
}

func mean(xs []float64) float64 {
	if len(xs) == 0 {
		return 0
	}
	s := 0.0
	for _, x := range xs {
		s += x
	}
	return s / float64(len(xs))
}
