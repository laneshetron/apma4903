// Package recorder appends every raw market-data message to hourly JSONL
// files. It is the source of truth for offline replay.
//
// Each line is {"rx_ns": <receive time, unix ns>, "raw": <message verbatim>}.
// Files live at <dir>/raw/YYYY-MM-DD/HH.jsonl.{gz,zst} in UTC.
//
// With CodecZstd the payload is ~45% smaller than gzip and, more usefully, is
// written as independently decompressable frames of SegmentBytes each, with a
// sidecar <HH>.idx listing every frame:
//
//	# off,first_rx_ns,last_rx_ns,records
//	0,1789927201114000000,1789927261992000000,41233
//
// A reader wanting one minute out of an hour seeks to the frames whose time
// range overlaps it instead of decompressing from the start of the file. That
// is the shape borrowed from github.com/laneshetron/zseries, whose segment +
// index layout this follows.
package recorder

import (
	"bufio"
	"bytes"
	"compress/gzip"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"sync"
	"sync/atomic"
	"time"

	"github.com/klauspost/compress/zstd"
)

// Codec selects the on-disk compression.
type Codec int

const (
	CodecGzip Codec = iota // .jsonl.gz, one gzip member per file open
	CodecZstd              // .jsonl.zst, independent frames + .idx sidecar
)

// SegmentBytes is how much uncompressed payload goes into one zstd frame.
// Smaller means finer seeking and slightly worse compression.
const SegmentBytes = 4 << 20

// ZstdLevel is deliberately low: this runs on the feed's write path, and the
// archive pass (deploy/recompress.sh) recompresses cold days harder.
var ZstdLevel = zstd.SpeedDefault

// countWriter tracks the byte offset of the next write, which is where the
// next zstd frame will begin.
type countWriter struct {
	w io.Writer
	n int64
}

func (c *countWriter) Write(p []byte) (int, error) {
	n, err := c.w.Write(p)
	c.n += int64(n)
	return n, err
}

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

	codec Codec

	mu     sync.Mutex
	hour   time.Time // start of the hour the open file covers
	f      *os.File
	gz     *gzip.Writer
	zw     *zstd.Encoder
	cw     *countWriter
	w      *bufio.Writer
	closed bool
	stop   chan struct{}
	done   chan struct{}

	// current zstd frame (CodecZstd only)
	idx        *os.File
	frameOff   int64
	frameFirst int64
	frameLast  int64
	frameRecs  int64
	frameBytes int

	// Write hands records to a background goroutine so compression never runs on the
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

// Open creates a gzip recorder rooted at dir and starts a periodic flusher.
func Open(dir string, flushEvery time.Duration) (*Recorder, error) {
	return OpenCodec(dir, flushEvery, CodecGzip)
}

// OpenCodec creates a recorder with an explicit on-disk codec.
func OpenCodec(dir string, flushEvery time.Duration, codec Codec) (*Recorder, error) {
	if err := os.MkdirAll(filepath.Join(dir, "raw"), 0o755); err != nil {
		return nil, err
	}
	r := &Recorder{dir: dir, now: time.Now, rate: flushEvery, codec: codec, stop: make(chan struct{}), done: make(chan struct{}),
		queue: make(chan record, 65536), wdone: make(chan struct{})}
	go r.flushLoop()
	go r.writeLoop()
	return r, nil
}

// writeLoop drains the queue into the compressed stream.
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
				if r.gz != nil {
					_ = r.gz.Flush()
				}
				if r.zw != nil {
					_ = r.zw.Flush()
				}
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
	ext := ".jsonl.gz"
	if r.codec == CodecZstd {
		ext = ".jsonl.zst"
	}
	return filepath.Join(r.dir, "raw", t.Format("2006-01-02"), t.Format("15")+ext)
}

// IndexPath returns the sidecar index path for the hour containing t (CodecZstd).
func (r *Recorder) IndexPath(t time.Time) string {
	t = t.UTC()
	return filepath.Join(r.dir, "raw", t.Format("2006-01-02"), t.Format("15")+".idx")
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
	if r.codec == CodecZstd {
		st, err := f.Stat()
		if err != nil {
			f.Close()
			return err
		}
		idx, err := os.OpenFile(r.IndexPath(h), os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
		if err != nil {
			f.Close()
			return err
		}
		if st.Size() == 0 {
			if _, err := idx.WriteString("# off,first_rx_ns,last_rx_ns,records\n"); err != nil {
				f.Close()
				idx.Close()
				return err
			}
		}
		// Appending starts a new frame at the current end of file, so a restart
		// mid-hour never corrupts the frames already written.
		cw := &countWriter{w: f, n: st.Size()}
		zw, err := zstd.NewWriter(cw, zstd.WithEncoderLevel(ZstdLevel))
		if err != nil {
			f.Close()
			idx.Close()
			return err
		}
		r.f, r.cw, r.zw, r.idx = f, cw, zw, idx
		r.w = bufio.NewWriterSize(zw, 256<<10)
		r.frameOff, r.frameFirst, r.frameLast, r.frameRecs, r.frameBytes = st.Size(), 0, 0, 0, 0
		r.hour = h
		return nil
	}
	// Each open appends a fresh gzip member; gzip readers concatenate members.
	r.f, r.gz = f, gzip.NewWriter(f)
	r.w = bufio.NewWriterSize(r.gz, 256<<10)
	r.hour = h
	return nil
}

// endFrameLocked closes the current zstd frame and records it in the index, so
// that the bytes from frameOff onward decompress on their own. Caller holds mu.
func (r *Recorder) endFrameLocked() error {
	if r.zw == nil || r.frameRecs == 0 {
		return nil
	}
	if err := r.w.Flush(); err != nil {
		return err
	}
	if err := r.zw.Close(); err != nil { // ends the frame
		return err
	}
	if _, err := fmt.Fprintf(r.idx, "%d,%d,%d,%d\n", r.frameOff, r.frameFirst, r.frameLast, r.frameRecs); err != nil {
		return err
	}
	r.frameOff = r.cw.n
	r.frameFirst, r.frameLast, r.frameRecs, r.frameBytes = 0, 0, 0, 0
	r.zw.Reset(r.cw)
	return nil
}

func (r *Recorder) closeFileLocked() error {
	if r.f == nil {
		return nil
	}
	var errs []error
	if r.codec == CodecZstd {
		errs = append(errs, r.endFrameLocked())
		// endFrameLocked left a reset (empty) encoder; closing it writes an
		// empty frame, which readers skip.
		errs = append(errs, r.zw.Close(), r.idx.Sync(), r.idx.Close())
		r.zw, r.cw, r.idx = nil, nil, nil
	} else {
		errs = append(errs, r.w.Flush(), r.gz.Close())
		r.gz = nil
	}
	errs = append(errs, r.f.Close())
	r.f, r.w = nil, nil
	for _, err := range errs {
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
	ns := rx.UnixNano()
	r.w.WriteString(`{"rx_ns":`)
	r.w.WriteString(strconv.FormatInt(ns, 10))
	r.w.WriteString(`,"raw":`)
	r.w.Write(raw)
	if _, err := r.w.WriteString("}\n"); err != nil {
		return err
	}
	r.lines++
	if r.codec == CodecZstd {
		if r.frameRecs == 0 {
			r.frameFirst = ns
		}
		r.frameLast = ns
		r.frameRecs++
		r.frameBytes += len(raw) + 24
		if r.frameBytes >= SegmentBytes {
			return r.endFrameLocked()
		}
	}
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
