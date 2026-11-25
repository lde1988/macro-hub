"""Coinalyze open interest: altcoins against Bitcoin. Needs the COINALYZE_API_KEY secret.

Summed over the markets in registry/oi_universe.yaml (every Bitcoin perpetual, and the crypto
altcoin perpetuals holding 97% of altcoin open interest). About a thousand markets at 40 a
minute takes roughly 27 minutes, so this runs in its own daily workflow, not in the 15-minute run.
"""
from pathlib import Path

import pandas as pd

from hub.sources import Result
from hub.sources.coinalyze import call, parse_history, sum_universe
from hub.util import SourceError, load_yaml


def fetch(entries, ctx):
    key = ctx.env.get("COINALYZE_API_KEY", "").strip()
    if not key:
        raise SourceError("COINALYZE_API_KEY is not set")
    uni = load_yaml(Path(ctx.root) / "registry" / "oi_universe.yaml")
    btc, alt = uni["btc"], uni["alt"]
    syms, hist = btc + alt, {}
    ids = {e["code"]: e["id"] for e in entries}
    have = ctx.last.get(ids["oi:alt"])
    if ctx.backfill or have is None:
        start = pd.Timestamp(min(e["start"] for e in entries))
    else:   # reach back to the last stored day (plus a small overlap), so a missed day is filled in
        start = min(pd.Timestamp(have) - pd.Timedelta(days=3), ctx.today - pd.Timedelta(days=6))
    t0, t1 = int(start.timestamp()), int(ctx.now.timestamp())
    failed = 0
    for i in range(0, len(syms), 20):
        try:
            j = call(ctx, "/open-interest-history", key, symbols=",".join(syms[i:i + 20]), interval="daily",
                     convert_to_usd="true", **{"from": t0, "to": t1})
            hist.update(parse_history(j, ctx.today))
        except Exception:
            failed += 20
    if failed > len(syms) * 0.02:      # a total built from an incomplete list would look like a fall in open interest
        raise SourceError(f"{failed} of {len(syms)} markets could not be read; nothing stored")
    b, a = sum_universe(hist, btc, alt)
    b = b[b > 0]
    a = a.reindex(b.index).dropna()    # days without Bitcoin open interest are dropped: the ratio would be meaningless
    res = Result()
    cut = start if (ctx.backfill or have is None) else pd.Timestamp(have) - pd.Timedelta(days=2)
    res.history[ids["oi:btc"]] = b[b.index >= cut]
    res.history[ids["oi:alt"]] = a[a.index >= cut]
    return res
