package quoter

import (
	"encoding/json"
	"math"
	"os"
	"testing"
)

func TestEdgeModelMatchesPython(t *testing.T) {
	m, err := LoadEdgeModel("testdata/tables.json")
	if err != nil {
		t.Fatal(err)
	}
	b, _ := os.ReadFile("testdata/tables.json")
	var fx struct {
		Fixtures []struct {
			Side  string   `json:"side"`
			Imb   float64  `json:"imb"`
			Micro *float64 `json:"micro"`
			TTX   float64  `json:"ttx_min"`
			Q     float64  `json:"q"`
			Edge  *float64 `json:"edge"`
		} `json:"fixtures"`
	}
	if err := json.Unmarshal(b, &fx); err != nil {
		t.Fatal(err)
	}
	if len(fx.Fixtures) < 100 {
		t.Fatalf("too few fixtures: %d", len(fx.Fixtures))
	}
	for i, f := range fx.Fixtures {
		got, ok := m.Edge(f.Side, f.Imb, f.Micro, f.TTX, f.Q)
		if f.Edge == nil {
			if ok {
				t.Errorf("fixture %d: python has no edge, go returned %v", i, got)
			}
			continue
		}
		if !ok || math.Abs(got-*f.Edge) > 1e-9 {
			t.Errorf("fixture %d %+v: got %v ok=%v, want %v", i, f, got, ok, *f.Edge)
		}
	}
}

func TestBuckets(t *testing.T) {
	lower := []float64{0, 50, 100, 200}
	for x, want := range map[float64]int{-1: 0, 0: 0, 49.9: 0, 50: 1, 199: 2, 200: 3, 1e6: 3} {
		if got := bucketLower(x, lower); got != want {
			t.Errorf("bucketLower(%v) = %d, want %d", x, got, want)
		}
	}
	cuts := []float64{-0.33, 0.33}
	for x, want := range map[float64]int{-1: 0, -0.34: 0, -0.33: 1, 0: 1, 0.32: 1, 0.33: 2, 1: 2} {
		if got := bucketCut(x, cuts); got != want {
			t.Errorf("bucketCut(%v) = %d, want %d", x, got, want)
		}
	}
}
