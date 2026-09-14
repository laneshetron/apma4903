package kalshi

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"sync"
	"sync/atomic"
	"time"

	"github.com/coder/websocket"
)

// RawMessage is one server -> client frame with its local receive time.
type RawMessage struct {
	Rx   time.Time
	Data []byte
}

// Conn is a single authenticated WebSocket connection. A background reader
// routes command responses (messages carrying an id) to the waiting Do call
// and everything else to Messages. Once the reader fails, Err reports why and
// the connection must be discarded; reconnection is the caller's job.
type Conn struct {
	ws     *websocket.Conn
	nextID atomic.Int64

	msgs chan RawMessage
	done chan struct{}
	err  error

	mu      sync.Mutex
	waiters map[int]chan Envelope
}

// DialOptions configure Dial.
type DialOptions struct {
	// ReadLimit caps a single frame; snapshots for many markets can be large.
	ReadLimit int64
	// Buffer is the capacity of the Messages channel.
	Buffer int
	// HTTPClient is used for the handshake (optional).
	HTTPClient *http.Client
}

// Dial opens and authenticates a connection to env.
func Dial(ctx context.Context, env Env, signer *Signer, opts DialOptions) (*Conn, error) {
	if opts.ReadLimit == 0 {
		opts.ReadLimit = 32 << 20
	}
	if opts.Buffer == 0 {
		opts.Buffer = 4096
	}
	h, err := signer.Headers(http.MethodGet, WSPath)
	if err != nil {
		return nil, err
	}
	ws, resp, err := websocket.Dial(ctx, env.WSURL(), &websocket.DialOptions{
		HTTPHeader: h,
		HTTPClient: opts.HTTPClient,
	})
	if err != nil {
		if resp != nil {
			return nil, fmt.Errorf("kalshi: ws dial: HTTP %d: %w", resp.StatusCode, err)
		}
		return nil, fmt.Errorf("kalshi: ws dial: %w", err)
	}
	ws.SetReadLimit(opts.ReadLimit)
	c := &Conn{
		ws:      ws,
		msgs:    make(chan RawMessage, opts.Buffer),
		done:    make(chan struct{}),
		waiters: map[int]chan Envelope{},
	}
	go c.readLoop()
	return c, nil
}

// Messages delivers data messages in arrival order. It is closed when the
// connection dies; check Err afterwards.
func (c *Conn) Messages() <-chan RawMessage { return c.msgs }

// Done is closed when the reader has exited.
func (c *Conn) Done() <-chan struct{} { return c.done }

// Err returns the reader's terminal error (nil until Done is closed).
func (c *Conn) Err() error {
	select {
	case <-c.done:
		return c.err
	default:
		return nil
	}
}

func (c *Conn) readLoop() {
	defer close(c.done)
	defer close(c.msgs)
	ctx := context.Background()
	for {
		typ, data, err := c.ws.Read(ctx)
		rx := time.Now()
		if err != nil {
			c.err = err
			c.failWaiters(err)
			return
		}
		if typ != websocket.MessageText {
			continue
		}
		// Peek at id/type without decoding msg. Responses carry the command id.
		var head struct {
			ID   int    `json:"id"`
			Type string `json:"type"`
		}
		if json.Unmarshal(data, &head) == nil && head.ID != 0 && isResponse(head.Type) {
			c.mu.Lock()
			w, ok := c.waiters[head.ID]
			delete(c.waiters, head.ID)
			c.mu.Unlock()
			if ok {
				var env Envelope
				_ = json.Unmarshal(data, &env)
				w <- env
			}
			// Responses are also delivered downstream so the recorder sees them.
		}
		c.msgs <- RawMessage{Rx: rx, Data: data}
	}
}

func isResponse(t string) bool {
	switch t {
	case TypeSubscribed, TypeUnsubscribed, TypeOK, TypeError:
		return true
	}
	return false
}

func (c *Conn) failWaiters(err error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	for id, w := range c.waiters {
		close(w)
		delete(c.waiters, id)
	}
}

// ErrConnClosed is returned by Do when the connection died before a response arrived.
var ErrConnClosed = errors.New("kalshi: ws connection closed")

// Do sends a command and waits for the matching response. A server "error"
// response is returned as an *ErrorMsg.
func (c *Conn) Do(ctx context.Context, cmd string, params any) (*Envelope, error) {
	id := int(c.nextID.Add(1))
	w := make(chan Envelope, 1)
	c.mu.Lock()
	c.waiters[id] = w
	c.mu.Unlock()

	data, err := json.Marshal(Command{ID: id, Cmd: cmd, Params: params})
	if err != nil {
		return nil, err
	}
	if err := c.ws.Write(ctx, websocket.MessageText, data); err != nil {
		c.mu.Lock()
		delete(c.waiters, id)
		c.mu.Unlock()
		return nil, fmt.Errorf("kalshi: ws write %s: %w", cmd, err)
	}
	select {
	case env, ok := <-w:
		if !ok {
			return nil, ErrConnClosed
		}
		if env.Type == TypeError {
			var em ErrorMsg
			_ = env.Decode(&em)
			return &env, &em
		}
		return &env, nil
	case <-ctx.Done():
		c.mu.Lock()
		delete(c.waiters, id)
		c.mu.Unlock()
		return nil, ctx.Err()
	}
}

// Subscribe subscribes channel for the given markets (nil = all, where allowed)
// and returns the server-assigned sid.
func (c *Conn) Subscribe(ctx context.Context, channel string, tickers []string) (int, error) {
	env, err := c.Do(ctx, "subscribe", SubscribeParams{Channels: []string{channel}, MarketTickers: tickers})
	if err != nil {
		return 0, err
	}
	var m SubscribedMsg
	if err := env.Decode(&m); err != nil {
		return 0, err
	}
	return m.Sid, nil
}

// UpdateSubscription applies add_markets / delete_markets / get_snapshot to a sid.
func (c *Conn) UpdateSubscription(ctx context.Context, sid int, action string, tickers []string) error {
	_, err := c.Do(ctx, "update_subscription", UpdateSubscriptionParams{Sids: []int{sid}, MarketTickers: tickers, Action: action})
	return err
}

// Unsubscribe cancels sids.
func (c *Conn) Unsubscribe(ctx context.Context, sids ...int) error {
	_, err := c.Do(ctx, "unsubscribe", UnsubscribeParams{Sids: sids})
	return err
}

// Ping sends a WebSocket ping and waits for the pong.
func (c *Conn) Ping(ctx context.Context) error { return c.ws.Ping(ctx) }

// Close closes the connection; the reader exits shortly after.
func (c *Conn) Close() error {
	return c.ws.Close(websocket.StatusNormalClosure, "bye")
}
