"""Coin Metrics community API. Realised price = price divided by MVRV (cross-check only)."""
import pandas as pd

from hub.sources import Result

URL = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"


def parse(rows):
    out = {}
    for x in rows:
        try:
            out[pd.Timestamp(x["time"][:10])] = float(x["PriceUSD"]) / float(x["CapMVRVCur"])
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            continue
    return pd.Series(out, dtype=float)


def fetch(entries, ctx):
    res = Result()
    for e in entries:
        start = ctx.since(e, 15)
        rows, url, params = [], URL, {"assets": "btc", "metrics": "PriceUSD,CapMVRVCur", "frequency": "1d",
                                      "page_size": 10000, "start_time": start.strftime("%Y-%m-%d")}
        while url:
            j = ctx.web.get(url, params=params, timeout=90).json()
            rows += j.get("data", [])
            url, params = j.get("next_page_url"), None
        s = parse(rows)
        res.history[e["id"]] = s[s.index < ctx.today]
    return res
