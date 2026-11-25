"""Coinalyze: funding rates and open interest. Needs the COINALYZE_API_KEY secret.

Rate limit: 40 symbols a minute. Open interest is summed over the markets
listed in registry/oi_universe.yaml and refreshed once a day.
"""
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
    oi = {e["code"]: e for e in entries if e["code"].startswith("oi:")}
    uni_path = Path(ctx.root) / "registry" / "oi_universe.yaml"
    have = ctx.last.get("OI_ALT")
    due = have is None or pd.Timestamp(have) < ctx.today - pd.Timedelta(days=1)  # once a day is enough
    if oi and uni_path.exists() and due:
        uni = load_yaml(uni_path)
        btc, alt = uni.get("btc", []), uni.get("alt", [])
        syms, hist = btc + alt, {}
        reach = min((ctx.today - pd.Timestamp(have)).days + 3, 90) if have is not None else 10
        t0 = int((ctx.today - pd.Timedelta(days=max(reach, 10))).timestamp())
        try:
            for i in range(0, len(syms), 20):
                j = call(ctx, "/open-interest-history", key, symbols=",".join(syms[i:i + 20]), interval="daily",
                         convert_to_usd="true", **{"from": t0, "to": t1})
                hist.update(parse_history(j, ctx.today))
            b, a = sum_universe(hist, btc, alt)
            # only days after the last stored one (plus a 2-day overlap) are written: older days came from the full back-fill
            cut = pd.Timestamp(have) - pd.Timedelta(days=2) if have is not None else ctx.today - pd.Timedelta(days=3)
            res.history[oi["oi:btc"]["id"]] = b[b.index >= cut]
            res.history[oi["oi:alt"]["id"]] = a[a.index >= cut]
        except Exception as ex:
            res.errors["OI_BTC"] = res.errors["OI_ALT"] = str(ex)
    return res
