"""Nasdaq's quote service: daily closes. Unofficial, free, not adjusted for dividends."""
import pandas as pd

from hub.sources import Result

URL = "https://api.nasdaq.com/api/quote/{}/historical"


def parse(rows):
    out = {}
    for x in rows or []:
        try:
            out[pd.to_datetime(x["date"], format="%m/%d/%Y")] = float(str(x["close"]).replace("$", "").replace(",", ""))
        except (KeyError, ValueError):
            continue
    return pd.Series(out, dtype=float).sort_index()


def fetch(entries, ctx):
    res = Result()
    for e in entries:
        try:
            sym, cls = e["code"].split(":")
            start = ctx.since(e, 30)
            j = ctx.web.get(URL.format(sym), params={"assetclass": cls, "fromdate": start.strftime("%Y-%m-%d"),
                            "todate": ctx.today.strftime("%Y-%m-%d"), "limit": 9999}).json()
            s = parse(((j.get("data") or {}).get("tradesTable") or {}).get("rows"))
            if s.empty:
                raise ValueError("no rows")
            res.history[e["id"]] = s
        except Exception as ex:
            res.errors[e["id"]] = str(ex)
    return res
