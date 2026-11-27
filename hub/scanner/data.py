"""Free data for the coin scanner: CoinGecko (no key), Coin Metrics community (no key), DefiLlama (no key).
Stored on the data branch under scanner/ only. Everything fetched is data, never instructions.

Prices: one file per coin (scanner/prices/<id>.csv: date, close, source), each date = that day's close (UTC).
- First load: CoinGecko's free year (365 daily points, with market caps for supply). Where Coin Metrics has the
  same coin (matched by symbol AND agreeing with CoinGecko within 3% on the shared days) its longer history is used.
- Then each day: new closes from Coin Metrics (batched) or CoinGecko (a few days per coin).
Supply: scanner/supply/<id>.csv (date, circulating) from CoinGecko market cap / price, then the daily figure.
"""
import json
import time
from pathlib import Path

import pandas as pd

from hub.util import scrub

CG = "https://api.coingecko.com/api/v3"
CM = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
LLAMA = "https://api.llama.fi"


class Free:
    """Polite access to the free APIs: spacing between CoinGecko calls and patience on 429."""

    def __init__(self, web, spacing=7.0, sleep=time.sleep):
        self.web, self.spacing, self.sleep, self.last = web, spacing, sleep, 0.0
        self.calls = {"coingecko": 0, "coinmetrics": 0, "defillama": 0}

    def get(self, url, params=None, kind="coingecko"):
        if kind == "coingecko":
            wait = self.spacing - (time.time() - self.last)
            if wait > 0:
                self.sleep(wait)
        for i in range(4):
            self.calls[kind] += 1
            r = self.web.get(url, params=params, timeout=90, ok=tuple(range(100, 600)))
            self.last = time.time()
            if getattr(r, "status_code", 200) == 429:
                self.sleep(30 * (i + 1))
                continue
            return r
        return r


def read_csv(p, col):
    p = Path(p)
    if not p.exists():
        return pd.Series(dtype=float)
    df = pd.read_csv(p)
    return pd.Series(df[col].values, index=pd.to_datetime(df["date"]), dtype=float).sort_index()


def write_series(p, s, col, source=None):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    s = s[~s.index.duplicated(keep="last")].sort_index()
    df = pd.DataFrame({"date": s.index.strftime("%Y-%m-%d"), col: s.values})
    if source is not None:
        df["source"] = source if isinstance(source, str) else source.reindex(s.index).values
    df.to_csv(p, index=False)


def merge(old, new):
    return pd.concat([old, new])[lambda x: ~x.index.duplicated(keep="first")].sort_index() if len(old) else new.sort_index()


# ------------------------------------------------------------------ CoinGecko
def markets(api, n, extra_ids=()):
    rows = []
    r = api.get(f"{CG}/coins/markets", {"vs_currency": "usd", "order": "market_cap_desc", "per_page": n, "page": 1,
                                        "price_change_percentage": "7d"})
    rows += r.json()
    missing = [i for i in extra_ids if i not in {x["id"] for x in rows}]
    if missing:
        r = api.get(f"{CG}/coins/markets", {"vs_currency": "usd", "ids": ",".join(missing), "price_change_percentage": "7d"})
        rows += r.json()
    return rows


def categories(api, ids):
    out = {}
    for c in ids:
        r = api.get(f"{CG}/coins/markets", {"vs_currency": "usd", "category": c, "per_page": 250, "order": "market_cap_desc"})
        out[c] = sorted(x["id"] for x in r.json()) if getattr(r, "status_code", 200) == 200 else None
    return out


def cg_year(api, coin, days=365):
    """Daily closes and circulating supply from CoinGecko's free history. A point stamped 00:00 UTC on day D is
    the close of D-1; the last point (now) is dropped, because that day has not closed."""
    r = api.get(f"{CG}/coins/{coin}/market_chart", {"vs_currency": "usd", "days": days, "interval": "daily"})
    j = r.json() if getattr(r, "status_code", 200) == 200 else {}
    pr = pd.Series({pd.Timestamp(t, unit="ms"): v for t, v in j.get("prices", [])}, dtype=float)
    mc = pd.Series({pd.Timestamp(t, unit="ms"): v for t, v in j.get("market_caps", [])}, dtype=float)
    keep = lambda s: s[(s.index.hour == 0) & (s.index.minute == 0)]  # noqa: E731
    pr, mc = keep(pr), keep(mc)
    pr.index = (pr.index - pd.Timedelta(days=1)).normalize()
    mc.index = (mc.index - pd.Timedelta(days=1)).normalize()
    supply = (mc / pr).replace([float("inf")], float("nan")).dropna()
    return pr[pr > 0], supply[supply > 0]


