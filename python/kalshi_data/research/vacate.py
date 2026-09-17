"""Is the next touch move predictable from microstructure, early enough to be first at the new level?

Target, per side s of the active KXBTC15M market sampled every --step ms: does the
OPPOSITE touch vacate (the ask seen from s moves away by >= 1 tick) within H ms,
for H in 50 / 100 / 250 / 500 / 1000; and, given a vacate, does a new bid form at
the vacated price within 2 s (the level we could be first at).

Features at the sample instant, signed so that positive favours the vacate
(spot up for s = yes, down for s = no):
  Kalshi   sizes of the top two levels on both sides, spread (ticks), age of each
           touch, contracts removed from / traded at the opposite touch over the last
           100 / 500 ms, taker volume both ways over 1 s, price level, minutes to close
  spot     Coinbase mid change over 50 / 100 / 250 / 500 / 1000 / 5000 ms, top-of-book
           imbalance and microprice, signed trade flow (1 s, 5 s) on every recorded
           venue, Kraken / Gemini / Bitstamp mid minus Coinbase, BRTI minus Coinbase
  contract moneyness (spot - strike) / (sigma sqrt(ttx)), realized vol

Two passes: build rows to research/vacate_<day>.parquet (--build), then fit
walk-forward with scikit-learn (--fit TRAIN_DAY TEST_DAY) and report base rate,
AUC, precision / recall by threshold and lead time at each horizon.

    uv run python -m kalshi_data.research.vacate --build 2026-09-16 --data-dir ../data_aws
    uv run python -m kalshi_data.research.vacate --fit 2026-09-16 2026-09-17
"""

from __future__ import annotations

import argparse
import bisect
import heapq
import json
import math
import sys
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl

from ..book import parse_price, parse_qty
from ..raw import iter_records
from ..spot import SpotQuote, SpotTrade, iter_spot
from .alpha import fetch_strikes
from .markouts import FastBook, close_time
from .sim import tick_at

ONE = 10_000
QTY = 100
HORIZONS_MS = (50, 100, 250, 500, 1000)
SPOT_VENUES = ("coinbase", "coinbase_perp", "kraken", "kraken_futures", "okx", "bybit", "hyperliquid", "gemini_btc", "bitstamp")
RET_MS = (50, 100, 250, 500, 1000, 5000)


class Window:
    """Sum of values over trailing windows."""

    def __init__(self, max_ms: int):
        self.q: deque = deque()
        self.max_ns = max_ms * 1_000_000

    def add(self, rx: int, v: float) -> None:
        self.q.append((rx, v))
        self.trim(rx)

    def trim(self, rx: int) -> None:
        lo = rx - self.max_ns
        while self.q and self.q[0][0] < lo:
            self.q.popleft()

    def sum(self, rx: int, ms: int) -> float:
        lo = rx - ms * 1_000_000
        s = 0.0
        for r, v in reversed(self.q):
            if r < lo:
                break
            s += v
        return s


