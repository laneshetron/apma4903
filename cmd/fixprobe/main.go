// fixprobe measures Kalshi's order-entry latency over the FIX gateway
// (KalshiNR session, FIXT.1.1 / FIX50SP2 over TLS), the same experiment as
// orderprobe but bypassing the REST gateway. Uses the REST API key: the FIX
// SenderCompID is the key id and the Logon is signed with the same RSA key.
//
//	fixprobe -config config.yaml -n 50 -series KXBTC15M -price 0.01 -out fixprobe.jsonl
//
// Per iteration: NewOrderSingle (1 contract, post-only YES bid at -price)
// -> ExecutionReport New; OrderCancelRequest -> ExecutionReport Canceled.
// Timed legs: send -> exec report received, and send -> TransactTime<60>
// (the engine's own clock, millisecond precision). Also subscribes to the
// public orderbook_delta over WS for the same market, as orderprobe does.
package main

import (
	"bufio"
	"context"
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/tls"
	"encoding/base64"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"net"
	"os"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"

	"github.com/laneshetron/kalshi/internal/config"
	"github.com/laneshetron/kalshi/internal/kalshi"
)

const soh = "\x01"

type fixMsg map[int]string

type fixConn struct {
	c      net.Conn
	r      *bufio.Reader
	sender string
	target string
	seq    int
	mu     sync.Mutex
	in     chan struct {
		rx time.Time
		m  fixMsg
	}
}

func fixTime(t time.Time) string { return t.UTC().Format("20060102-15:04:05.000") }

// build frames body fields (already in order) into a full FIX message.
func (f *fixConn) build(msgType string, body []string, sending time.Time) ([]byte, int) {
	f.seq++
	hdr := []string{"35=" + msgType, "49=" + f.sender, "56=" + f.target, "34=" + strconv.Itoa(f.seq), "52=" + fixTime(sending)}
	inner := strings.Join(append(hdr, body...), soh) + soh
	msg := "8=FIXT.1.1" + soh + "9=" + strconv.Itoa(len(inner)) + soh + inner
	sum := 0
	for i := 0; i < len(msg); i++ {
		sum += int(msg[i])
	}
	msg += fmt.Sprintf("10=%03d%s", sum%256, soh)
	return []byte(msg), f.seq
}

func (f *fixConn) send(msgType string, body []string) (time.Time, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	now := time.Now()
	b, _ := f.build(msgType, body, now)
	_, err := f.c.Write(b)
	return now, err
}

func parse(raw []byte) fixMsg {
	m := fixMsg{}
	for _, kv := range strings.Split(string(raw), soh) {
		if i := strings.IndexByte(kv, '='); i > 0 {
			if k, err := strconv.Atoi(kv[:i]); err == nil {
				m[k] = kv[i+1:]
			}
		}
	}
	return m
}

// readOne reads a full FIX message (8=...|9=len|...|10=xxx|).
func (f *fixConn) readOne() ([]byte, error) {
	// read up to "9=" length field
	head, err := f.r.ReadString(1) // 8=FIXT.1.1<SOH>
	if err != nil {
		return nil, err
	}
	lenField, err := f.r.ReadString(1) // 9=NNN<SOH>
	if err != nil {
		return nil, err
	}
	n, err := strconv.Atoi(strings.TrimSuffix(strings.TrimPrefix(lenField, "9="), soh))
	if err != nil {
		return nil, fmt.Errorf("bad length field %q", lenField)
	}
	body := make([]byte, n+7) // body + "10=xxx<SOH>"
	if _, err := ioReadFull(f.r, body); err != nil {
		return nil, err
	}
	return append([]byte(head+lenField), body...), nil
}

func ioReadFull(r *bufio.Reader, b []byte) (int, error) {
	n := 0
	for n < len(b) {
		k, err := r.Read(b[n:])
		n += k
		if err != nil {
			return n, err
		}
	}
	return n, nil
}

