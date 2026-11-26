"""DefiLlama fees (free, no key): fees paid by users per day, per protocol or chain.
"Fees" means different things for different coins (trading fees, gas, oracle payments)."""
import pandas as pd

from hub.sources import Result

URL = "https://api.llama.fi/summary/fees/{}"


def parse(j, today):
    s = pd.Series({pd.Timestamp(int(t), unit="s").normalize(): float(v) for t, v in (j.get("totalDataChart") or []) if v is not None},
                  dtype=float).sort_index()
    return s[s.index < today]          # today's figure is still moving


def fetch(entries, ctx):
    res = Result()
    for e in entries:
        try:
            j = ctx.web.get(URL.format(e["code"]), params={"dataType": "dailyFees"}, timeout=90).json()
            s = parse(j, ctx.today)
            res.history[e["id"]] = s[s.index >= ctx.since(e, 20)]
        except Exception as ex:
            res.errors[e["id"]] = str(ex)
    return res
