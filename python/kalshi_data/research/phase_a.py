"""Phase A market-making viability read from Kalshi's public REST history.

    uv run python -m kalshi_data.research.phase_a --hours 24 --series KXBTC15M KXETH15M KXBTCD

For each series, over markets that settled in the last N hours:
  * candlesticks (1-min) for every market -> quoted spread, volume by
    minutes-to-expiry, time-of-day
  * full trade tape for a sample of markets -> taker imbalance, trade sizes,
    and maker MARKOUTS: P&L per contract for the passive side of each trade,
    measured at 10s / 30s / 60s after the trade and at settlement.

Markout convention (per contract, in cents of YES price): the maker took the
opposite side of the taker at the trade price p. If the taker bought YES the
maker is short YES: markout = p - ref. If the taker sold YES (bought NO) the
maker is long YES: markout = ref - p. ref is the VWAP of trades in the
[t+h, t+h+5s] window (or the settlement value). Positive = maker gained.

IMPORTANT: because ref is built from later trades (which print at bid or
ask), it sits near the mid on average, so this markout ALREADY includes the
half-spread the maker captured at the touch. A market with zero information
in its flow shows a markout of about +half-spread (~+0.4c); the shortfall
below that is the adverse-selection cost. The markout is therefore directly
the maker's gross P&L per contract for a fill at the touch that is unwound
h seconds later at the prevailing price. Phase B replaces ref with the true
order-book mid from our own recording.

Responses are cached under --cache so re-runs are free.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import statistics as st
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.elections.kalshi.com/trade-api/v2"
HORIZONS = (10, 30, 60)  # seconds


class Client:
    def __init__(self, cache: Path, min_interval: float = 0.12):
        self.cache = cache
        self.cache.mkdir(parents=True, exist_ok=True)
        self.min_interval = min_interval
        self._last = 0.0
        self.requests = 0

    def get(self, path: str, **params) -> dict:
        q = urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
        url = f"{BASE}{path}?{q}" if q else f"{BASE}{path}"
        key = self.cache / (hashlib.sha1(url.encode()).hexdigest() + ".json")
        if key.exists():
            return json.loads(key.read_text())
        for attempt in range(6):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            try:
                self._last = time.monotonic()
                self.requests += 1
                with urllib.request.urlopen(url, timeout=60) as r:
                    data = json.load(r)
                key.write_text(json.dumps(data))
                return data
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:
                    time.sleep(2**attempt)
                    continue
                raise
            except (TimeoutError, OSError, urllib.error.URLError) as e:
                print(f"  retry {attempt+1} after {type(e).__name__}: {url[:90]}", file=sys.stderr)
                time.sleep(2**attempt)
        raise RuntimeError(f"giving up on {url}")

    def settled_markets(self, series: str, min_close_ts: int) -> list[dict]:
        out, cursor = [], ""
        while True:
            d = self.get("/markets", series_ticker=series, status="settled", limit=1000, min_close_ts=min_close_ts, cursor=cursor)
            out += d["markets"]
            cursor = d.get("cursor") or ""
            if not cursor:
                return out

    def candles(self, series: str, m: dict) -> list[dict]:
        s, e = ts(m["open_time"]), ts(m["close_time"])
        return self.get(f"/series/{series}/markets/{m['ticker']}/candlesticks", start_ts=s, end_ts=e, period_interval=1)["candlesticks"]

    def trades(self, ticker: str, max_pages: int = 200) -> list[dict]:
        out, cursor = [], ""
        for _ in range(max_pages):
            d = self.get("/markets/trades", ticker=ticker, limit=1000, cursor=cursor)
            out += d["trades"]
            cursor = d.get("cursor") or ""
            if not cursor:
                break
        out.sort(key=lambda t: t["created_time"])
        return out


def ts(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def tsf(iso: str) -> float:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def f(x) -> float:
    return float(x) if x not in (None, "") else float("nan")


def wmean(pairs) -> float:
    pairs = [(v, w) for v, w in pairs if w > 0 and v == v]
    tot = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / tot if tot else float("nan")


# ---------------------------------------------------------------- candles ---

def candle_stats(series: str, markets: list[dict], c: Client) -> dict:
    spreads, spread_by_ttx, vol_by_ttx, vol_by_hour = [], defaultdict(list), defaultdict(float), defaultdict(float)
    total_vol, n_with_vol = 0.0, 0
    for m in markets:
        if f(m.get("volume_fp", 0)) <= 0:
            continue  # nothing to learn from an untraded strike; saves thousands of calls on KXBTCD
        cs = c.candles(series, m)
        close = ts(m["close_time"])
        mv = 0.0
        for x in cs:
            bid, ask = f(x["yes_bid"].get("close_dollars")), f(x["yes_ask"].get("close_dollars"))
            vol = f(x["volume_fp"])
            ttx = max(0, (close - x["end_period_ts"]) // 60)  # minutes to expiry at candle end
            if bid == bid and ask == ask and 0 < bid < 1 and 0 < ask < 1:
                sp = (ask - bid) * 100
                spreads.append((sp, vol))
                spread_by_ttx[ttx].append((sp, vol))
            vol_by_ttx[ttx] += vol
            vol_by_hour[datetime.fromtimestamp(x["end_period_ts"], timezone.utc).hour] += vol
            mv += vol
        total_vol += mv
        n_with_vol += mv > 0
    return {
        "markets": len(markets), "markets_with_volume": n_with_vol, "volume": total_vol,
        "spread_vw_cents": wmean(spreads),
        "spread_median_cents": st.median([s for s, _ in spreads]) if spreads else float("nan"),
        "spread_by_ttx": {k: wmean(v) for k, v in sorted(spread_by_ttx.items())},
        "vol_by_ttx": dict(sorted(vol_by_ttx.items())),
        "vol_by_hour_utc": dict(sorted(vol_by_hour.items())),
    }


# ----------------------------------------------------------------- trades ---

def markouts(trades: list[dict], settle: float | None, close_ts: int) -> dict:
    """Volume-weighted maker markouts in cents, overall and by minutes-to-expiry."""
    times = [tsf(t["created_time"]) for t in trades]
    px = [f(t["yes_price_dollars"]) for t in trades]
    qty = [f(t["count_fp"]) for t in trades]
    # prefix sums for fast window VWAP
    cpq = [0.0]
    cq = [0.0]
    for p, q in zip(px, qty):
        cpq.append(cpq[-1] + p * q)
        cq.append(cq[-1] + q)

    def vwap(a: float, b: float) -> float | None:
        i, j = bisect.bisect_left(times, a), bisect.bisect_right(times, b)
        if j <= i:
            return None
        return (cpq[j] - cpq[i]) / (cq[j] - cq[i])

    res = {h: [] for h in HORIZONS}
    res["settle"] = []
    by_ttx = defaultdict(lambda: {h: [] for h in (*HORIZONS, "settle")})
    for k, t in enumerate(trades):
        sign = 1 if t["taker_side"] == "yes" else -1  # maker short YES if taker bought YES
        ttx = max(0, int((close_ts - times[k]) // 60))
        for h in HORIZONS:
            ref = vwap(times[k] + h, times[k] + h + 5)
            if ref is None:
                continue
            mo = sign * (px[k] - ref) * 100
            res[h].append((mo, qty[k]))
            by_ttx[ttx][h].append((mo, qty[k]))
        if settle is not None:
            mo = sign * (px[k] - settle) * 100
            res["settle"].append((mo, qty[k]))
            by_ttx[ttx]["settle"].append((mo, qty[k]))
    return {
        "overall": {h: wmean(v) for h, v in res.items()},
        "coverage": {h: sum(q for _, q in v) / max(1e-9, sum(qty)) for h, v in res.items()},
        "by_ttx": {k: {h: wmean(v) for h, v in d.items()} for k, d in sorted(by_ttx.items())},
    }


def trade_stats(markets: list[dict], c: Client) -> dict:
    sizes, imb_yes, n_trades, vol = [], 0.0, 0, 0.0
    agg = {h: [] for h in (*HORIZONS, "settle")}
    agg_ttx = defaultdict(lambda: {h: [] for h in (*HORIZONS, "settle")})
    per_market = []
    for m in markets:
        tr = c.trades(m["ticker"])
        if not tr:
            continue
        settle = {"yes": 1.0, "no": 0.0}.get(m.get("result"))
        mo = markouts(tr, settle, ts(m["close_time"]))
        q = [f(t["count_fp"]) for t in tr]
        sizes += q
        vol += sum(q)
        n_trades += len(tr)
        imb_yes += sum(x for x, t in zip(q, tr) if t["taker_side"] == "yes")
        for h in agg:
            agg[h].append((mo["overall"][h], sum(q)))
            for ttx, d in mo["by_ttx"].items():
                agg_ttx[ttx][h].append((d[h], sum(qq for qq, t in zip(q, tr) if int((ts(m["close_time"]) - tsf(t["created_time"])) // 60) == ttx)))
        per_market.append((m["ticker"], len(tr), sum(q), mo["overall"]))
    sizes.sort()
    return {
        "sampled_markets": len(per_market), "trades": n_trades, "volume": vol,
        "size_median": st.median(sizes) if sizes else float("nan"),
        "size_p90": sizes[int(0.9 * len(sizes))] if sizes else float("nan"),
        "size_mean": vol / n_trades if n_trades else float("nan"),
        "taker_yes_share": imb_yes / vol if vol else float("nan"),
        "markout_vw": {h: wmean(v) for h, v in agg.items()},
        "markout_by_ttx": {k: {h: wmean(v) for h, v in d.items()} for k, d in sorted(agg_ttx.items())},
        "per_market": per_market,
    }


# ----------------------------------------------------------------- report ---

def sample(markets: list[dict], n: int) -> list[dict]:
    """Spread the sample across the period; for many-strike series prefer volume."""
    ms = sorted(markets, key=lambda m: -f(m.get("volume_fp", 0)))
    ms = [m for m in ms if f(m.get("volume_fp", 0)) > 0]
    if not ms:
        return []
    ms.sort(key=lambda m: m["close_time"])
    step = max(1, len(ms) // n)
    return ms[::step][:n]


def fmt_c(x: float) -> str:
    return "  n/a " if x != x else f"{x:+6.2f}"


def report(series: str, cs: dict, tsd: dict, hours: float) -> str:
    L = [f"## {series}", ""]
    L.append(f"- markets settled in window: {cs['markets']} ({cs['markets_with_volume']} with volume); "
             f"volume {cs['volume']:,.0f} contracts = {cs['volume']/hours*24:,.0f}/day")
    L.append(f"- quoted spread (1-min closes): volume-weighted {cs['spread_vw_cents']:.2f}c, median {cs['spread_median_cents']:.2f}c")
    top_hours = sorted(cs["vol_by_hour_utc"].items(), key=lambda kv: -kv[1])[:4]
    L.append("- busiest hours (UTC): " + ", ".join(f"{h:02d}h {v/cs['volume']*100:.0f}%" for h, v in top_hours))
    ttx_items = list(cs["vol_by_ttx"].items())
    if ttx_items:
        last3 = sum(v for k, v in ttx_items if k <= 2) / cs["volume"] * 100 if cs["volume"] else 0
        L.append(f"- share of volume in the last 3 minutes before expiry: {last3:.0f}%")
    L.append("")
    if not tsd["trades"]:
        L.append("_no trades sampled_")
        return "\n".join(L)
    L.append(f"- trade sample: {tsd['sampled_markets']} markets, {tsd['trades']:,} trades, {tsd['volume']:,.0f} contracts; "
             f"size median {tsd['size_median']:.0f} / mean {tsd['size_mean']:.0f} / p90 {tsd['size_p90']:.0f}; "
             f"taker bought YES {tsd['taker_yes_share']*100:.0f}% of volume")
    mv = tsd["markout_vw"]
    L.append("")
    L.append("Maker markout, cents per contract, volume-weighted (positive = maker profits before spread):")
    L.append("")
    L.append("| horizon | 10s | 30s | 60s | settlement |")
    L.append("|---|---|---|---|---|")
    L.append(f"| all trades | {fmt_c(mv[10])} | {fmt_c(mv[30])} | {fmt_c(mv[60])} | {fmt_c(mv['settle'])} |")
    L.append("")
    L.append("By minutes-to-expiry at trade time (volume-weighted):")
    L.append("")
    L.append("| min to expiry | 10s | 30s | 60s | settlement |")
    L.append("|---|---|---|---|---|")
    for k, d in tsd["markout_by_ttx"].items():
        if k > 20:
            continue
        L.append(f"| {k:2d} | {fmt_c(d[10])} | {fmt_c(d[30])} | {fmt_c(d[60])} | {fmt_c(d['settle'])} |")
    half = cs["spread_vw_cents"] / 2
    L.append("")
    L.append(f"Reading: markout already includes the captured half-spread (~{half:.2f}c). "
             f"Implied adverse selection = half-spread - markout: "
             + ", ".join(f"{h}s {fmt_c(half - mv[h]).strip()}c" for h in HORIZONS) + f", settlement {fmt_c(half - mv['settle']).strip()}c. "
             "Markout itself is the maker's gross P&L per contract for a touch fill unwound at that horizon.")
    L.append("")
    L.append("Per-market (ticker, trades, contracts, markout 30s / settle):")
    L.append("")
    for tk, n, q, mo in tsd["per_market"]:
        L.append(f"- `{tk}` {n:,} trades, {q:,.0f} contracts, {fmt_c(mo[30])}c / {fmt_c(mo['settle'])}c")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--series", nargs="+", default=["KXBTC15M", "KXETH15M", "KXBTCD"])
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--sample", type=int, default=12, help="markets per series to pull full trade tapes for")
    ap.add_argument("--cache", type=Path, default=Path("../data/research_cache"))
    ap.add_argument("--out", type=Path, default=Path("../research/phase_a.md"))
    a = ap.parse_args()

    c = Client(a.cache)
    now = int(time.time())
    sections = [f"# Phase A: market-making viability read", "",
                f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC over markets settled in the last {a.hours:g}h. "
                f"Method: see `python/kalshi_data/research/phase_a.py`.", ""]
    for s in a.series:
        print(f"[{s}] listing markets...", file=sys.stderr)
        ms = c.settled_markets(s, now - int(a.hours * 3600))
        print(f"[{s}] {len(ms)} markets; candles...", file=sys.stderr)
        cs = candle_stats(s, ms, c)
        sm = sample(ms, a.sample)
        print(f"[{s}] trades for {len(sm)} sampled markets...", file=sys.stderr)
        tsd = trade_stats(sm, c)
        sections.append(report(s, cs, tsd, a.hours))
        sections.append("")
        print(f"[{s}] done ({c.requests} requests so far)", file=sys.stderr)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(sections))
    print("\n".join(sections))


if __name__ == "__main__":
    main()
