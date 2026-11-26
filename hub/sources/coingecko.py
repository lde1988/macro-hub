"""CoinGecko (no key). Two kinds of series, each recorded once a day (no free history):
- dotted paths into /global, for example "total_market_cap.usd";
- "markets:<coin id>:<field>" from /coins/markets (supply figures), all coins in one call."""
import pandas as pd

from hub.sources import Result

URL = "https://api.coingecko.com/api/v3/global"
MARKETS = "https://api.coingecko.com/api/v3/coins/markets"


def dig(d, dotted):
    for k in dotted.split("."):
        d = d[k]
    return float(d)


def fetch(entries, ctx):
    res = Result()
    glob = [e for e in entries if not e["code"].startswith("markets:")]
    mk = [e for e in entries if e["code"].startswith("markets:")]
    if glob:
        data = ctx.web.get(URL).json()["data"]
        for e in glob:
            v = dig(data, e["code"])
            res.history[e["id"]] = pd.Series({ctx.today: v})
            res.once.add(e["id"])
            res.live[e["id"]] = (v, ctx.now.isoformat())
    if mk:
        ids = sorted({e["code"].split(":")[1] for e in mk})
        try:
            rows = {r["id"]: r for r in ctx.web.get(MARKETS, params={"vs_currency": "usd", "ids": ",".join(ids)}).json()}
            for e in mk:
                _, cid, field = e["code"].split(":")
                v = (rows.get(cid) or {}).get(field)
                if v is None:
                    res.errors[e["id"]] = f"{cid} has no {field}"
                    continue
                res.history[e["id"]] = pd.Series({ctx.today: float(v)})
                res.once.add(e["id"])
        except Exception as ex:
            for e in mk:
                res.errors[e["id"]] = str(ex)
    return res
