"""FRED (St. Louis Fed). Needs the FRED_API_KEY secret. The key travels in the
web address, so errors never include the address (see hub/util.py)."""
import pandas as pd

from hub.sources import Result
from hub.util import SourceError

URL = "https://api.stlouisfed.org/fred/series/observations"
LOOKBACK = {"D": 120, "W": 400, "M": 900}  # days re-read each time, to catch revisions


def parse(obs):
    out = {}
    for o in obs:
        if o.get("value") not in (".", "", None):
            try:
                out[pd.Timestamp(o["date"])] = float(o["value"])
            except ValueError:
                continue
    return pd.Series(out, dtype=float).sort_index()


def fetch(entries, ctx):
    key = ctx.env.get("FRED_API_KEY", "").strip()
    if not key:
        raise SourceError("FRED_API_KEY is not set")
    res = Result()
    for e in entries:
        try:
            start = ctx.since(e, LOOKBACK.get(e["freq"], 120))
            r = ctx.web.get(URL, params={"series_id": e["code"], "api_key": key, "file_type": "json",
                                         "observation_start": start.strftime("%Y-%m-%d")})
            res.history[e["id"]] = parse(r.json().get("observations", []))
        except Exception as ex:
            res.errors[e["id"]] = str(ex)
    return res
