"""Adverse selection: can it be predicted before the sweep?

    uv run python -m kalshi_data.research.alpha 2026-09-14 [--series KXBTC15M]

Builds one row per taker sweep with
  * spot microstructure features at the moment of the sweep (Coinbase
    top-of-book imbalance and microprice, trade-flow imbalance on Coinbase /
    Kraken / Gemini / Bitstamp, spot returns, Kraken-Coinbase gap),
  * Kalshi state (touch depth both sides, previous sweep toxic?, sweep size),
  * option state (moneyness d and minutes to expiry from the market strike
    and BRTI realized vol),
  * targets: maker markouts at 1/10/30/60s, spot move after the sweep.
Every directional feature is signed into the TAKER's direction, so positive
means "the feature agrees with the taker" (bad for the maker).

Then: markouts bucketed by each feature; a ridge alpha (spot move 5s ahead)
fit on the first 60% of the day and tested on the rest; markouts bucketed by
out-of-sample predicted alpha. Rows are written to research/alpha_<day>.parquet.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import re
import time
import sys
import urllib.request
from collections import deque
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl

from ..raw import iter_records
from ..spot import SpotQuote, SpotTrade, iter_spot
from .markouts import HORIZONS_S, IDX_HORIZONS_S, Analyzer, MarketState, Sweep

BASE = "https://api.elections.kalshi.com/trade-api/v2"
VENUES = ("coinbase", "kraken", "gemini_btc", "bitstamp")


class Flow:
    """Signed trade volume over trailing windows."""

    def __init__(self, windows=(1, 5)):
        self.w = windows
        self.q: deque = deque()  # (rx_ns, signed_size, size)

    def add(self, rx: int, side: str, size: float) -> None:
        self.q.append((rx, size if side == "buy" else -size, size))
        while self.q and self.q[0][0] < rx - max(self.w) * 1_000_000_000:
            self.q.popleft()

    def imb(self, rx: int, w: int) -> float | None:
        lo = rx - w * 1_000_000_000
        net = tot = 0.0
        for r, sgn, sz in reversed(self.q):
            if r < lo:
                break
            net += sgn
            tot += sz
        return net / tot if tot > 0 else None


class SpotState:
    def __init__(self):
        self.cb_bid = self.cb_ask = self.cb_bs = self.cb_as = None
        self.kr_bid = self.kr_ask = None
        self.mids: deque = deque()  # (rx_ns, coinbase mid) last 35s
        self.flow = {v: Flow() for v in VENUES}
        self.brti: deque = deque()  # (rx_ns, value) last 5 min for realized vol
        self.brti_last = None
        self._vol = None
        self._n_brti = 0

    def on_quote(self, q: SpotQuote) -> None:
        if q.venue == "coinbase":
            self.cb_bid, self.cb_ask = q.bid, q.ask
            self.mids.append((q.rx_ns, (q.bid + q.ask) / 2))
            while self.mids and self.mids[0][0] < q.rx_ns - 35_000_000_000:
                self.mids.popleft()
        elif q.venue == "kraken":
            self.kr_bid, self.kr_ask = q.bid, q.ask

    def on_quote_sizes(self, bs: float, as_: float) -> None:
        self.cb_bs, self.cb_as = bs, as_

    def on_trade(self, t: SpotTrade) -> None:
        self.flow[t.venue].add(t.rx_ns, t.side, t.size)

    def on_brti(self, rx: int, v: float) -> None:
        self.brti.append((rx, v))
        self.brti_last = v
        while self.brti and self.brti[0][0] < rx - 300_000_000_000:
            self.brti.popleft()
        self._n_brti += 1
        if self._n_brti % 25 == 0:   # refresh the cached vol every ~5s of ticks
            self._vol = self._realized_vol()

    def mid_ago(self, rx: int, s: float) -> float | None:
        lo = rx - int(s * 1e9)
        for r, m in self.mids:
            if r >= lo:
                return m
        return None

    def cb_mid(self) -> float | None:
        return (self.cb_bid + self.cb_ask) / 2 if self.cb_bid else None

    def realized_vol(self) -> float | None:
        return self._vol

    def _realized_vol(self) -> float | None:
        """std of BRTI log returns over the last 5 min, scaled to per sqrt(second)."""
        if len(self.brti) < 30:
            return None
        vals = [v for _, v in self.brti]
        rets = np.diff(np.log(vals))
        # ticks are 5hz; scale to per-second
        return float(np.std(rets) * math.sqrt(5)) if len(rets) > 10 else None

    def features(self, rx: int, sign: int) -> dict:
        f = {}
        mid = self.cb_mid()
        if mid is None:
            return f
        if self.cb_bs is not None and self.cb_as is not None and self.cb_bs + self.cb_as > 0:
            f["cb_imb"] = sign * (self.cb_bs - self.cb_as) / (self.cb_bs + self.cb_as)
            micro = (self.cb_bid * self.cb_as + self.cb_ask * self.cb_bs) / (self.cb_bs + self.cb_as)
            f["cb_micro"] = sign * (micro - mid)
        f["cb_spread"] = self.cb_ask - self.cb_bid
        for s in (1, 5, 30):
            m0 = self.mid_ago(rx, s)
            if m0 is not None:
                f[f"ret_{s}s"] = sign * (mid - m0)
        if self.kr_bid:
            f["kr_minus_cb"] = sign * ((self.kr_bid + self.kr_ask) / 2 - mid)
        for v, fl in self.flow.items():
            for w in (1, 5):
                x = fl.imb(rx, w)
                if x is not None:
                    f[f"{v}_flow_{w}s"] = sign * x
        return f


class FeatureAnalyzer(Analyzer):
    def __init__(self, series, spot: SpotState, strikes: dict[str, float]):
        super().__init__(series)
        self.spot = spot
        self.strikes = strikes
        self.last_sweep: dict[str, Sweep] = {}

    def on_sweep_open(self, sw: Sweep, ms: MarketState) -> None:
        f = self.spot.features(sw.rx_ns, sw.sign)
        b = ms.book
        if not b.stale and b.best_yes >= 0 and b.best_no >= 0:
            yd, nd = b.yes.get(b.best_yes, 0), b.no.get(b.best_no, 0)
            # depth on the side the taker is consuming vs the other side
            hit, other = (nd, yd) if sw.taker_side == "yes" else (yd, nd)
            f["touch_depth_hit"] = hit / 100
            f["touch_imb"] = (other - hit) / (other + hit) if other + hit > 0 else 0.0
            f["mid"] = b.mid()
        prev = self.last_sweep.get(sw.ticker)
        f["prev_full_2s"] = 1.0 if prev is not None and sw.rx_ns - prev.rx_ns <= 2_000_000_000 and prev.klass in ("full", "multi") else 0.0
        f["prev_same_dir_2s"] = 1.0 if prev is not None and sw.rx_ns - prev.rx_ns <= 2_000_000_000 and prev.taker_side == sw.taker_side else 0.0
        self.last_sweep[sw.ticker] = sw
        K = self.strikes.get(sw.ticker)
        S = self.spot.brti_last
        vol = self.spot.realized_vol()
        tau = max(1.0, ms.close_ts - sw.rx_ns / 1e9)  # seconds
        if K and S and vol:
            d = math.log(S / K) / (vol * math.sqrt(tau))
            f["d"] = d
            f["abs_d"] = abs(d)
            f["delta_x_sigma10"] = math.exp(-d * d / 2) / math.sqrt(2 * math.pi) / (vol * math.sqrt(tau)) * vol * math.sqrt(10)  # dP per 10s sigma move
            f["vol_1s_bp"] = vol * 1e4
        f["tau_min"] = tau / 60
        sw.feats = f


_STRIKE_CACHE = Path("../research/strikes_cache.json")
_TICKER_STRIKE = re.compile(r"-[TB](\d+(?:\.\d+)?)$")   # KXBTCD-26SEP1717-T76499.99 -> 76499.99


def fetch_strikes(tickers: list[str]) -> dict[str, float]:
    out = {}
    cache = {}
    try:
        cache = json.loads(_STRIKE_CACHE.read_text())
    except Exception:  # noqa: BLE001
        pass
    todo = []
    for t in tickers:
        m = _TICKER_STRIKE.search(t)
        if m:
            out[t] = float(m.group(1))
        elif t in cache:
            out[t] = cache[t]
        else:
            todo.append(t)
    for t in todo:
        try:
            with urllib.request.urlopen(f"{BASE}/markets/{t}", timeout=20) as r:
                m = json.load(r)["market"]
            k = m.get("floor_strike") or m.get("cap_strike")
            if k is not None:
                out[t] = float(k)
                cache[t] = float(k)
            time.sleep(0.12)
        except Exception as e:  # noqa: BLE001
            print(f"strike {t}: {e}", file=sys.stderr)
            time.sleep(1.0)
    if todo:
        try:
            _STRIKE_CACHE.write_text(json.dumps(cache))
        except Exception:  # noqa: BLE001
            pass
    return out


def build(data_dir: Path, day: date, series: str) -> pl.DataFrame:
    # strikes for the day's markets (tickers seen in the log)
    tickers = set()
    for rec in iter_records(data_dir, day):
        raw = rec.raw
        if raw.get("type") == "orderbook_snapshot" and raw["msg"]["market_ticker"].startswith(series + "-"):
            tickers.add(raw["msg"]["market_ticker"])
    print(f"fetching {len(tickers)} strikes...", file=sys.stderr)
    strikes = fetch_strikes(sorted(tickers))

    spot = SpotState()
    an = FeatureAnalyzer({series}, spot, strikes)
    an.signal_source = "spot"

    def spot_events():
        its = [iter_spot(data_dir, v, day) for v in VENUES]
        yield from heapq.merge(*its, key=lambda e: e.rx_ns)

    # Coinbase ticker sizes are not in SpotQuote; read them from the raw frames
    def cb_sizes():
        for rec in iter_records(data_dir / "spot" / "coinbase", day):
            raw = rec.raw
            if raw.get("type") == "ticker" and raw.get("product_id") == "BTC-USD" and raw.get("best_bid_size"):
                yield ("cbsz", rec.rx_ns, float(raw["best_bid_size"]), float(raw["best_ask_size"]))

    n = 0
    last_rx = 0
    stream = heapq.merge(iter_records(data_dir, day), spot_events(), cb_sizes(),
                         key=lambda e: e[1] if isinstance(e, tuple) else e.rx_ns)
    for ev in stream:
        n += 1
        if n % 5_000_000 == 0:
            print(f"  {n/1e6:.0f}M events, {len(an.sweeps):,} sweeps", file=sys.stderr)
        if isinstance(ev, tuple):
            spot.on_quote_sizes(ev[2], ev[3])
            continue
        if isinstance(ev, SpotQuote):
            if ev.asset != "BTC":
                continue
            spot.on_quote(ev)
            if ev.venue == "coinbase":
                an.tick(ev.rx_ns, (ev.bid + ev.ask) / 2)
            continue
        if isinstance(ev, SpotTrade):
            if ev.asset == "BTC":
                spot.on_trade(ev)
            continue
        raw = ev.raw
        if raw.get("type") == "cfbenchmarks_value_5hz" and raw["msg"].get("index_id") == "BRTI":
            spot.on_brti(ev.rx_ns, float(json.loads(raw["msg"]["data"])["value"]))
        an.feed(ev)
        last_rx = ev.rx_ns
    an.finish(last_rx + 120_000_000_000)

    rows = []
    for sw in an.sweeps:
        if not sw.feats or sw.klass == "unknown":
            continue
        r = {"ticker": sw.ticker, "rx_ns": sw.rx_ns, "taker_side": sw.taker_side, "klass": sw.klass,
             "qty": sw.qty / 100, "ttx_min": sw.ttx_min, "mo0": sw.mo.get(0)}
        for h in HORIZONS_S:
            r[f"mo{h}"] = sw.mo.get(h)
        for h in IDX_HORIZONS_S:
            r[f"dspot{h}"] = sw.didx.get(h)
        r.update(sw.feats)
        rows.append(r)
    cols = sorted({k for r in rows for k in r})
    return pl.DataFrame({c: [r.get(c) for r in rows] for c in cols}, strict=False)


# ---------------------------------------------------------------- analysis ---

def wmean(df: pl.DataFrame, col: str) -> float | None:
    d = df.filter(pl.col(col).is_not_null())
    if d.height == 0:
        return None
    return float((d[col] * d["qty"]).sum() / d["qty"].sum())


def fmt(x):
    return "  n/a " if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:+6.2f}"


def bucket_table(df: pl.DataFrame, col: str, edges: list[float], labels: list[str], title: str) -> list[str]:
    L = [f"**{title}** (`{col}`)", "", "| bucket | vol share | full+multi share | mo 1s | mo 10s | mo 30s | full+multi mo 1s | full+multi mo 30s | Δspot 5s |", "|---|---|---|---|---|---|---|---|---|"]
    tot = df["qty"].sum()
    d = df.filter(pl.col(col).is_not_null())
    for lo, hi, name in zip(edges[:-1], edges[1:], labels):
        b = d.filter((pl.col(col) >= lo) & (pl.col(col) < hi))
        if b.height == 0:
            continue
        fm = b.filter(pl.col("klass").is_in(["full", "multi"]))
        L.append(f"| {name} | {b['qty'].sum()/tot*100:.0f}% | {fm['qty'].sum()/max(1e-9,b['qty'].sum())*100:.0f}% | {fmt(wmean(b,'mo1'))} | {fmt(wmean(b,'mo10'))} | {fmt(wmean(b,'mo30'))} | {fmt(wmean(fm,'mo1'))} | {fmt(wmean(fm,'mo30'))} | {fmt(wmean(b,'dspot5'))} |")
    L.append("")
    return L


def analyze(df: pl.DataFrame, day: date) -> str:
    L = [f"# Adverse selection predictability, {day}", "",
         f"{df.height:,} sweeps with features ({df['qty'].sum():,.0f} contracts). Directional features are signed into the taker's direction: "
         "positive = agrees with the taker = adverse for the maker. Markouts (mo) in cents/contract, volume-weighted; Δspot in $.", ""]
    L.append("## 1. Spot microstructure, one feature at a time")
    L.append("")
    tri = [-1e9, -0.33, 0.33, 1e9]
    L += bucket_table(df, "cb_imb", tri, ["against", "flat", "agrees"], "Coinbase top-of-book imbalance")
    L += bucket_table(df, "cb_micro", [-1e9, -0.5, 0.5, 1e9], ["against >$0.5", "flat", "agrees >$0.5"], "Coinbase microprice - mid")
    L += bucket_table(df, "coinbase_flow_5s", tri, ["against", "flat", "agrees"], "Coinbase trade-flow imbalance, 5s")
    L += bucket_table(df, "kraken_flow_5s", tri, ["against", "flat", "agrees"], "Kraken trade-flow imbalance, 5s")
    L += bucket_table(df, "ret_5s", [-1e9, -5, -1, 1, 5, 1e9], ["< -$5", "-5..-1", "flat", "+1..+5", "> +$5"], "Coinbase mid return over prior 5s")
    L += bucket_table(df, "kr_minus_cb", [-1e9, -2, 2, 1e9], ["Kraken below", "flat", "Kraken above"], "Kraken mid minus Coinbase mid (Kraken leading?)")
    L.append("## 2. Option state (Greeks)")
    L.append("")
    L += bucket_table(df, "abs_d", [0, 0.5, 1, 2, 1e9], ["|d|<0.5 (ATM)", "0.5-1", "1-2", ">2 (far)"], "Moneyness |d| = |ln(S/K)| / (σ√τ)")
    L += bucket_table(df, "delta_x_sigma10", [0, 0.005, 0.01, 0.02, 0.05, 1e9], ["<0.5c", "0.5-1c", "1-2c", "2-5c", ">5c"], "Expected |Δprice| from a 1σ 10s spot move (delta x σ10)")
    L.append("## 3. Kalshi book state")
    L.append("")
    L += bucket_table(df, "touch_depth_hit", [0, 100, 500, 2000, 1e9], ["<100", "100-500", "500-2000", ">2000"], "Depth at the touch being hit (contracts)")
    L += bucket_table(df, "touch_imb", [-1e9, -0.33, 0.33, 1e9], ["hit side deeper", "balanced", "other side deeper"], "Touch imbalance (other - hit)/(other + hit)")
    L += bucket_table(df, "prev_full_2s", [-0.5, 0.5, 1.5], ["no", "yes"], "Previous sweep within 2s was a full sweep")
    L += bucket_table(df, "prev_same_dir_2s", [-0.5, 0.5, 1.5], ["no", "yes"], "Previous sweep within 2s was in the same direction")
    L += bucket_table(df, "qty", [0, 10, 50, 200, 1000, 1e9], ["<10", "10-50", "50-200", "200-1000", ">1000"], "Sweep size (contracts)")

    # ---- alpha fit: predict dspot5 from spot features, time-split ----
    L.append("## 4. Fitted alpha: Δspot 5s ahead from spot microstructure (ridge, first 60% train / last 40% test)")
    L.append("")
    feats = [c for c in ("cb_imb", "cb_micro", "coinbase_flow_1s", "coinbase_flow_5s", "kraken_flow_1s", "kraken_flow_5s",
                         "gemini_btc_flow_5s", "bitstamp_flow_5s", "ret_1s", "ret_5s", "ret_30s", "kr_minus_cb") if c in df.columns]
    d = df.filter(pl.all_horizontal([pl.col(c).is_not_null() for c in feats + ["dspot5", "mo1", "mo30"]])).sort("rx_ns")
    if d.height > 1000:
        X = d.select(feats).to_numpy().astype(float)
        y = d["dspot5"].to_numpy().astype(float)
        n = d.height
        cut = int(n * 0.6)
        mu, sd = X[:cut].mean(0), X[:cut].std(0) + 1e-12
        Xs = (X - mu) / sd
        Xs = np.hstack([Xs, np.ones((n, 1))])
        lam = 10.0
        A = Xs[:cut].T @ Xs[:cut] + lam * np.eye(Xs.shape[1])
        w = np.linalg.solve(A, Xs[:cut].T @ y[:cut])
        pred = Xs @ w
        r_in = np.corrcoef(pred[:cut], y[:cut])[0, 1]
        r_out = np.corrcoef(pred[cut:], y[cut:])[0, 1]
        L.append(f"- n train {cut:,}, test {n-cut:,}; correlation(pred, Δspot5s): in-sample {r_in:.3f}, **out-of-sample {r_out:.3f}**")
        L.append("- coefficients (per 1 sd of feature, $ of Δspot5s): " + ", ".join(f"{f} {w[i]:+.2f}" for i, f in enumerate(feats)))
        L.append("")
        test = d[cut:].with_columns(pl.Series("alpha", pred[cut:]))
        L += bucket_table(test, "alpha", [-1e9, -2, -0.5, 0.5, 2, 1e9], ["α < -$2 (against taker)", "-2..-0.5", "flat", "+0.5..+2", "α > +$2 (with taker)"], "Out-of-sample markouts by predicted alpha")
        # what a maker who refuses to rest when alpha > threshold would keep
        for thr in (0.5, 1.0, 2.0):
            keep = test.filter(pl.col("alpha") < thr)
            fmk = keep.filter(pl.col("klass").is_in(["full", "multi"]))
            L.append(f"- refuse to rest when α ≥ +${thr:g}: keeps {keep['qty'].sum()/test['qty'].sum()*100:.0f}% of volume; "
                     f"all mo 1s/30s {fmt(wmean(keep,'mo1')).strip()}/{fmt(wmean(keep,'mo30')).strip()}c; "
                     f"full+multi mo 1s/30s {fmt(wmean(fmk,'mo1')).strip()}/{fmt(wmean(fmk,'mo30')).strip()}c")
        base_fm = d[cut:].filter(pl.col("klass").is_in(["full", "multi"]))
        L.append(f"- baseline (test period, no filter): all mo 1s/30s {fmt(wmean(d[cut:],'mo1')).strip()}/{fmt(wmean(d[cut:],'mo30')).strip()}c; "
                 f"full+multi {fmt(wmean(base_fm,'mo1')).strip()}/{fmt(wmean(base_fm,'mo30')).strip()}c")
    else:
        L.append("_not enough rows with all features_")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, default=Path("../data"))
    ap.add_argument("--series", default="KXBTC15M")
    ap.add_argument("--out-dir", type=Path, default=Path("../research"))
    ap.add_argument("--reuse", action="store_true", help="reuse the parquet from a previous run")
    a = ap.parse_args()
    pq = a.out_dir / f"alpha_{a.day}.parquet"
    if a.reuse and pq.exists():
        df = pl.read_parquet(pq)
    else:
        df = build(a.data_dir, a.day, a.series)
        df.write_parquet(pq)
    text = analyze(df, a.day)
    (a.out_dir / f"alpha_{a.day}.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
