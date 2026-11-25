"""CoinGecko global snapshot. No free history, so one value is recorded per UTC day."""
import pandas as pd

from hub.sources import Result

URL = "https://api.coingecko.com/api/v3/global"


def dig(d, dotted):
    for k in dotted.split("."):
        d = d[k]
    return float(d)


def fetch(entries, ctx):
    res = Result()
    data = ctx.web.get(URL).json()["data"]
    for e in entries:
        v = dig(data, e["code"])
        res.history[e["id"]] = pd.Series({ctx.today: v})
        res.once.add(e["id"])
        res.live[e["id"]] = (v, ctx.now.isoformat())
    return res
