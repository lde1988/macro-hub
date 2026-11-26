"""Coin valuations. Pure functions; no network. Context only: these readings never enter the
buy / hold reading, the backdrop or any push.

Two price readings per coin, each in standard deviations:
- Short term, every coin: the 1-year z-score. Over the last 365 daily closes, take the mean and the
  standard deviation (sample form) of the natural log of the close. Reading = (log price today - mean)
  / standard deviation. Fair value = exp(mean).
- Long term, coins with at least 4 years of history: the 4-year trend channel. A straight line fitted
  to the log of the daily close against time over the last 1,461 days only, refitted daily; the
  standard deviation of the residuals over the same window (population form). Fair value = the line today.
A third reading, price against revenue, is further down.
"""
import math

import numpy as np
import pandas as pd

ZONES = ["-3 SD oversold", "-2 SD oversold", "-1 SD oversold", "below fair value", "above fair value",
         "+1 SD overbought", "+2 SD overbought", "+3 SD overbought"]
METHODS = "Short term: compared with the last year. Long term: trend over the last 4 years."
SHORT_LABEL = "Compared with its average price over the last year."
LABEL = "Trend-based estimate. Assumes the last 4 years' growth continues."
NO_FIT = "the line does not fit this coin's last 4 years; reading not meaningful"


def zone(z):
    """Eight zones: the fair-value band is split at 0 into "below fair value" (-1 to 0) and
    "above fair value" (0 to +1), both amber; 1 to 2 SD is the first band, 2 to 3 the second,
    beyond 3 the third. An exact edge belongs to the zone nearer the line."""
    if abs(z) <= 1:
        return ("below fair value", "amber") if z < 0 else ("above fair value", "amber")
    k = min(int(math.ceil(abs(z))) - 1, 3)
    return (f"-{k} SD oversold", "green") if z < 0 else (f"+{k} SD overbought", "red")


def _bands(centre, sd):
    return {f"{k:+d}": math.exp(centre + k * sd) for k in (-3, -2, -1, 1, 2, 3)}   # keys "+1", "-2"... (JSON-safe)


def _price_now(s, price_now, cfg):
    last = float(s.iloc[-1])
    if price_now and abs(float(price_now) / last - 1) <= cfg["valuations"]["live_max_gap"]:
        return float(price_now), True
    return last, False


def one_year(history, cfg, price_now=None):
    """Short term: the 1-year z-score of the log price (sample standard deviation)."""
    v = cfg["valuations"]
    n = v["short_days"]
    s = history[history > 0].sort_index() if len(history) else history
    base = {"label": SHORT_LABEL, "days_available": len(s)}
    if len(s) < n:
        return {**base, "status": "too_little", "text": "too little history"}
    w = np.log(s.iloc[-n:].values)
    mean, sd = float(w.mean()), float(w.std(ddof=1))
    p, live = _price_now(s, price_now, cfg)
    z = (math.log(p) - mean) / sd if sd > 1e-12 else 0.0
    name, colour = zone(z)
    return {**base, "status": "ok", "z": round(z, 3), "zone": name, "colour": colour, "price": p, "price_is_live": live,
            "last_close_date": str(s.index[-1])[:10], "fair_value": math.exp(mean), "bands": _bands(mean, sd),
            "window_from": str(s.index[-n])[:10]}


def fit(s):
    """Straight line through the log of the closes s against calendar days, with its fit."""
    t = (s.index - s.index[0]).days.values.astype(float)
    y = np.log(s.values)
    slope, intercept = np.polyfit(t, y, 1)
    resid = y - (intercept + slope * t)
    sd = float(resid.std())
    r2 = float(1 - resid.var() / y.var()) if y.var() > 0 else 0.0
    return {"start": s.index[0], "intercept": float(intercept), "slope": float(slope), "sd": sd, "r2": r2}


def channel(history, cfg, price_now=None, today=None):
    """Long term: the 4-year trend channel, refitted on the last 1,461 days. None for a coin with under 4 years."""
    v = cfg["valuations"]
    n = v["long_days"]
    s = history[history > 0].sort_index() if len(history) else history
    if (len(s) and (s.index[-1] - s.index[0]).days + 1 < n) or len(s) < n * 0.9:
        return None
    w = s[s.index > s.index[-1] - pd.Timedelta(days=n)]
    f = fit(w)
    today = pd.Timestamp(today).normalize() if today is not None else w.index[-1]
    centre = f["intercept"] + f["slope"] * (today - f["start"]).days
    p, live = _price_now(s, price_now, cfg)
    z = (math.log(p) - centre) / f["sd"] if f["sd"] > 1e-12 else 0.0
    name, colour = zone(z)
    out = {"label": LABEL, "status": "ok", "z": round(z, 3), "zone": name, "colour": colour, "price": p, "price_is_live": live,
           "fair_value": math.exp(centre), "growth_per_year": math.exp(f["slope"] * 365) - 1, "r2": round(f["r2"], 3),
           "bands": _bands(centre, f["sd"]), "window_from": str(w.index[0])[:10], "warnings": []}
    if f["r2"] < v["min_r_squared"]:
        out["status"] = "greyed"
        out["warnings"] = [NO_FIT]
    return out