func dialFIX(ctx context.Context, host string, keyID string, priv *rsa.PrivateKey) (*fixConn, error) {
	d := tls.Dialer{Config: &tls.Config{MinVersion: tls.VersionTLS12}}
	c, err := d.DialContext(ctx, "tcp", host)
	if err != nil {
		return nil, err
	}
	if tc, ok := c.(*tls.Conn); ok {
		if raw, ok := tc.NetConn().(*net.TCPConn); ok {
			_ = raw.SetNoDelay(true)
		}
	}
	f := &fixConn{c: c, r: bufio.NewReaderSize(c, 1<<16), sender: keyID, target: "KalshiNR"}
	f.in = make(chan struct {
		rx time.Time
		m  fixMsg
	}, 256)
	// Logon: signature over SendingTime|MsgType|MsgSeqNum|SenderCompID|TargetCompID
	now := time.Now()
	seq := f.seq + 1
	pre := strings.Join([]string{fixTime(now), "A", strconv.Itoa(seq), f.sender, f.target}, soh)
	h := sha256.Sum256([]byte(pre))
	sig, err := rsa.SignPSS(rand.Reader, priv, crypto.SHA256, h[:], &rsa.PSSOptions{SaltLength: rsa.PSSSaltLengthEqualsHash})
	if err != nil {
		return nil, err
	}
	rawData := base64.StdEncoding.EncodeToString(sig)
	body := []string{"98=0", "108=30", "141=Y", "1137=9", "21005=Y", "21011=Y", "95=" + strconv.Itoa(len(rawData)), "96=" + rawData}
	f.mu.Lock()
	b, _ := f.build("A", body, now)
	_, err = f.c.Write(b)
	f.mu.Unlock()
	if err != nil {
		return nil, err
	}
	raw, err := f.readOne()
	if err != nil {
		return nil, fmt.Errorf("logon read: %w", err)
	}
	m := parse(raw)
	if m[35] != "A" {
		return nil, fmt.Errorf("logon rejected: 35=%s 58=%q", m[35], m[58])
	}
	go func() {
		for {
			raw, err := f.readOne()
			rx := time.Now()
			if err != nil {
				close(f.in)
				return
			}
			m := parse(raw)
			switch m[35] {
			case "0": // heartbeat
			case "1": // test request -> heartbeat with TestReqID
				_, _ = f.send("0", []string{"112=" + m[112]})
			default:
				f.in <- struct {
					rx time.Time
					m  fixMsg
				}{rx, m}
			}
		}
	}()
	// app-level heartbeat
	go func() {
		t := time.NewTicker(25 * time.Second)
		defer t.Stop()
		for range t.C {
			if _, err := f.send("0", nil); err != nil {
				return
			}
		}
	}()
	return f, nil
}

func (f *fixConn) waitExec(clOrdID, execType string, timeout time.Duration) (time.Time, fixMsg, error) {
	deadline := time.After(timeout)
	for {
		select {
		case ev, ok := <-f.in:
			if !ok {
				return time.Time{}, nil, errors.New("fix connection closed")
			}
			if ev.m[35] == "8" && ev.m[11] == clOrdID && ev.m[150] == execType {
				return ev.rx, ev.m, nil
			}
			if ev.m[35] == "8" && ev.m[11] == clOrdID && ev.m[150] == "8" {
				return ev.rx, ev.m, fmt.Errorf("rejected: 58=%q 103=%s", ev.m[58], ev.m[103])
			}
			if ev.m[35] == "9" && ev.m[11] == clOrdID {
				return ev.rx, ev.m, fmt.Errorf("cancel rejected: 58=%q", ev.m[58])
			}
			if ev.m[35] == "5" {
				return ev.rx, ev.m, fmt.Errorf("logout: 58=%q", ev.m[58])
			}
			if ev.m[35] == "3" {
				return ev.rx, ev.m, fmt.Errorf("session reject: 58=%q 373=%s", ev.m[58], ev.m[373])
			}
		case <-deadline:
			return time.Time{}, nil, errors.New("timeout waiting for exec report " + execType)
		}
	}
}

func transactMs(m fixMsg) float64 {
	t, err := time.Parse("20060102-15:04:05.000", m[60])
	if err != nil {
		if t, err = time.Parse("20060102-15:04:05.000000", m[60]); err != nil {
			return -1
		}
	}
	return float64(t.UnixNano()) / 1e6
}