class Spot:
    def __init__(self):
        self.cb_bid = self.cb_ask = None
        self.cb_bs = self.cb_as = None
        self.mids: deque = deque()          # (rx, mid) last 6 s
        self.other_mid: dict[str, float] = {}
        self.flow = {v: (Window(5000), Window(5000)) for v in SPOT_VENUES}   # signed, total
        self.brti = None
        self.brti_hist: deque = deque()

    def on_quote(self, q: SpotQuote) -> None:
        if q.venue == "coinbase":
            self.cb_bid, self.cb_ask = q.bid, q.ask
            self.mids.append((q.rx_ns, (q.bid + q.ask) / 2))
            lo = q.rx_ns - 6_000_000_000
            while self.mids and self.mids[0][0] < lo:
                self.mids.popleft()
        else:
            self.other_mid[q.venue] = (q.bid + q.ask) / 2

    def on_trade(self, t: SpotTrade) -> None:
        w = self.flow.get(t.venue)
        if w is None:
            return
        w[0].add(t.rx_ns, t.size if t.side == "buy" else -t.size)
        w[1].add(t.rx_ns, t.size)

    def on_brti(self, rx: int, v: float) -> None:
        self.brti = v
        self.brti_hist.append((rx, v))
        lo = rx - 300_000_000_000
        while self.brti_hist and self.brti_hist[0][0] < lo:
            self.brti_hist.popleft()

    def vol(self) -> float | None:
        if len(self.brti_hist) < 60:
            return None
        vals = np.array([v for _, v in self.brti_hist])
        r = np.diff(np.log(vals))
        return float(np.std(r) * math.sqrt(5))   # per sqrt(second); BRTI is 5 Hz

    def mid_ago(self, rx: int, ms: int) -> float | None:
        lo = rx - ms * 1_000_000
        # mids are appended in time order; find the first at or after lo
        i = bisect.bisect_left(self.mids, (lo, -1.0))
        if i < len(self.mids):
            return self.mids[i][1]
        return None

    def features(self, rx: int, sign: int) -> dict | None:
        if self.cb_bid is None:
            return None
        mid = (self.cb_bid + self.cb_ask) / 2
        f = {"cb_spread": self.cb_ask - self.cb_bid}
        if self.cb_bs and self.cb_as:
            f["cb_imb"] = sign * (self.cb_bs - self.cb_as) / (self.cb_bs + self.cb_as)
            micro = (self.cb_bid * self.cb_as + self.cb_ask * self.cb_bs) / (self.cb_bs + self.cb_as)
            f["cb_micro"] = sign * (micro - mid)
        for ms in RET_MS:
            m0 = self.mid_ago(rx, ms)
            f[f"ret_{ms}"] = sign * (mid - m0) if m0 is not None else 0.0
        for v, (sw, tw) in self.flow.items():
            for ms in (1000, 5000):
                tot = tw.sum(rx, ms)
                f[f"{v}_flow_{ms}"] = sign * sw.sum(rx, ms) / tot if tot > 0 else 0.0
        for v, m in self.other_mid.items():
            f[f"{v}_minus_cb"] = sign * (m - mid)
        if self.brti is not None:
            f["brti_minus_cb"] = sign * (self.brti - mid)
        f["_mid"] = mid
        return f


class MarketState:
    def __init__(self, ticker: str, close_ns: int, strike: float | None):
        self.ticker = ticker
        self.close_ns = close_ns
        self.strike = strike
        self.book = FastBook()
        self.best_hist = {"yes": ([], []), "no": ([], [])}    # (rx list, price list) at every best change
        self.best_since = {"yes": 0, "no": 0}
        self.removed = {"yes": Window(500), "no": Window(500)}   # contracts removed at the best by deltas (not trades)
        self.traded = {"yes": Window(1000), "no": Window(1000)}  # taker volume hitting this side
        self.last_trade_ts = None
        self.pending_neg: dict[tuple, list] = defaultdict(list)


