"""DefiLlama stablecoin supply. Today's still-moving figure is passed as live, not stored."""
import pandas as pd

from hub.sources import Result

URL = "https://stablecoins.llama.fi/stablecoincharts/all"


def parse(rows):
    usd, allp = {}, {}
    for x in rows:
        c = x.get("totalCirculatingUSD") or {}
        if not c:
            continue
        d = pd.Timestamp(int(x["date"]), unit="s").normalize()
        usd[d] = float(c.get("peggedUSD", 0.0))
        allp[d] = float(sum(c.values()))
    return pd.Series(usd, dtype=float).sort_index(), pd.Series(allp, dtype=float).sort_index()


def fetch(entries, ctx):
    res = Result()
    usd, allp = parse(ctx.web.get(URL, timeout=90).json())
    for e in entries:
        s = usd if e["code"] == "peggedUSD" else allp
        s = s[s.index >= ctx.since(e, 45)]
        res.history[e["id"]] = s[s.index < ctx.today]
        if len(s) and s.index[-1] >= ctx.today:
            res.live[e["id"]] = (float(s.iloc[-1]), ctx.now.isoformat())
    return res
