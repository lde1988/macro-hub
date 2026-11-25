"""Coinalyze: funding rates. Needs the COINALYZE_API_KEY secret. Rate limit: 40 symbols a minute.
Open interest is in coinalyze_oi.py (its own daily job, because it needs about a thousand markets)."""
import time
from pathlib import Path

import pandas as pd

from hub.sources import Result
from hub.util import SourceError, load_yaml

BASE = "https://api.coinalyze.net/v1"


def call(ctx, path, key, **params):
    for _ in range(8):
        r = ctx.web.get(BASE + path, headers={"api_key": key}, params=params, ok=(200, 429), timeout=90)
        if r.status_code == 200:
            return r.json()
        time.sleep(min(float(r.headers.get("Retry-After", 20)) + 0.5, 65))
    raise SourceError("Coinalyze still rate-limited after 8 tries")


def parse_history(items, today):
    """{symbol: Series(date -> daily close)}; today's unfinished day is dropped."""
    out = {}
    for x in items or []:
        s = pd.Series({pd.Timestamp(h["t"], unit="s").normalize(): float(h["c"]) for h in x.get("history", [])}, dtype=float)
        out[x["symbol"]] = s[s.index < today].sort_index()
    return out


def sum_universe(hist, btc_symbols, alt_symbols):
    """Daily totals. A market with no value for a day is carried forward up to 3 days
    so one missing print does not make the total jump."""
    df = pd.DataFrame(hist).sort_index().ffill(limit=3)
    btc = df[[c for c in btc_symbols if c in df]].sum(axis=1, min_count=1)
    alt = df[[c for c in alt_symbols if c in df]].sum(axis=1, min_count=1)
    return btc.dropna(), alt.dropna()


def fetch(entries, ctx):
    key = ctx.env.get("COINALYZE_API_KEY", "").strip()
    if not key:
        raise SourceError("COINALYZE_API_KEY is not set")
    res = Result()
    t1 = int(ctx.now.timestamp())
    fund = [e for e in entries if e["code"].startswith("funding:")]
    for e in fund:
        try:
            t0 = int(ctx.since(e, 20).timestamp())
            j = call(ctx, "/funding-rate-history", key, symbols=e["code"].split(":", 1)[1], interval="daily",
                     **{"from": t0, "to": t1})
            res.history[e["id"]] = next(iter(parse_history(j, ctx.today).values()))
        except Exception as ex:
            res.errors[e["id"]] = str(ex)
    return res
