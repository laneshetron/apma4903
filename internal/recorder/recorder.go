// Package recorder appends every raw market-data message to hourly gzipped
// JSONL files. It is the source of truth for offline replay.
//
// Each line is {"rx_ns": <receive time, unix ns>, "raw": <message verbatim>}.
// Files live at <dir>/raw/YYYY-MM-DD/HH.jsonl.gz in UTC.
package recorder

import (
	"bufio"
	"bytes"
	"compress/gzip"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"sync"
	"sync/atomic"
	"time"
)

// LocalEvent is a collector-side event written into the same stream as
// exchange messages so replay knows about connection state. Its wire form is
// {"type":"_local","event":..., ...fields}.
type LocalEvent struct {
	Event  string         `json:"event"`
	Fields map[string]any `json:"-"`
}

// LocalType is the type field of collector-side events.
const LocalType = "_local"

// Local event names.
const (
	EventConnect      = "connect"
	EventDisconnect   = "disconnect"
	EventSubscribed   = "subscribed"
	EventGap          = "gap"
	EventResync       = "resync"
	EventRESTSnapshot = "rest_snapshot"
	EventMarketsSync  = "markets_sync"
)

// Recorder writes records. Safe for concurrent use.
type Recorder struct {
	dir  string
	now  func() time.Time
	rate time.Duration

	mu     sync.Mutex
	hour   time.Time // start of the hour the open file covers
	f      *os.File
	gz     *gzip.Writer
	w      *bufio.Writer
	closed bool
	stop   chan struct{}
	done   chan struct{}

	// Write hands records to a background goroutine so gzip never runs on the
	// caller (the feed reader or the trading loop); the channel is bounded so
	// a stalled disk applies back-pressure instead of unbounded memory.
	queue   chan record
	wdone   chan struct{}
	dropped atomic.Uint64

	lines uint64
}

type record struct {
	rx  time.Time
	raw []byte
}

// Open creates a recorder rooted at dir and starts a periodic flusher.
func Open(dir string, flushEvery time.Duration) (*Recorder, error) {
	if err := os.MkdirAll(filepath.Join(dir, "raw"), 0o755); err != nil {
		return nil, err
	}
	r := &Recorder{dir: dir, now: time.Now, rate: flushEvery, stop: make(chan struct{}), done: make(chan struct{}),
		queue: make(chan record, 65536), wdone: make(chan struct{})}
	go r.flushLoop()
	go r.writeLoop()
	return r, nil
}

// writeLoop drains the queue into the gzip stream.
func (r *Recorder) writeLoop() {
	defer close(r.wdone)
	for rec := range r.queue {
		r.mu.Lock()
		err := r.writeLocked(rec.rx, rec.raw)
		r.mu.Unlock()
		if err != nil {
			r.dropped.Add(1)
		}
	}
}

// Write queues one record. It never blocks on compression; if the queue is
// full (disk stalled) it blocks briefly rather than dropping data.
func (r *Recorder) Write(rx time.Time, raw []byte) error {
	raw = bytes.TrimRight(raw, " \t\r\n")
	cp := make([]byte, len(raw))
	copy(cp, raw) // the caller may reuse its buffer
	r.mu.Lock()
	closed := r.closed
	r.mu.Unlock()
	if closed {
		return fmt.Errorf("recorder: closed")
	}
	r.queue <- record{rx, cp}
	return nil
}

func (r *Recorder) flushLoop() {
	defer close(r.done)
	t := time.NewTicker(r.rate)
	defer t.Stop()
	for {
		select {
		case <-t.C:
			r.mu.Lock()
			if r.w != nil {
				_ = r.w.Flush()
				_ = r.gz.Flush()
			}
			r.mu.Unlock()
		case <-r.stop:
			return
		}
	}
}

// Path returns the file path for the hour containing t.
func (r *Recorder) Path(t time.Time) string {
	t = t.UTC()
	return filepath.Join(r.dir, "raw", t.Format("2006-01-02"), t.Format("15")+".jsonl.gz")
}

// rotate ensures the open file covers hour h. Caller holds mu.
func (r *Recorder) rotate(h time.Time) error {
	if r.f != nil && h.Equal(r.hour) {
		return nil
	}
	if err := r.closeFileLocked(); err != nil {
		return err
	}
	p := r.Path(h)
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		return err
	}
	f, err := os.OpenFile(p, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
	if err != nil {
		return err
	}
	// Each open appends a fresh gzip member; gzip readers concatenate members.
	r.f, r.gz = f, gzip.NewWriter(f)
	r.w = bufio.NewWriterSize(r.gz, 256<<10)
	r.hour = h
	return nil
}

func (r *Recorder) closeFileLocked() error {
	if r.f == nil {
		return nil
	}
	err1 := r.w.Flush()
	err2 := r.gz.Close()
	err3 := r.f.Close()
	r.f, r.gz, r.w = nil, nil, nil
	for _, err := range []error{err1, err2, err3} {
		if err != nil {
			return err
		}
	}
	return nil
}

// Write records one raw message received at rx. Trailing whitespace is
// dropped (Kalshi frames end with a newline) so each record stays on one line.
func (r *Recorder) writeLocked(rx time.Time, raw []byte) error {
	if err := r.rotate(rx.UTC().Truncate(time.Hour)); err != nil {
		return err
	}
	r.w.WriteString(`{"rx_ns":`)
	r.w.WriteString(strconv.FormatInt(rx.UnixNano(), 10))
	r.w.WriteString(`,"raw":`)
	r.w.Write(raw)
	if _, err := r.w.WriteString("}\n"); err != nil {
		return err
	}
	r.lines++
	return nil
}

// WriteLocal records a collector-side event with arbitrary extra fields.
func (r *Recorder) WriteLocal(event string, fields map[string]any) error {
	m := make(map[string]any, len(fields)+2)
	for k, v := range fields {
		m[k] = v
	}
	m["type"] = LocalType
	m["event"] = event
	raw, err := json.Marshal(m)
	if err != nil {
		return err
	}
	return r.Write(r.now(), raw)
}

// Lines returns the number of records written.
func (r *Recorder) Lines() uint64 {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.lines
}

// Close flushes and closes the current file.
func (r *Recorder) Close() error {
	close(r.stop)
	<-r.done
	r.mu.Lock()
	r.closed = true
	r.mu.Unlock()
	close(r.queue) // flush whatever is queued, then close the file
	<-r.wdone
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.closeFileLocked()
}

// Record is one decoded line of a raw file.
type Record struct {
	RxNs int64           `json:"rx_ns"`
	Raw  json.RawMessage `json:"raw"`
}
