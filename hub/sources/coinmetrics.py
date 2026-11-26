"""Coin Metrics community API (free, no key; CC BY-NC 4.0, credit "Coin Metrics" with a link to coinmetrics.io).

Two kinds of series:
- "PriceUSD/CapMVRVCur": realised price = price divided by MVRV, a cross-check for Bitview.
- "price:<asset>": the daily price (PriceUSD), for the coin-valuation tab.
A daily value dated D is the price at the end of day D (UTC); it matches Coinbase's daily close for D.
"""
import pandas as pd

from hub.sources import Result

URL = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"


def parse(rows):
    """Realised price rows."""
    out = {}
    for x in rows:
        try:
            out[pd.Timestamp(x["time"][:10])] = float(x["PriceUSD"]) / float(x["CapMVRVCur"])
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            continue
    return pd.Series(out, dtype=float)


def parse_price(rows, metric="PriceUSD"):
    out = {}
    for x in rows:
        try:
            v = float(x[metric])
        except (KeyError, TypeError, ValueError):
            continue
        if v > 0:
            out[pd.Timestamp(x["time"][:10])] = v
    return pd.Series(out, dtype=float).sort_index()


def _get(ctx, assets, metrics, start):
    rows, url, params = [], URL, {"assets": assets, "metrics": metrics, "frequency": "1d",
                                  "page_size": 10000, "start_time": start.strftime("%Y-%m-%d")}
    while url:
        j = ctx.web.get(url, params=params, timeout=90).json()
        rows += j.get("data", [])
        url, params = j.get("next_page_url"), None
    return rows


def fetch(entries, ctx):
    res = Result()
    for e in entries:
        try:
            start = ctx.since(e, 15)
            if e["code"].startswith("price:"):
                s = parse_price(_get(ctx, e["code"].split(":", 1)[1], "PriceUSD", start))
            elif e["code"].startswith("supply:"):
                s = parse_price(_get(ctx, e["code"].split(":", 1)[1], "SplyCur", start), "SplyCur")
            else:
                s = parse(_get(ctx, "btc", "PriceUSD,CapMVRVCur", start))
            res.history[e["id"]] = s[s.index < ctx.today]
        except Exception as ex:
            res.errors[e["id"]] = str(ex)
    return res