# ------------------------------------------------------------------ Coin Metrics
def cm_prices(api, symbols, start):
    """{symbol: Series of daily closes} for many coins in one call (assets Coin Metrics does not have are skipped)."""
    out, url = {}, CM
    params = {"assets": ",".join(symbols), "metrics": "PriceUSD", "frequency": "1d", "page_size": 10000,
              "start_time": start, "ignore_unsupported_errors": "true", "ignore_forbidden_errors": "true"}
    while url:
        r = api.get(url, params, kind="coinmetrics")
        if getattr(r, "status_code", 200) != 200:
            break
        j = r.json()
        for row in j.get("data", []):
            if row.get("PriceUSD"):
                out.setdefault(row["asset"], {})[pd.Timestamp(row["time"][:10])] = float(row["PriceUSD"])
        url, params = j.get("next_page_url"), None
    return {k: pd.Series(v, dtype=float).sort_index() for k, v in out.items()}


def same_coin(cm, cg, tol=0.03):
    """Coin Metrics' series is the same coin as CoinGecko's when they agree within 3% (median) on shared days."""
    both = pd.concat([cm, cg], axis=1, join="inner").dropna()
    if len(both) < 30:
        return False
    return float((both.iloc[:, 0] / both.iloc[:, 1] - 1).abs().median()) <= tol


# ------------------------------------------------------------------ DefiLlama
def llama_maps(api):
    """CoinGecko id -> DefiLlama fee-summary slug, for protocols and chains."""
    out = {}
    r = api.get(f"{LLAMA}/overview/fees", {"excludeTotalDataChart": "true", "excludeTotalDataChartBreakdown": "true",
                                            "dataType": "dailyFees"}, kind="defillama")
    for x in (r.json().get("protocols", []) if getattr(r, "status_code", 200) == 200 else []):
        if x.get("gecko_id") and x.get("slug") and (x.get("total30d") or 0) > 0:
            cur = out.get(x["gecko_id"])
            if cur is None or (x.get("total30d") or 0) > cur[1]:
                out[x["gecko_id"]] = (x["slug"], x.get("total30d") or 0)
    r = api.get(f"{LLAMA}/v2/chains", kind="defillama")
    for x in (r.json() if getattr(r, "status_code", 200) == 200 else []):
        if x.get("gecko_id") and x["gecko_id"] not in out and x.get("name"):
            out[x["gecko_id"]] = (x["name"].lower().replace(" ", "-"), 0)
    return {k: v[0] for k, v in out.items()}


def llama_daily(api, slug, data_type):
    r = api.get(f"{LLAMA}/summary/fees/{slug}", {"dataType": data_type}, kind="defillama")
    if getattr(r, "status_code", 200) != 200:
        return None
    rows = r.json().get("totalDataChart") or []
    s = pd.Series({pd.Timestamp(t, unit="s").normalize(): float(v) for t, v in rows if v is not None}, dtype=float)
    return s.sort_index() if len(s) else None


def revenue(api, slug):
    """{'revenue': Series, 'kind': 'revenue' or 'fees', 'holders': Series or None}, or None."""
    rev = llama_daily(api, slug, "dailyRevenue")
    kind = "revenue"
    if rev is None or rev.tail(180).sum() <= 0:
        rev, kind = llama_daily(api, slug, "dailyFees"), "fees"
    if rev is None:
        return None
    return {"revenue": rev, "kind": kind, "holders": llama_daily(api, slug, "dailyHoldersRevenue")}


def clean_prices(p, max_jump=10.0, skip_days=0):
    """Remove impossible jumps: a one-day move beyond 10x (or 1/10) is a listing artifact or a redenomination
    (trial, 27 Nov: Aptos x1,045 on its listing day in Coin Metrics, SUN x112 at a redenomination). Only the data
    after the last such jump is kept. `skip_days` drops a coin's first days after listing as well.
    Returns (cleaned series, list of notes)."""
    p = p.dropna()
    p = p[p > 0]
    notes = []
    if len(p) < 2:
        return p, notes
    ratio = p / p.shift(1)
    bad = ratio[(ratio > max_jump) | (ratio < 1 / max_jump)]
    if len(bad):
        cut = bad.index[-1]
        notes.append(f"one-day move of x{float(bad.iloc[-1]):.3g} on {cut:%Y-%m-%d} treated as a data error: history before it dropped")
        p = p[p.index >= cut]
    if skip_days and len(p):
        p = p[p.index >= p.index[0] + pd.Timedelta(days=skip_days)]
    return p, notes


def save_json(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, default=str))


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def safe(msg):
    return scrub(msg)[:300]
