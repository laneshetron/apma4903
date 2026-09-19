"""Does the book price the partially-known settlement average in the final minute?

KXBTC15M / KXETH15M settle YES iff the mean of the index over the 60 s before close is
> strike. At t seconds before close, k = 60 - t of those seconds are already known (the
5 Hz index feed); the remaining t seconds are a random walk from the current index. So

    P(YES | t) = Phi( (partial_sum + t * S_now - 60 * K) / (sigma * sqrt(sum_{j=1..t} j^2)) )

with S_now the latest index, sigma the per-second vol (realized over the last 5 min).
The sum of the remaining path is a sum of partial sums of increments, whose variance is
sigma^2 * sum j^2. This is also the value at t > 60 with k = 0.

For every second from T-180 to T-1 we record P(YES), the book's best bid/ask, and the
realized settlement, and ask: buying YES at the ask when P - ask > threshold (or NO when
bid - P > threshold), net of the taker fee 0.07 p (1-p), what does it earn at settlement?

    uv run python -m kalshi_data.research.settle_window 2026-09-17 --data-dir ../data_aws [--series KXBTC15M]
"""

from __future__ import annotations

import argparse
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
from .alpha import fetch_strikes
from .markouts import FastBook, close_time

ONE = 10_000
FEE = 0.07


def phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--data-dir", type=Path, default=Path("../data_aws"))
    ap.add_argument("--series", default="KXBTC15M")
    ap.add_argument("--from-s", type=int, default=180, help="start recording this many seconds before close")
    a = ap.parse_args()
    index_id = "ETHUSD_RTI" if "ETH" in a.series else "BRTI"

    tickers = set()
    for rec in iter_records(a.data_dir, a.day):
        raw = rec.raw
        if raw.get("type") == "orderbook_snapshot" and raw["msg"]["market_ticker"].startswith(a.series + "-"):
            tickers.add(raw["msg"]["market_ticker"])
    strikes = fetch_strikes(sorted(tickers))
    closes = {t: int(close_time(t) * 1e9) for t in tickers if close_time(t)}
    books = {t: FastBook() for t in closes}
    idx: deque = deque()          # (rx_ns, ts_ms, value) 5 Hz index, last ~6 min
    avg60: dict[int, float] = {}  # window_end_ms -> official 60 s average
    rows = []
    last_sec: dict[str, int] = {}

    def vol_per_s() -> float | None:
        if len(idx) < 300:
            return None
        v = np.array([x[2] for x in idx])
        r = np.diff(np.log(v))
        return float(np.std(r) * math.sqrt(5))

    for rec in iter_records(a.data_dir, a.day):
        raw = rec.raw
        t = raw.get("type")
        rx = rec.rx_ns
        if t == "cfbenchmarks_value_5hz" and raw["msg"].get("index_id") == index_id:
            d = json.loads(raw["msg"]["data"])
            idx.append((rx, int(d["time"]), float(d["value"])))
            while idx and rx - idx[0][0] > 360_000_000_000:
                idx.popleft()
            continue
        if t == "cfbenchmarks_value" and raw["msg"].get("index_id") == index_id:
            av = raw["msg"].get("avg_60s_data")
            if av:
                avg60[int(av["window_end_ts_exclusive"])] = float(av["value"])
            continue
        if t not in ("orderbook_snapshot", "orderbook_delta"):
            continue
        tk = raw["msg"]["market_ticker"]
        b = books.get(tk)
        if b is None:
            continue
        if t == "orderbook_snapshot":
            b.snapshot(raw["msg"])
        else:
            msg = raw["msg"]
            try:
                b.delta(msg["side"], parse_price(msg["price_dollars"]), parse_qty(msg["delta_fp"]))
            except ValueError:
                continue
        close_ns = closes[tk]
        tts = (close_ns - rx) / 1e9
        if not (0 < tts <= a.from_s) or b.best_yes < 0 or b.best_no < 0 or tk not in strikes:
            continue
        sec = int(tts)
        if last_sec.get(tk) == sec:
            continue
        last_sec[tk] = sec
        if not idx:
            continue
        s_now = idx[-1][2]
        sig = vol_per_s()
        if sig is None:
            continue
        # known part of the settlement window: index samples with exchange time in [close-60s, now]
        win_start_ms = close_ns // 1_000_000 - 60_000
        known = [v for _, ts, v in idx if ts >= win_start_ms]
        k = min(60, len(known) / 5.0)           # seconds known (5 Hz)
        partial = float(np.mean(known)) * k if known else 0.0
        t_rem = max(0.0, 60 - k)
        n = int(round(t_rem))
        var = (sig * s_now) ** 2 * sum(j * j for j in range(1, n + 1))
        mean_total = partial + t_rem * s_now
        K = strikes[tk]
        z = (mean_total - 60 * K) / math.sqrt(var) if var > 0 else (math.inf if mean_total > 60 * K else -math.inf)
        p_yes = phi(z)
        rows.append({"ticker": tk, "tts": sec, "p_yes": p_yes, "yes_bid": b.best_yes / ONE, "yes_ask": (ONE - b.best_no) / ONE,
                     "bid_depth": b.side("yes").get(b.best_yes, 0) / 100, "ask_depth": b.side("no").get(b.best_no, 0) / 100,
                     "known_s": k, "s_now": s_now, "strike": K, "sig": sig, "close_ms": close_ns // 1_000_000})
    df = pl.DataFrame(rows)
    # settlement per ticker from the official average at close
    sett = {}
    for tk, cns in closes.items():
        av = avg60.get(cns // 1_000_000)
        if av is not None and tk in strikes:
            sett[tk] = 1.0 if av > strikes[tk] else 0.0
    df = df.with_columns(pl.col("ticker").replace_strict(sett, default=None).alias("settle")).drop_nulls("settle")
    print(f"# Settlement-window study, {a.series} {a.day}: {df['ticker'].n_unique()} markets settled, {df.height:,} (market, second) rows\n")
    # calibration of the model
    df = df.with_columns(pl.col("p_yes").round(1).alias("pbin"))
    cal = df.filter(pl.col("tts") <= 60).group_by("pbin").agg(pl.col("settle").mean().alias("realized"), pl.len().alias("n")).sort("pbin")
    print("Model calibration in the last 60 s (P(YES) bin -> realized):\n")
    print("| p bin | n | realized |\n|---|---|---|")
    for r in cal.iter_rows():
        print(f"| {r[0]:.1f} | {r[2]:,} | {r[1]:.2f} |")
    # trade rule: buy YES at ask if p - ask > thr; buy NO at (1 - bid) if (1-p) - (1-bid) > thr. one contract per (market, second); settle value minus price minus fee
    print("\nTaking rule, one contract per (market, second) where the edge exceeds the threshold (¢ per contract, after taker fee):\n")
    print("| window | threshold | trades | markets | edge/ct ¢ | P&L $ | win % |\n|---|---|---|---|---|---|---|")
    for lo, hi in ((1, 15), (15, 30), (30, 60), (60, 120), (120, 180)):
        w = df.filter((pl.col("tts") >= lo) & (pl.col("tts") < hi))
        for thr in (0.02, 0.05, 0.10, 0.20):
            pnl = []; mk = set()
            for r in w.iter_rows(named=True):
                p, bid, ask, st = r["p_yes"], r["yes_bid"], r["yes_ask"], r["settle"]
                if p - ask > thr and ask < 1:
                    pnl.append(st - ask - FEE * ask * (1 - ask)); mk.add(r["ticker"])
                elif (1 - p) - (1 - bid) > thr and bid > 0:
                    pnl.append((1 - st) - (1 - bid) - FEE * bid * (1 - bid)); mk.add(r["ticker"])
            if pnl:
                arr = np.array(pnl)
                print(f"| T-{hi}..T-{lo} s | {thr:.2f} | {len(arr):,} | {len(mk)} | {arr.mean()*100:+.2f} | {arr.sum():+.1f} | {(arr > 0).mean()*100:.0f}% |")
    # --- honest version: one trade per (market, window) at the first second the edge clears the threshold,
    #     sized by the contracts at the touch (capped), scored per market; model vs book-mid Brier per window
    print("\nModel vs book mid as predictors (Brier, lower is better), and one trade per market per window at the first signal, size = min(touch depth, 50):\n")
    print("| window | rows | Brier model | Brier book mid | thr | markets traded | contracts | P&L $ | $/mkt | t (markets) | win % |\n|---|---|---|---|---|---|---|---|---|---|---|")
    for lo, hi in ((1, 15), (15, 30), (30, 60), (60, 120), (120, 180)):
        w = df.filter((pl.col("tts") >= lo) & (pl.col("tts") < hi)).sort(["ticker", "tts"], descending=[False, True])
        if w.height == 0:
            continue
        mid = ((w["yes_bid"] + w["yes_ask"]) / 2).to_numpy()
        st_ = w["settle"].to_numpy()
        b_model = float(np.mean((w["p_yes"].to_numpy() - st_) ** 2))
        b_book = float(np.mean((mid - st_) ** 2))
        for thr in (0.05, 0.10):
            per_mkt = {}
            for r in w.iter_rows(named=True):
                if r["ticker"] in per_mkt:
                    continue
                p, bid, ask, st = r["p_yes"], r["yes_bid"], r["yes_ask"], r["settle"]
                if p - ask > thr and ask < 1:
                    q = min(r["ask_depth"], 50)
                    per_mkt[r["ticker"]] = q * (st - ask - FEE * ask * (1 - ask))
                elif (1 - p) - (1 - bid) > thr and bid > 0:
                    q = min(r["bid_depth"], 50)
                    per_mkt[r["ticker"]] = q * ((1 - st) - (1 - bid) - FEE * bid * (1 - bid))
            if per_mkt:
                v = np.array(list(per_mkt.values()))
                tstat = v.mean() / (v.std(ddof=1) / math.sqrt(len(v))) if len(v) > 2 and v.std(ddof=1) > 0 else float("nan")
                print(f"| T-{hi}..T-{lo} s | {w.height:,} | {b_model:.3f} | {b_book:.3f} | {thr:.2f} | {len(v)} | — | {v.sum():+.1f} | {v.mean():+.2f} | {tstat:+.1f} | {(v > 0).mean()*100:.0f}% |")
    df.write_parquet(Path("../research") / f"settle_window_{a.series}_{a.day}.parquet")


if __name__ == "__main__":
    main()