type sample struct {
	I            int     `json:"i"`
	ClOrdID      string  `json:"cl_ord_id"`
	Send         int64   `json:"send_ns"`
	CreateAck    float64 `json:"create_ack_ms"`    // ExecutionReport New received
	CreateEngine float64 `json:"create_engine_ms"` // TransactTime - send
	CreateDelta  float64 `json:"create_delta_ms"`  // public orderbook_delta received
	CreateDelTs  float64 `json:"create_delta_ts_ms"`
	CancelAck    float64 `json:"cancel_ack_ms"`
	CancelEngine float64 `json:"cancel_engine_ms"`
	CancelDelta  float64 `json:"cancel_delta_ms"`
	CancelDelTs  float64 `json:"cancel_delta_ts_ms"`
	Err          string  `json:"err,omitempty"`
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run() error {
	cfgPath := flag.String("config", "config.yaml", "collector config (for env and credentials)")
	host := flag.String("host", "mm.fix.elections.kalshi.com:8228", "FIX order-entry host:port (KalshiNR)")
	series := flag.String("series", "KXBTC15M", "series to pick a market from")
	price := flag.String("price", "0.01", "YES bid price, dollars")
	n := flag.Int("n", 50, "iterations")
	gap := flag.Duration("gap", 1500*time.Millisecond, "pause between iterations")
	out := flag.String("out", "", "write per-iteration JSON lines here")
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
	priv, err := kalshi.LoadPrivateKey(cfg.PrivateKeyPath)
	if err != nil {
		return err
	}
	rest, err := kalshi.NewREST(env, signer, nil)
	if err != nil {
		return err
	}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	var ticker string
	for {
		if ticker, err = pickMarket(ctx, rest, *series); err == nil {
			break
		}
		fmt.Fprintln(os.Stderr, err.Error()+"; waiting")
		time.Sleep(15 * time.Second)
	}
	fmt.Fprintf(os.Stderr, "market %s, FIX %s, price %s\n", ticker, *host, *price)

	// public book over WS, to see when our order becomes visible to others
	conn, err := kalshi.Dial(ctx, env, signer, kalshi.DialOptions{})
	if err != nil {
		return err
	}
	if _, err := conn.Subscribe(ctx, kalshi.SubscribeParams{Channels: []string{"orderbook_delta"}, MarketTickers: []string{ticker}}); err != nil {
		return err
	}
	deltaEv := make(chan kalshi.RawMessage, 1024)
	go func() {
		for m := range conn.Messages() {
			var e kalshi.Envelope
			if json.Unmarshal(m.Data, &e) == nil && e.Type == "orderbook_delta" {
				deltaEv <- m
			}
		}
	}()

	fx, err := dialFIX(ctx, *host, cfg.KeyID, priv)
	if err != nil {
		return fmt.Errorf("fix: %w", err)
	}
	fmt.Fprintln(os.Stderr, "FIX logon ok")

	var w *os.File
	if *out != "" {
		if w, err = os.Create(*out); err != nil {
			return err
		}
		defer w.Close()
	}
	var samples []sample
	for i := 0; i < *n; i++ {
		s := probeOnce(fx, ticker, *price, deltaEv)
		s.I = i
		samples = append(samples, s)
		if w != nil {
			b, _ := json.Marshal(s)
			w.Write(append(b, '\n'))
		}
		if s.Err != "" {
			fmt.Fprintf(os.Stderr, "iter %d: %s\n", i, s.Err)
		} else {
			fmt.Fprintf(os.Stderr, "iter %2d create: ack %.1f engine %.1f delta %.1f | cancel: ack %.1f engine %.1f delta %.1f ms\n",
				i, s.CreateAck, s.CreateEngine, s.CreateDelta, s.CancelAck, s.CancelEngine, s.CancelDelta)
		}
		time.Sleep(*gap)
	}
	_, _ = fx.send("5", nil)
	summarize(samples)
	return nil
}

func pickMarket(ctx context.Context, rest *kalshi.REST, series string) (string, error) {
	ms, err := rest.ListOpenMarkets(ctx, series)
	if err != nil {
		return "", err
	}
	best, bestT := "", time.Time{}
	for _, m := range ms {
		if m.CloseTime.After(bestT) {
			best, bestT = m.Ticker, m.CloseTime
		}
	}
	if best == "" || time.Until(bestT) < 8*time.Minute {
		return "", errors.New("no open market with >= 8 min to close")
	}
	return best, nil
}

func drain(ch chan kalshi.RawMessage) {
	for {
		select {
		case <-ch:
		default:
			return
		}
	}
}

func waitDelta(ch chan kalshi.RawMessage, price string, sign int, timeout time.Duration) (time.Time, int64, error) {
	deadline := time.After(timeout)
	want := strings.TrimRight(strings.TrimRight(price, "0"), ".")
	for {
		select {
		case m := <-ch:
			var e kalshi.Envelope
			if json.Unmarshal(m.Data, &e) != nil {
				continue
			}
			var d struct {
				Price string `json:"price_dollars"`
				Delta string `json:"delta_fp"`
				Side  string `json:"side"`
				TsMs  int64  `json:"ts_ms"`
			}
			if json.Unmarshal(e.Msg, &d) != nil || d.Side != "yes" {
				continue
			}
			p := strings.TrimRight(strings.TrimRight(d.Price, "0"), ".")
			neg := strings.HasPrefix(d.Delta, "-")
			if p == want && ((sign > 0 && !neg) || (sign < 0 && neg)) {
				return m.Rx, d.TsMs, nil
			}
		case <-deadline:
			return time.Time{}, 0, errors.New("timeout waiting for delta")
		}
	}
}

func probeOnce(fx *fixConn, ticker, price string, deltaEv chan kalshi.RawMessage) sample {
	drain(deltaEv)
	ms := func(t0, t time.Time) float64 { return float64(t.Sub(t0).Nanoseconds()) / 1e6 }
	s := sample{ClOrdID: uuid.NewString()}
	t0, err := fx.send("D", []string{"11=" + s.ClOrdID, "38=1", "40=2", "54=1", "55=" + ticker, "44=" + price, "59=1", "18=6"})
	s.Send = t0.UnixNano()
	if err != nil {
		s.Err = "send: " + err.Error()
		return s
	}
	rx, m, err := fx.waitExec(s.ClOrdID, "0", 3*time.Second)
	if err != nil {
		s.Err = "create: " + err.Error()
		return s
	}
	s.CreateAck = ms(t0, rx)
	s.CreateEngine = transactMs(m) - float64(t0.UnixNano())/1e6
	if t, ts, err := waitDelta(deltaEv, price, +1, 3*time.Second); err == nil {
		s.CreateDelta = ms(t0, t)
		s.CreateDelTs = float64(ts) - float64(t0.UnixNano())/1e6
	} else {
		s.CreateDelta, s.CreateDelTs = -1, -1
	}

	drain(deltaEv)
	cid := uuid.NewString()
	t1, err := fx.send("F", []string{"11=" + cid, "41=" + s.ClOrdID, "37=" + m[37], "54=1", "55=" + ticker})
	if err != nil {
		s.Err = "cancel send: " + err.Error()
		return s
	}
	rx, m2, err := fx.waitExec(cid, "4", 3*time.Second)
	if err != nil {
		s.Err = "cancel: " + err.Error()
		return s
	}
	s.CancelAck = ms(t1, rx)
	s.CancelEngine = transactMs(m2) - float64(t1.UnixNano())/1e6
	if t, ts, err := waitDelta(deltaEv, price, -1, 3*time.Second); err == nil {
		s.CancelDelta = ms(t1, t)
		s.CancelDelTs = float64(ts) - float64(t1.UnixNano())/1e6
	} else {
		s.CancelDelta, s.CancelDelTs = -1, -1
	}
	return s
}

func summarize(samples []sample) {
	pct := func(xs []float64, p float64) float64 {
		if len(xs) == 0 {
			return -1
		}
		sort.Float64s(xs)
		return xs[int(p*float64(len(xs)-1))]
	}
	cols := []struct {
		name string
		get  func(sample) float64
	}{
		{"create: send->TransactTime", func(s sample) float64 { return s.CreateEngine }},
		{"create: send->exec report", func(s sample) float64 { return s.CreateAck }},
		{"create: send->public delta", func(s sample) float64 { return s.CreateDelta }},
		{"create: send->delta ts_ms", func(s sample) float64 { return s.CreateDelTs }},
		{"cancel: send->TransactTime", func(s sample) float64 { return s.CancelEngine }},
		{"cancel: send->exec report", func(s sample) float64 { return s.CancelAck }},
		{"cancel: send->public delta", func(s sample) float64 { return s.CancelDelta }},
		{"cancel: send->delta ts_ms", func(s sample) float64 { return s.CancelDelTs }},
	}
	ok := 0
	for _, s := range samples {
		if s.Err == "" {
			ok++
		}
	}
	fmt.Printf("\n%d/%d iterations ok\n\n| leg | min | p10 | p50 | p90 | max |\n|---|---|---|---|---|---|\n", ok, len(samples))
	for _, c := range cols {
		var xs []float64
		for _, s := range samples {
			if v := c.get(s); s.Err == "" && v >= 0 {
				xs = append(xs, v)
			}
		}
		fmt.Printf("| %s | %.1f | %.1f | %.1f | %.1f | %.1f |\n", c.name, pct(xs, 0), pct(xs, 0.1), pct(xs, 0.5), pct(xs, 0.9), pct(xs, 1))
	}
}
