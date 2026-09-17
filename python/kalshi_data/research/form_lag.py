"""For every touch vacate on the active market: how long until a bid appears at the vacated price?"""
import sys, bisect
from datetime import date
from pathlib import Path
sys.path.insert(0, ".")
from kalshi_data.raw import iter_records
from kalshi_data.book import parse_price, parse_qty
from kalshi_data.research.markouts import FastBook, close_time
ONE=10_000
day = date.fromisoformat(sys.argv[1]); data_dir = Path("../data_aws")
books = {}; closes = {}
births = {}   # (tk, side, price) -> rx first size>0
lags = []; nform = 0; nvac = 0; pend = []
for rec in iter_records(data_dir, day):
    raw = rec.raw; t = raw.get("type")
    if t not in ("orderbook_snapshot", "orderbook_delta"): continue
    tk = raw["msg"]["market_ticker"]
    if not tk.startswith("KXBTC15M-"): continue
    b = books.get(tk)
    if b is None:
        b = books[tk] = FastBook(); closes[tk] = close_time(tk) * 1e9
    rx = rec.rx_ns
    if t == "orderbook_snapshot":
        b.snapshot(raw["msg"]); continue
    msg = raw["msg"]; side, price, d = msg["side"], parse_price(msg["price_dollars"]), parse_qty(msg["delta_fp"])
    best_before = b.best(side)
    try: b.delta(side, price, d)
    except ValueError: continue
    # active market only: nearest close > now, not in the last 5 min
    if not (closes[tk] - 300e9 > rx > closes[tk] - 900e9): continue
    if d > 0 and b.side(side).get(price, 0) == d:   # level born
        births[(tk, side, price)] = rx
    if d < 0 and price == best_before and b.best(side) < best_before:
        # side's touch vacated (its best fell): the other side can now bid at ONE - best_before
        nvac += 1
        other = "no" if side == "yes" else "yes"
        vac_price = ONE - best_before
        # was there already a bid at that price? (crossing impossible, so no) -> record pending
        births.pop((tk, other, vac_price), None)
        pend.append((rx, tk, other, vac_price))
    if d > 0 and (tk, side, price) in births and births[(tk, side, price)] == rx:
        # check if this birth answers a pending vacate
        for i in range(len(pend) - 1, -1, -1):
            vrx, vtk, vs, vp = pend[i]
            if rx - vrx > 2e9: break
            if vtk == tk and vs == side and vp == price:
                lags.append((rx - vrx) / 1e6); nform += 1; del pend[i]; break
    # prune
    while pend and rx - pend[0][0] > 2e9: pend.pop(0)

import numpy as np
lags = np.array(lags)
print(f"{sys.argv[1]}: vacates {nvac:,}, bid formed at the vacated price within 2 s: {nform:,} ({nform/max(1,nvac)*100:.0f}%)")
for p in (10, 25, 50, 75, 90): print(f"  formation lag p{p}: {np.percentile(lags, p):.0f} ms")
for ms in (5, 10, 16, 25, 50, 100): print(f"  formed within {ms:>3} ms: {(lags < ms).mean()*100:5.1f}%")
