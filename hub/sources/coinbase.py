"""Coinbase Exchange daily candles. A candle is [time, low, high, open, close, volume]."""
import pandas as pd

from hub.sources import Result

URL = "https://api.exchange.coinbase.com/products/{}/candles"


def parse(candles, now_ts):
    """Split candles into finished daily closes and the live price (close of the open candle)."""
    done, live = {}, None
    for t, _lo, _hi, _op, close, _vol in candles:
        if t + 86400 <= now_ts:
            done[pd.Timestamp(t, unit="s")] = float(close)
        elif live is None or t > live[1]:
            live = (float(close), t)
    return pd.Series(done, dtype=float).sort_index(), (live[0] if live else None)


def fetch(entries, ctx):
    res = Result()
    now_ts = ctx.now.timestamp()
    for e in entries:
        try:
            start = ctx.since(e, 20)
            parts, end, live = [], ctx.today + pd.Timedelta(days=1), None
            while end > start:
                lo = max(start, end - pd.Timedelta(days=299))
                r = ctx.web.get(URL.format(e["code"]), params={"granularity": 86400,
                                "start": lo.strftime("%Y-%m-%dT00:00:00Z"), "end": end.strftime("%Y-%m-%dT00:00:00Z")})
                s, lv = parse(r.json(), now_ts)
                parts.append(s)
                live = live if live is not None else lv
                end = lo - pd.Timedelta(days=1)
            res.history[e["id"]] = pd.concat(parts).sort_index()
            if live is not None:
                res.live[e["id"]] = (live, ctx.now.isoformat())
        except Exception as ex:
            res.errors[e["id"]] = str(ex)
    return res
