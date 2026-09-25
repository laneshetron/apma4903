package recorder

import (
	"bufio"
	"compress/gzip"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/klauspost/compress/zstd"
)

func readAll(t *testing.T, p string) []Record {
	t.Helper()
	f, err := os.Open(p)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	gz, err := gzip.NewReader(f)
	if err != nil {
		t.Fatal(err)
	}
	var out []Record
	sc := bufio.NewScanner(gz)
	for sc.Scan() {
		var rec Record
		if err := json.Unmarshal(sc.Bytes(), &rec); err != nil {
			t.Fatalf("bad line %q: %v", sc.Text(), err)
		}
		out = append(out, rec)
	}
	return out
}

func TestWriteRotateAndReopen(t *testing.T) {
	dir := t.TempDir()
	r, err := Open(dir, time.Hour)
	if err != nil {
		t.Fatal(err)
	}
	t0 := time.Date(2026, 9, 13, 20, 59, 59, 0, time.UTC)
	t1 := t0.Add(2 * time.Second) // crosses into 21:00
	r.now = func() time.Time { return t0 }

	if err := r.Write(t0, []byte(`{"type":"trade","sid":1}`)); err != nil {
		t.Fatal(err)
	}
	if err := r.WriteLocal(EventConnect, map[string]any{"url": "wss://x"}); err != nil {
		t.Fatal(err)
	}
	if err := r.Write(t1, []byte(`{"type":"orderbook_delta","sid":2}`)); err != nil {
		t.Fatal(err)
	}
	if err := r.Close(); err != nil {
		t.Fatal(err)
	}

	p0 := filepath.Join(dir, "raw", "2026-09-13", "20.jsonl.gz")
	p1 := filepath.Join(dir, "raw", "2026-09-13", "21.jsonl.gz")
	recs0 := readAll(t, p0)
	if len(recs0) != 2 || recs0[0].RxNs != t0.UnixNano() {
		t.Fatalf("hour 20: %+v", recs0)
	}
	var local map[string]any
	_ = json.Unmarshal(recs0[1].Raw, &local)
	if local["type"] != LocalType || local["event"] != EventConnect || local["url"] != "wss://x" {
		t.Errorf("local event = %v", local)
	}
	if recs1 := readAll(t, p1); len(recs1) != 1 || string(recs1[0].Raw) != `{"type":"orderbook_delta","sid":2}` {
		t.Fatalf("hour 21: %+v", recs1)
	}

	// Reopen and append to the same hour: gzip members concatenate.
	r, err = Open(dir, time.Hour)
	if err != nil {
		t.Fatal(err)
	}
	if err := r.Write(t1.Add(time.Second), []byte(`{"type":"trade","sid":3}`)); err != nil {
		t.Fatal(err)
	}
	if err := r.Close(); err != nil {
		t.Fatal(err)
	}
	if recs1 := readAll(t, p1); len(recs1) != 2 {
		t.Fatalf("after reopen hour 21 has %d records", len(recs1))
	}
	if r.Write(t1, []byte("{}")) == nil {
		t.Error("write after close should fail")
	}
}

// --- CodecZstd: seekable frames + index sidecar (the zseries layout) ---

func readIndex(t *testing.T, p string) [][4]int64 {
	t.Helper()
	b, err := os.ReadFile(p)
	if err != nil {
		t.Fatal(err)
	}
	var out [][4]int64
	for _, ln := range strings.Split(strings.TrimSpace(string(b)), "\n") {
		if ln == "" || ln[0] == '#' {
			continue
		}
		var e [4]int64
		if _, err := fmt.Sscanf(ln, "%d,%d,%d,%d", &e[0], &e[1], &e[2], &e[3]); err != nil {
			t.Fatalf("index line %q: %v", ln, err)
		}
		out = append(out, e)
	}
	return out
}

// writeN writes n records of roughly `pad` bytes each, one millisecond apart.
func writeN(t *testing.T, r *Recorder, base time.Time, n, pad int) {
	t.Helper()
	body := strings.Repeat("x", pad)
	for i := range n {
		raw := fmt.Appendf(nil, `{"i":%d,"p":%q}`, i, body)
		if err := r.Write(base.Add(time.Duration(i)*time.Millisecond), raw); err != nil {
			t.Fatal(err)
		}
	}
}