REVENUE_LABEL = "Fully diluted value against the last year of fees, compared with its own history only"
APPROX = "approximate: past supply estimated"


def revenue(price, fees, cfg, rc, supply=None, circulating=None, total=None, price_now=None):
    """Price against revenue: fully diluted value / the last 365 days of fees, as a z-score of its log
    against the coin's own history of the same multiple.
    rc: the coin's revenue settings. supply: Ether's supply history when rc["supply"] == "history"."""
    v = cfg["valuations"]
    n, need = v["revenue_days"], v["revenue_min_days"]
    out = {"label": REVENUE_LABEL, "approximate": bool(rc.get("approximate")), "note": rc.get("note", ""),
           # a caveat greys the reading and is shown beside it: estimated past supply, or a short fee history
           "caveat": rc.get("caveat") or (APPROX if rc.get("approximate") else "")}
    if rc.get("supply") == "max":
        out["unlock"] = 1 - circulating / rc["max_supply"] if circulating else None
    elif circulating and total:
        out["unlock"] = max(0.0, 1 - circulating / total)
    if not len(fees) or not len(price):
        return {**out, "status": "none", "text": "no fees data"}
    f = fees.sort_index()
    f = f.reindex(pd.date_range(f.index[0], f.index[-1], freq="D")).fillna(0.0)
    have = len(f) - (n - 1)                                   # days of the multiple available
    if have < need:
        return {**out, "status": "waiting", "available_in": (need - have), "days": max(have, 0)}
    roll = f.rolling(n).sum().dropna()
    roll = roll[roll > 0]
    if rc.get("supply") == "max":
        sup = pd.Series(float(rc["max_supply"]), index=price.index)
    elif rc.get("supply") == "history":
        sup = supply.reindex(price.index.union(supply.index)).ffill().reindex(price.index) if supply is not None and len(supply) else None
    else:
        sup = pd.Series(float(total), index=price.index) if total else None
    if sup is None:
        return {**out, "status": "none", "text": "no supply figure"}
    fdv = (price * sup).dropna()
    m = (fdv / roll).dropna()
    m = m[m > 0]
    if len(m) < need:
        return {**out, "status": "waiting", "available_in": need - len(m), "days": len(m)}
    lm = np.log(m)
    last_price = float(price.iloc[-1])
    p = float(price_now) if price_now and abs(float(price_now) / last_price - 1) <= v["live_max_gap"] else last_price
    fdv_now = p * float(sup.dropna().iloc[-1])
    mult = fdv_now / float(roll.iloc[-1])
    sd = float(lm.std())
    z = (math.log(mult) - float(lm.mean())) / sd if sd > 1e-9 else 0.0    # a multiple that never moved reads 0
    name, colour = zone(z)
    return {**out, "status": "ok", "z": round(z, 3), "zone": name, "colour": colour, "multiple": mult, "fdv": fdv_now,
            "fees_365": float(roll.iloc[-1]), "typical_multiple": math.exp(float(lm.mean())), "days": len(m),
            "fees_to": str(f.index[-1])[:10]}


def all_coins(view, cfg):
    """All readings per coin, in the configured order. view: hub.signals.core.View."""
    out = []
    for c in cfg["valuations"]["coins"]:
        hist, live = view.s(c["history"]), view.live(c["live"])
        rv = None
        if c.get("revenue"):
            rc = c["revenue"]
            last = lambda sid: (float(view.s(sid).iloc[-1]) if len(view.s(sid)) else None)
            rv = revenue(hist, view.s(rc["fees"]), cfg, rc,
                         supply=view.s(rc["supply_series"]) if rc.get("supply_series") else None,
                         circulating=last(f"SUP_CIRC_{c['sym']}"), total=last(f"SUP_TOTAL_{c['sym']}"), price_now=live)
        out.append({"sym": c["sym"], "name": c["name"], "methods": METHODS,
                    "history_from": str(hist.index[0])[:10] if len(hist) else None,
                    "years": round((hist.index[-1] - hist.index[0]).days / 365.25, 2) if len(hist) else 0,
                    "short": one_year(hist, cfg, live), "long": channel(hist, cfg, live, view.now.normalize()), "revenue": rv})
    return out
