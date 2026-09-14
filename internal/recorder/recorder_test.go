package recorder

import (
	"bufio"
	"compress/gzip"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"
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
