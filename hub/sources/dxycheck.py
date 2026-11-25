"""Published dollar index close, used only as a check beside the computed value.
It never drives a dial, and a failure here never raises a "source down" alert."""
import pandas as pd

from hub.sources import Result

URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}"


def parse(j):
    r = j["chart"]["result"][0]
    closes = r["indicators"]["quote"][0]["close"]
    out = {pd.Timestamp(t, unit="s").normalize(): float(c) for t, c in zip(r["timestamp"], closes) if c}
    return pd.Series(out, dtype=float).sort_index()


def fetch(entries, ctx):
    res = Result()
    for e in entries:
        j = ctx.web.get(URL.format(e["code"]), params={"range": "10y" if ctx.backfill else "1mo", "interval": "1d"}).json()
        s = parse(j)
        res.history[e["id"]] = s[s.index < ctx.today]
    return res
