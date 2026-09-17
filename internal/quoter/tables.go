package quoter

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
)

// EdgeModel is the fitted expected edge (half-spread + 30s markout, cents per
// contract) of a resting 100-lot by queue position and market state, exported
// by python/kalshi_data/research/export_tables.py. Marginal tables by state
// are combined additively around the all-state curve, exactly as in the sim.
type EdgeModel struct {
	FittedOn   string       `json:"fitted_on"`
	QEdges     []float64    `json:"q_edges"`     // lower edges of queue-ahead buckets
	ImbEdges   []float64    `json:"imb_edges"`   // interior cut points
	MicroEdges []float64    `json:"micro_edges"` // interior cut points ($)
	TTXEdges   []float64    `json:"ttx_edges"`   // interior cut points (minutes)
	All        []*float64   `json:"all"`
	Imb        [][]*float64 `json:"imb"`
	Micro      [][]*float64 `json:"micro"`
	TTX        [][]*float64 `json:"ttx"`
}

// LoadEdgeModel reads the JSON written by export_tables.py.
func LoadEdgeModel(path string) (*EdgeModel, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var m EdgeModel
	if err := json.Unmarshal(b, &m); err != nil {
		return nil, fmt.Errorf("edge model %s: %w", path, err)
	}
	if len(m.All) != len(m.QEdges) || len(m.Imb) != len(m.ImbEdges)+1 || len(m.Micro) != len(m.MicroEdges)+1 || len(m.TTX) != len(m.TTXEdges)+1 {
		return nil, errors.New("edge model: table shapes do not match edges")
	}
	return &m, nil
}

// bucketLower returns the index of the last lower edge <= x (edges ascending; x below the first edge maps to 0).
func bucketLower(x float64, lower []float64) int {
	i := 0
	for j := 1; j < len(lower); j++ {
		if x >= lower[j] {
			i = j
		}
	}
	return i
}

// bucketCut returns the bucket index for interior cut points c: x < c[0] -> 0, c[0] <= x < c[1] -> 1, ...
func bucketCut(x float64, cuts []float64) int {
	i := 0
	for _, c := range cuts {
		if x >= c {
			i++
		}
	}
	return i
}

// Edge returns the expected edge in cents of a resting order on side ("yes" bid
// or "no" bid) with q contracts ahead, given the touch imbalance from the
// resting order's point of view ((other - ours)/(other + ours)), the unsigned
// Coinbase microprice pressure in $ (nil if unknown) and minutes to expiry.
// ok=false when the all-state curve has no estimate for this queue bucket.
func (m *EdgeModel) Edge(side string, imb float64, micro *float64, ttxMin float64, q float64) (float64, bool) {
	qi := bucketLower(q, m.QEdges)
	base := m.All[qi]
	if base == nil {
		return 0, false
	}
	e := *base
	if c := m.Imb[bucketCut(imb, m.ImbEdges)][qi]; c != nil {
		e += *c - *base
	}
	if micro != nil {
		// pressure against a YES bid is spot going down (micro < 0); against a NO bid (our ask) it is up
		x := *micro
		if side == "yes" {
			x = -x
		}
		if c := m.Micro[bucketCut(x, m.MicroEdges)][qi]; c != nil {
			e += *c - *base
		}
	}
	if c := m.TTX[bucketCut(ttxMin, m.TTXEdges)][qi]; c != nil {
		e += *c - *base
	}
	return e, true
}
