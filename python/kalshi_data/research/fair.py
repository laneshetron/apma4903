"""Fair value for KXBTC15M-style markets and its validation.

    uv run python -m kalshi_data.research.fair 2026-09-14

Settlement: YES iff the 60s average of BRTI before close >= strike. Fair value
is P(A_T >= K) under driftless diffusion with realized vol:
  tau >= 60s:  A_T ~ S_t, sd = S_t * sigma * sqrt(tau - 60 + 20)
  tau <  60s:  A_T = (known part of the window + S_t * tau + noise) / 60,
               noise sd = S_t * sigma * tau^1.5 / sqrt(3)
Spot S_t can be BRTI (the settlement index, smoothed) or the Coinbase mid
(raw, leads BRTI). sigma is realized from the same series over 5 minutes.

Validation on a 1s grid per market: fair vs Kalshi mid (calibration), and
whether (fair - mid) predicts the mid 10/30/60s later.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import sys
from collections import deque
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl

from ..raw import iter_records
from ..spot import SpotQuote, iter_spot
from .alpha import fetch_strikes
from .markouts import FastBook, close_time

WINDOW_S = 60.0


def norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))


class SpotSeries:
    """A spot series with realized vol and the trailing 60s integral for the settlement average."""

    def __init__(self, vol_window_s: float = 300.0):
        self.ticks: deque = deque()   # (t_s, value)
        self.vol_window = vol_window_s
        self._vol: float | None = None
        self._n = 0

    def add(self, t_s: float, v: float) -> None:
        self.ticks.append((t_s, v))
        while self.ticks and self.ticks[0][0] < t_s - max(self.vol_window, WINDOW_S) - 1:
            self.ticks.popleft()
        self._n += 1
        if self._n % 25 == 0:
            self._vol = self._realized_vol()

    def last(self) -> float | None:
        return self.ticks[-1][1] if self.ticks else None

    def _realized_vol(self) -> float | None:
        """std of log returns per sqrt(second) from ticks in the vol window, using 1s sampling."""
        if len(self.ticks) < 30:
            return None
        t_end = self.ticks[-1][0]
        pts = [(t, v) for t, v in self.ticks if t >= t_end - self.vol_window]
        if len(pts) < 30:
            return None
        # resample to 1s
        grid = []
        j = 0
        t = pts[0][0]
        while t <= t_end:
            while j + 1 < len(pts) and pts[j + 1][0] <= t:
                j += 1
            grid.append(pts[j][1])
            t += 1.0
        if len(grid) < 20:
            return None
        r = np.diff(np.log(np.array(grid)))
        return float(np.std(r))

    def vol(self) -> float | None:
        return self._vol

    def window_integral(self, t_from: float, t_to: float) -> float | None:
        """Integral of the series over [t_from, t_to] (piecewise constant), or None if not covered."""
        if not self.ticks or self.ticks[0][0] > t_from:
            return None
        total = 0.0
        prev_t, prev_v = None, None
        for t, v in self.ticks:
            if prev_t is not None and t > t_from:
                a, b = max(prev_t, t_from), min(t, t_to)
                if b > a:
                    total += prev_v * (b - a)
            prev_t, prev_v = t, v
            if t >= t_to:
                break
        if prev_t is not None and prev_t < t_to:
            total += prev_v * (t_to - max(prev_t, t_from))
        return total


def fair_value(spot: SpotSeries, K: float, t_s: float, close_s: float, sigma: float | None = None) -> float | None:
    S = spot.last()
    sigma = sigma if sigma is not None else spot.vol()
    if S is None or sigma is None or K <= 0:
        return None
    tau = close_s - t_s
    if tau <= 0:
        return None
    if tau >= WINDOW_S:
        sd = S * sigma * math.sqrt(tau - WINDOW_S + WINDOW_S / 3)
        return norm_cdf((S - K) / sd) if sd > 0 else (1.0 if S >= K else 0.0)
    known = spot.window_integral(close_s - WINDOW_S, t_s)
    if known is None:
        known = S * (WINDOW_S - tau)
    mean = (known + S * tau) / WINDOW_S
    sd = S * sigma * tau ** 1.5 / math.sqrt(3) / WINDOW_S
    return norm_cdf((mean - K) / sd) if sd > 0 else (1.0 if mean >= K else 0.0)


# ------------------------------------------------------------- validation ---

def build(data_dir: Path, day: date, series: str) -> pl.DataFrame:
    tickers = sorted({r.raw["msg"]["market_ticker"] for r in iter_records(data_dir, day)
                      if r.raw.get("type") == "orderbook_snapshot" and r.raw["msg"]["market_ticker"].startswith(series + "-")})
    strikes = fetch_strikes(tickers)
    results = {}
    import urllib.request
    for t in tickers:
        try:
            with urllib.request.urlopen(f"https://api.elections.kalshi.com/trade-api/v2/markets/{t}", timeout=20) as r:
                m = json.load(r)["market"]
            if m.get("result") in ("yes", "no"):
                results[t] = 1.0 if m["result"] == "yes" else 0.0
        except Exception:  # noqa: BLE001
            pass
    print(f"{len(strikes)} strikes, {len(results)} settled results", file=sys.stderr)

    brti, cb = SpotSeries(), SpotSeries()
    books: dict[str, FastBook] = {}
    closes: dict[str, float] = {}
    next_sample: dict[str, float] = {}
    rows = []

    def quotes():
        for q in iter_spot(data_dir, "coinbase", day):
            if isinstance(q, SpotQuote) and q.asset == "BTC":
                yield q

    for ev in heapq.merge(iter_records(data_dir, day), quotes(), key=lambda e: e.rx_ns):
        t_s = ev.rx_ns / 1e9
        if isinstance(ev, SpotQuote):
            cb.add(t_s, (ev.bid + ev.ask) / 2)
            continue
        raw = ev.raw
        typ = raw.get("type")
        if typ == "cfbenchmarks_value_5hz" and raw["msg"].get("index_id") == "BRTI":
            brti.add(t_s, float(json.loads(raw["msg"]["data"])["value"]))
            continue
        if typ == "_local":
            if raw.get("event") in ("connect", "disconnect"):
                for b in books.values():
                    b.stale = True
            continue
        if typ not in ("orderbook_snapshot", "orderbook_delta"):
            continue
        msg = raw["msg"]
        tk = msg["market_ticker"]
        if not tk.startswith(series + "-") or tk not in strikes:
            continue
        b = books.get(tk)
        if b is None:
            b = books[tk] = FastBook()
            closes[tk] = close_time(tk) or 0
            next_sample[tk] = t_s
        if typ == "orderbook_snapshot":
            b.snapshot(msg)
        else:
            if b.stale:
                continue
            try:
                b.delta(msg["side"], int(round(float(msg["price_dollars"]) * 10000)), int(round(float(msg["delta_fp"]) * 100)))
            except ValueError:
                b.stale = True
                continue
        if t_s >= next_sample[tk]:
            next_sample[tk] = t_s + 1.0
            mid = b.mid()
            if mid is None:
                continue
            K = strikes[tk]
            rows.append({
                "ticker": tk, "t_s": t_s, "tau_s": closes[tk] - t_s, "mid": mid / 100,
                "fair_brti": fair_value(brti, K, t_s, closes[tk]),
                "fair_cb": fair_value(cb, K, t_s, closes[tk]),
                "fair_cb_brtivol": fair_value(cb, K, t_s, closes[tk], sigma=brti.vol()),
                "vol_brti_bp": (brti.vol() or float("nan")) * 1e4, "vol_cb_bp": (cb.vol() or float("nan")) * 1e4,
                "result": results.get(tk),
            })
    cols = sorted({k for r in rows for k in r})
    df = pl.DataFrame({c: [r.get(c) for r in rows] for c in cols}, strict=False)
    # future mids
    df = df.sort(["ticker", "t_s"])
    for h in (10, 30, 60):
        df = df.with_columns(pl.col("mid").shift(-h).over("ticker").alias(f"mid_{h}s"))
    return df


def analyze(df: pl.DataFrame) -> str:
    L = [f"# Fair value validation ({df.height:,} market-seconds, {df['ticker'].n_unique()} markets)", ""]
    L.append(f"Realized vol (bp per sqrt-second): BRTI median {df['vol_brti_bp'].median():.2f}, Coinbase median {df['vol_cb_bp'].median():.2f}")
    L.append("")
    for col in ("fair_brti", "fair_cb", "fair_cb_brtivol"):
        d = df.filter(pl.col(col).is_not_null() & (pl.col("tau_s") > 30))
        x, y = d[col].to_numpy(), d["mid"].to_numpy()
        A = np.vstack([x, np.ones_like(x)]).T
        slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
        resid = y - x
        L.append(f"## {col}")
        L.append("")
        L.append(f"- vs Kalshi mid: corr {np.corrcoef(x, y)[0,1]:.3f}, mid = {slope:.3f} x fair + {intercept:.3f}; "
                 f"mean(mid - fair) {resid.mean()*100:+.2f}c, mean |mid - fair| {np.abs(resid).mean()*100:.2f}c")
        # calibration vs settlement, by fair bucket (tau > 60s so it is a forecast)
        s = d.filter(pl.col("result").is_not_null() & (pl.col("tau_s") > 60))
        if s.height:
            L.append("- calibration vs settlement (tau > 60s): " + ", ".join(
                f"fair {lo:.1f}-{hi:.1f}: {s.filter((pl.col(col) >= lo) & (pl.col(col) < hi))['result'].mean():.2f} ({s.filter((pl.col(col) >= lo) & (pl.col(col) < hi)).height:,})"
                for lo, hi in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01))))
            m = s.filter((pl.col("mid") >= 0) )
            L.append("- Kalshi mid calibration, same rows: " + ", ".join(
                f"mid {lo:.1f}-{hi:.1f}: {m.filter((pl.col('mid') >= lo) & (pl.col('mid') < hi))['result'].mean():.2f}"
                for lo, hi in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01))))
        # predictiveness: regress future mid change on (fair - mid)
        L.append("- does (fair - mid) predict the mid? regression of mid(t+h) - mid(t) on (fair - mid):")
        for h in (10, 30, 60):
            p = d.filter(pl.col(f"mid_{h}s").is_not_null())
            gap = (p[col] - p["mid"]).to_numpy()
            dm = (p[f"mid_{h}s"] - p["mid"]).to_numpy()
            beta = float(np.dot(gap, dm) / np.dot(gap, gap)) if np.dot(gap, gap) > 0 else float("nan")
            r = np.corrcoef(gap, dm)[0, 1]
            L.append(f"    h={h}s: beta {beta:.3f} (1.0 = full convergence), corr {r:.3f}")
        # by gap bucket
        p = d.filter(pl.col("mid_30s").is_not_null()).with_columns(((pl.col(col) - pl.col("mid")) * 100).alias("gap_c"), ((pl.col("mid_30s") - pl.col("mid")) * 100).alias("dm30_c"))
        L.append("    mean 30s mid change (c) by fair - mid bucket: " + ", ".join(
            f"{name}: {p.filter((pl.col('gap_c') >= lo) & (pl.col('gap_c') < hi))['dm30_c'].mean():+.2f}"
            for lo, hi, name in ((-1e9, -3, "<-3c"), (-3, -1, "-3..-1"), (-1, 1, "flat"), (1, 3, "+1..+3"), (3, 1e9, ">+3c"))))
        L.append("")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, default=Path("../data"))
    ap.add_argument("--series", default="KXBTC15M")
    ap.add_argument("--out-dir", type=Path, default=Path("../research"))
    a = ap.parse_args()
    df = build(a.data_dir, a.day, a.series)
    df.write_parquet(a.out_dir / f"fair_{a.day}.parquet")
    text = analyze(df)
    (a.out_dir / f"fair_{a.day}.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