func TestZstdRoundTripAndFraming(t *testing.T) {
	dir := t.TempDir()
	r, err := OpenCodec(dir, 10*time.Millisecond, CodecZstd)
	if err != nil {
		t.Fatal(err)
	}
	base := time.Date(2026, 9, 25, 4, 0, 0, 0, time.UTC)
	const n, pad = 60000, 400 // ~25 MB uncompressed -> several 4 MiB frames
	writeN(t, r, base, n, pad)
	if err := r.Close(); err != nil {
		t.Fatal(err)
	}

	p := filepath.Join(dir, "raw", "2026-09-25", "04.jsonl.zst")
	raw, err := os.ReadFile(p)
	if err != nil {
		t.Fatal(err)
	}
	dec, err := zstd.NewReader(nil)
	if err != nil {
		t.Fatal(err)
	}
	defer dec.Close()
	all, err := dec.DecodeAll(raw, nil)
	if err != nil {
		t.Fatalf("decode whole file: %v", err)
	}
	lines := strings.Count(string(all), "\n")
	if lines != n {
		t.Fatalf("records = %d, want %d", lines, n)
	}

	idx := readIndex(t, filepath.Join(dir, "raw", "2026-09-25", "04.idx"))
	if len(idx) < 2 {
		t.Fatalf("expected several frames, got %d", len(idx))
	}
	var recs int64
	for _, e := range idx {
		recs += e[3]
	}
	if recs != int64(n) {
		t.Errorf("index accounts for %d records, want %d", recs, n)
	}

	// The point of the layout: every frame decompresses on its own, from the
	// byte offset the index gives, without touching the frames before it.
	for i, e := range idx {
		off := e[0]
		end := int64(len(raw))
		if i+1 < len(idx) {
			end = idx[i+1][0]
		}
		got, err := dec.DecodeAll(raw[off:end], nil)
		if err != nil {
			t.Fatalf("frame %d at %d: %v", i, off, err)
		}
		if int64(strings.Count(string(got), "\n")) != e[3] {
			t.Errorf("frame %d: %d records, index says %d", i, strings.Count(string(got), "\n"), e[3])
		}
		// and its records really do fall in the advertised time range
		first := strings.SplitN(string(got), "\n", 2)[0]
		var rec Record
		if err := json.Unmarshal([]byte(first), &rec); err != nil {
			t.Fatal(err)
		}
		if rec.RxNs != e[1] {
			t.Errorf("frame %d: first rx_ns %d, index says %d", i, rec.RxNs, e[1])
		}
		if e[1] > e[2] {
			t.Errorf("frame %d: first_rx %d after last_rx %d", i, e[1], e[2])
		}
	}
}

func TestZstdReopenAppendsCleanly(t *testing.T) {
	dir := t.TempDir()
	base := time.Date(2026, 9, 25, 4, 0, 0, 0, time.UTC)
	for range 3 { // three process lifetimes inside one hour
		r, err := OpenCodec(dir, time.Hour, CodecZstd)
		if err != nil {
			t.Fatal(err)
		}
		writeN(t, r, base, 100, 50)
		if err := r.Close(); err != nil {
			t.Fatal(err)
		}
	}
	raw, err := os.ReadFile(filepath.Join(dir, "raw", "2026-09-25", "04.jsonl.zst"))
	if err != nil {
		t.Fatal(err)
	}
	dec, _ := zstd.NewReader(nil)
	defer dec.Close()
	all, err := dec.DecodeAll(raw, nil)
	if err != nil {
		t.Fatalf("decode after reopen: %v", err)
	}
	if got := strings.Count(string(all), "\n"); got != 300 {
		t.Fatalf("records after 3 opens = %d, want 300", got)
	}
	idx := readIndex(t, filepath.Join(dir, "raw", "2026-09-25", "04.idx"))
	var recs int64
	for _, e := range idx {
		recs += e[3]
	}
	if recs != 300 {
		t.Errorf("index accounts for %d, want 300", recs)
	}
	// offsets must be strictly increasing, or seeking is meaningless
	for i := 1; i < len(idx); i++ {
		if idx[i][0] <= idx[i-1][0] {
			t.Errorf("frame offsets not increasing: %d then %d", idx[i-1][0], idx[i][0])
		}
	}
}

func TestGzipUnchangedByCodecWork(t *testing.T) {
	dir := t.TempDir()
	r, err := Open(dir, time.Hour)
	if err != nil {
		t.Fatal(err)
	}
	base := time.Date(2026, 9, 25, 4, 0, 0, 0, time.UTC)
	writeN(t, r, base, 50, 20)
	if err := r.Close(); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(dir, "raw", "2026-09-25", "04.jsonl.gz")); err != nil {
		t.Fatalf("gzip path: %v", err)
	}
	if _, err := os.Stat(filepath.Join(dir, "raw", "2026-09-25", "04.idx")); !os.IsNotExist(err) {
		t.Error("gzip recorder must not write an index sidecar")
	}
}