def build(data_dir: Path, day: date, series: str, step_ms: int, stop_before_s: int) -> pl.DataFrame:
    tickers = set()
    for rec in iter_records(data_dir, day):
        raw = rec.raw
        if raw.get("type") == "orderbook_snapshot" and raw["msg"]["market_ticker"].startswith(series + "-"):
            tickers.add(raw["msg"]["market_ticker"])
    print(f"fetching {len(tickers)} strikes...", file=sys.stderr)
    strikes = fetch_strikes(sorted(tickers))
    closes = {t: int(close_time(t) * 1e9) for t in tickers if close_time(t)}
    markets: dict[str, MarketState] = {t: MarketState(t, closes[t], strikes.get(t)) for t in closes}
    spot = Spot()

    def spot_events():
        its = [iter_spot(data_dir, v, day) for v in SPOT_VENUES if (data_dir / "spot" / v).is_dir()]
        yield from heapq.merge(*its, key=lambda e: e.rx_ns)

    def cb_sizes():
        for rec in iter_records(data_dir / "spot" / "coinbase", day):
            raw = rec.raw
            if raw.get("type") == "ticker" and raw.get("product_id") == "BTC-USD" and raw.get("best_bid_size"):
                yield ("cbsz", rec.rx_ns, float(raw["best_bid_size"]), float(raw["best_ask_size"]))

    rows: list[dict] = []
    samples: list[tuple] = []   # (ticker, side, rx, opp_best, our_best, row_index)
    next_sample = 0
    step_ns = step_ms * 1_000_000
    stop_ns = stop_before_s * 1_000_000_000
    n = 0
    stream = heapq.merge(iter_records(data_dir, day), spot_events(), cb_sizes(),
                         key=lambda e: e[1] if isinstance(e, tuple) else e.rx_ns)
    active: MarketState | None = None
    for ev in stream:
        n += 1
        if n % 5_000_000 == 0:
            print(f"  {n/1e6:.0f}M events, {len(rows):,} rows", file=sys.stderr)
        rx = ev[1] if isinstance(ev, tuple) else ev.rx_ns
        if isinstance(ev, tuple):
            spot.cb_bs, spot.cb_as = ev[2], ev[3]
        elif isinstance(ev, SpotQuote):
            if ev.asset == "BTC":
                spot.on_quote(ev)
        elif isinstance(ev, SpotTrade):
            if ev.asset == "BTC":
                spot.on_trade(ev)
        else:
            raw = ev.raw
            t = raw.get("type")
            if t == "cfbenchmarks_value_5hz" and raw["msg"].get("index_id") == "BRTI":
                spot.on_brti(rx, float(json.loads(raw["msg"]["data"])["value"]))
            elif t in ("orderbook_snapshot", "orderbook_delta", "trade"):
                m = markets.get(raw["msg"].get("market_ticker"))
                if m is None:
                    continue
                b = m.book
                if t == "orderbook_snapshot":
                    b.snapshot(raw["msg"])
                    for s in ("yes", "no"):
                        _note_best(m, s, rx)
                elif t == "orderbook_delta":
                    msg = raw["msg"]
                    side, price, d = msg["side"], parse_price(msg["price_dollars"]), parse_qty(msg["delta_fp"])
                    best_before = b.best(side)
                    try:
                        b.delta(side, price, d)
                    except ValueError:
                        continue
                    if d < 0 and price >= best_before:
                        # removal at the touch: attributed to a trade if one prints with the same ts, else a cancel
                        m.pending_neg[(side, msg["ts_ms"])].append((rx, -d))
                    for s in ("yes", "no"):
                        _note_best(m, s, rx)
                else:
                    msg = raw["msg"]
                    q = parse_qty(msg["count_fp"])
                    hit = "no" if msg["taker_side"] == "yes" else "yes"   # taker buying YES hits NO bids
                    m.traded[hit].add(rx, q / QTY)
                    # the trade explains removals at that side with the same engine ts
                    m.pending_neg.pop((hit, msg["ts_ms"]), None)
                # flush removals older than 300 ms as cancels
                for k in list(m.pending_neg):
                    lst = m.pending_neg[k]
                    if lst and rx - lst[0][0] > 300_000_000:
                        for r0, q0 in lst:
                            m.removed[k[0]].add(r0, q0 / QTY)
                        del m.pending_neg[k]
        # sampling
        if rx < next_sample:
            continue
        next_sample = rx + step_ns
        # the market the quoter would be in: nearest close still outside the stop window
        cand = [m for m in markets.values() if m.close_ns - stop_ns > rx and m.book.best_yes >= 0 and m.book.best_no >= 0 and rx > m.close_ns - 15 * 60_000_000_000]
        if not cand:
            continue
        m = min(cand, key=lambda x: x.close_ns)
        b = m.book
        ttx_min = (m.close_ns - rx) / 6e10
        vol = spot.vol()
        for s, sign in (("yes", 1), ("no", -1)):
            sf = spot.features(rx, sign)
            if sf is None:
                continue
            opp = "no" if s == "yes" else "yes"
            our_best, opp_best = b.best(s), b.best(opp)
            tick = tick_at(our_best)
            r = {"ticker": m.ticker, "side": s, "rx": rx, "our_best": our_best, "opp_best": opp_best,
                 "spread_ticks": (ONE - opp_best - our_best) / tick,
                 "our_size": b.side(s).get(our_best, 0) / QTY, "opp_size": b.side(opp).get(opp_best, 0) / QTY,
                 "our_size2": _second(b, s, our_best) / QTY, "opp_size2": _second(b, opp, opp_best) / QTY,
                 "opp_age_ms": (rx - m.best_since[opp]) / 1e6, "our_age_ms": (rx - m.best_since[s]) / 1e6,
                 "opp_removed_100": m.removed[opp].sum(rx, 100), "opp_removed_500": m.removed[opp].sum(rx, 500),
                 "opp_traded_100": m.traded[opp].sum(rx, 100), "opp_traded_500": m.traded[opp].sum(rx, 500), "opp_traded_1000": m.traded[opp].sum(rx, 1000),
                 "our_traded_1000": m.traded[s].sum(rx, 1000),
                 "price_c": (our_best if s == "yes" else ONE - our_best) / 100, "ttx_min": ttx_min}
            r["opp_removed_100"] /= max(r["opp_size"] + r["opp_removed_100"], 1)
            r["opp_removed_500"] /= max(r["opp_size"] + r["opp_removed_500"], 1)
            mid = sf.pop("_mid")
            if m.strike and vol and ttx_min > 0:
                r["moneyness"] = sign * (mid - m.strike) / (mid * vol * math.sqrt(ttx_min * 60))
                r["vol"] = vol
            r.update(sf)
            samples.append((m.ticker, s, rx, opp_best, len(rows)))
            rows.append(r)

    # labels from the best-price histories
    print(f"labelling {len(rows):,} rows...", file=sys.stderr)
    for h in HORIZONS_MS:
        for r in rows:
            r[f"vacate_{h}"] = 0
    for r in rows:
        r["lead_ms"] = float("nan")
        r["formed_2s"] = 0
    for tk, s, rx, opp_best, i in samples:
        m = markets[tk]
        opp = "no" if s == "yes" else "yes"
        rxs, prices = m.best_hist[opp]
        j = bisect.bisect_right(rxs, rx)
        # first best change after rx where the opposite best moved away (its bid price fell)
        while j < len(rxs) and prices[j] >= opp_best:
            j += 1
        if j < len(rxs):
            lead = (rxs[j] - rx) / 1e6
            rows[i]["lead_ms"] = lead
            for h in HORIZONS_MS:
                if lead <= h:
                    rows[i][f"vacate_{h}"] = 1
            # a new bid on OUR side at the vacated price (ONE - opp_best) within 2 s of the vacate
            vac_price = ONE - opp_best
            orxs, oprices = m.best_hist[s]
            k = bisect.bisect_right(orxs, rxs[j])
            while k < len(orxs) and orxs[k] - rxs[j] <= 2_000_000_000:
                if oprices[k] >= vac_price:
                    rows[i]["formed_2s"] = 1
                    break
                k += 1
    cols = sorted({k for r in rows for k in r})
    return pl.DataFrame({c: [r.get(c) for r in rows] for c in cols}, strict=False)


