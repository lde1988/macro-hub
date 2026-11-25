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


def last_finished_session(now):
    """Latest New York date whose trading session is over (the close is at 16:00; one hour's margin)."""
    ny = pd.Timestamp(now).tz_convert("America/New_York") if pd.Timestamp(now).tzinfo else pd.Timestamp(now, tz="UTC").tz_convert("America/New_York")
    day = ny.normalize().tz_localize(None)
    return day if ny.hour >= 17 else day - pd.Timedelta(days=1)


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
            s = s[s.index <= last_finished_session(ctx.now)]   # never store a price from a session still trading
            res.history[e["id"]] = s
        except Exception as ex:
            res.errors[e["id"]] = str(ex)
    return res
