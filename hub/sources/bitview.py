"""Bitview (hosted Bitcoin Research Kit). Free, no key. Data CC BY 4.0.

Daily values are positions counted from 1 January 2009. The last position is
today, still moving, so it is dropped: history holds finished days only.
"""
import pandas as pd

from hub.sources import Result

BASE = "https://bitview.space/api/series/{}/day1"
EPOCH = pd.Timestamp("2009-01-01")


def parse(block, today):
    idx = [EPOCH + pd.Timedelta(days=block["start"] + i) for i in range(len(block["data"]))]
    s = pd.Series(block["data"], index=idx, dtype=float).dropna()
    return s[s.index < today]


def fetch(entries, ctx):
    res = Result()
    for e in entries:
        try:
            start = ctx.since(e, 15)
            r = ctx.web.get(BASE.format(e["code"]), params={"start": start.strftime("%Y-%m-%d")}, timeout=120)
            res.history[e["id"]] = parse(r.json(), ctx.today)
        except Exception as ex:
            res.errors[e["id"]] = str(ex)
    return res