def _second(b: FastBook, s: str, best: int) -> int:
    lv = b.side(s)
    cands = [p for p in lv if p < best]
    return lv[max(cands)] if cands else 0


def _note_best(m: MarketState, s: str, rx: int) -> None:
    bp = m.book.best(s)
    rxs, prices = m.best_hist[s]
    if not prices or prices[-1] != bp:
        rxs.append(rx)
        prices.append(bp)
        m.best_since[s] = rx


# ------------------------------------------------------------------ fit ---

def fit(train: pl.DataFrame, test: pl.DataFrame) -> str:
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score

    skip = {"ticker", "side", "rx", "our_best", "opp_best", "lead_ms", "formed_2s"} | {f"vacate_{h}" for h in HORIZONS_MS}
    feats = [c for c in train.columns if c not in skip]
    Xtr = train.select(feats).to_numpy().astype(np.float32)
    Xte = test.select(feats).to_numpy().astype(np.float32)
    L = [f"# Touch-vacate prediction: train {train.height:,} rows, test {test.height:,} rows, {len(feats)} features\n"]
    L.append("| horizon | base rate train / test | AUC | prec@1% | prec@5% | prec@10% | recall@10% | lead p50 among hits (ms) | formed within 2 s given vacate |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    importances = {}
    for h in HORIZONS_MS:
        ytr = train[f"vacate_{h}"].to_numpy()
        yte = test[f"vacate_{h}"].to_numpy()
        clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=200, l2_regularization=1.0)
        clf.fit(Xtr, ytr)
        p = clf.predict_proba(Xte)[:, 1]
        auc = roc_auc_score(yte, p)
        order = np.argsort(-p)
        def prec(frac):
            k = max(1, int(frac * len(p)))
            return yte[order[:k]].mean()
        k10 = max(1, int(0.10 * len(p)))
        recall10 = yte[order[:k10]].sum() / max(1, yte.sum())
        hits = order[:k10][yte[order[:k10]] == 1]
        lead = np.nanmedian(test["lead_ms"].to_numpy()[hits]) if len(hits) else float("nan")
        formed = test["formed_2s"].to_numpy()[hits].mean() if len(hits) else float("nan")
        L.append(f"| {h} ms | {ytr.mean()*100:.1f}% / {yte.mean()*100:.1f}% | {auc:.3f} | {prec(0.01)*100:.0f}% | {prec(0.05)*100:.0f}% | {prec(0.10)*100:.0f}% | {recall10*100:.0f}% | {lead:.0f} | {formed*100:.0f}% |")
        if h == 250:
            # permutation-free importance proxy: single-feature AUCs on the test set
            for j, f in enumerate(feats):
                x = Xte[:, j]
                if np.nanstd(x) == 0:
                    continue
                a = roc_auc_score(yte, np.nan_to_num(x))
                importances[f] = max(a, 1 - a)
    L.append("\nSingle-feature AUC for the 250 ms horizon (test set), top 15:\n")
    L.append("| feature | AUC |\n|---|---|")
    for f, a in sorted(importances.items(), key=lambda kv: -kv[1])[:15]:
        L.append(f"| {f} | {a:.3f} |")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", type=date.fromisoformat)
    ap.add_argument("--fit", nargs=2, type=date.fromisoformat, metavar=("TRAIN", "TEST"))
    ap.add_argument("--data-dir", type=Path, default=Path("../data_aws"))
    ap.add_argument("--series", default="KXBTC15M")
    ap.add_argument("--step", type=int, default=100, help="sample cadence, ms")
    ap.add_argument("--stop-before", type=int, default=300)
    a = ap.parse_args()
    if a.build:
        df = build(a.data_dir, a.build, a.series, a.step, a.stop_before)
        out = Path("../research") / f"vacate_{a.build}.parquet"
        df.write_parquet(out)
        print(f"{df.height:,} rows -> {out}")
        for h in HORIZONS_MS:
            print(f"vacate within {h} ms: {df[f'vacate_{h}'].mean()*100:.1f}%")
    if a.fit:
        tr = pl.read_parquet(Path("../research") / f"vacate_{a.fit[0]}.parquet")
        te = pl.read_parquet(Path("../research") / f"vacate_{a.fit[1]}.parquet")
        text = fit(tr, te)
        print(text)
        (Path("../research") / f"vacate_{a.fit[0]}_{a.fit[1]}.md").write_text(text)


if __name__ == "__main__":
    main()
