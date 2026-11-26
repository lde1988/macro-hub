"""Log-regression channel, as used by Raoul Pal and Real Vision. Pure functions; no network.

Fit a straight line to the natural log of the daily close against calendar days, over the coin's
full available history. Fair value is the line's value today. The reading is
(log price - log fair value) / standard deviation of the residuals (population form).
Context only: these readings never enter the buy / hold reading, the backdrop or any push.
"""
import math

import numpy as np
import pandas as pd

ZONES = ["-3 SD oversold", "-2 SD oversold", "-1 SD oversold", "below fair value", "above fair value",
         "+1 SD overbought", "+2 SD overbought", "+3 SD overbought"]
METHODS = "Long-term trend: Pal's method. Recent trend: compared with its 200-day average."
LABEL = "Trend-based estimate. Assumes past growth continues."
DRIFT = "A constant-growth line drifts toward oversold as a coin's growth slows; read with care for older coins."
NO_FIT = "the line does not fit this coin's history; reading not meaningful"


def zone(z):
    """Eight zones: the fair-value band is split at 0 into "below fair value" (-1 to 0) and
    "above fair value" (0 to +1), both amber; 1 to 2 SD is the first band, 2 to 3 the second,
    beyond 3 the third. An exact edge belongs to the zone nearer the line."""
    if abs(z) <= 1:
        return ("below fair value", "amber") if z < 0 else ("above fair value", "amber")
    k = min(int(math.ceil(abs(z))) - 1, 3)
    return (f"-{k} SD oversold", "green") if z < 0 else (f"+{k} SD overbought", "red")


def fit(history):
    """history: daily closes (Series indexed by date, positive). Returns the line and its fit."""
    s = history[history > 0].sort_index()
    t = (s.index - s.index[0]).days.values.astype(float)
    y = np.log(s.values)
    slope, intercept = np.polyfit(t, y, 1)
    resid = y - (intercept + slope * t)
    sd = float(resid.std())
    r2 = float(1 - resid.var() / y.var()) if y.var() > 0 else 0.0
    return {"start": s.index[0], "end": s.index[-1], "intercept": float(intercept), "slope": float(slope), "sd": sd, "r2": r2, "n": len(s)}


def reading(history, cfg, price_now=None, today=None):
    """Everything the card needs. price_now: live price (else the last close). today: date the fair value is for."""
    v = cfg["valuations"]
    s = history[history > 0].sort_index() if len(history) else history
    if len(s) < 2:
        return {"status": "none", "text": "no data"}
    today = pd.Timestamp(today).normalize() if today is not None else s.index[-1]
    years = (s.index[-1] - s.index[0]).days / 365.25
    months = int(round(years * 12))
    base = {"history_from": str(s.index[0])[:10], "years": round(years, 2), "months": months, "label": LABEL, "drift_note": DRIFT}
    if years < v["min_years_dial"]:
        return {**base, "status": "too_little", "text": f"too little history ({months} months)"}
    f = fit(s)
    last = float(s.iloc[-1])
    p = float(price_now) if price_now and abs(float(price_now) / last - 1) <= v["live_max_gap"] else last
    t = (today - f["start"]).days
    fair = math.exp(f["intercept"] + f["slope"] * t)
    z = (math.log(p) - math.log(fair)) / f["sd"] if f["sd"] > 0 else 0.0
    name, colour = zone(z)
    out = {**base, "status": "ok", "z": round(z, 3), "zone": name, "colour": colour, "price": p, "fair_value": fair,
           "growth_per_year": math.exp(f["slope"] * 365) - 1, "r2": round(f["r2"], 3), "sd_log": f["sd"],
           "bands": {f"{k:+d}": fair * math.exp(k * f["sd"]) for k in (-3, -2, -1, 1, 2, 3)},   # keys "+1", "-2"... (JSON-safe)
           "price_is_live": p != last, "last_close_date": str(s.index[-1])[:10]}
    notes = []
    if years < v["min_years_confident"]:
        out["status"] = "greyed"
        notes.append(f"short history, low confidence ({months} months used)")
    if f["r2"] < v["min_r_squared"]:
        out["status"] = "greyed"
        notes.append(NO_FIT)
    out["warnings"] = notes
    return out


STRETCH_LABEL = "Compared with its own recent trend, not a fair value"


def stretch(history, cfg, price_now=None):
    """Stretch from trend: log(price / 200-day moving average), as a z-score against the coin's own
    history of the same measure. Needs at least 365 days of the measure."""
    v = cfg["valuations"]
    s = history[history > 0].sort_index() if len(history) else history
    n = v["stretch_ma_days"]
    base = {"label": STRETCH_LABEL}
    if len(s) < n + 1:
        return {**base, "status": "too_little", "text": "too little history", "days": 0}
    ma = s.rolling(n).mean()
    m = np.log(s / ma).dropna()
    if len(m) < v["stretch_min_days"]:
        return {**base, "status": "too_little", "text": "too little history", "days": len(m)}
    last = float(s.iloc[-1])
    p = float(price_now) if price_now and abs(float(price_now) / last - 1) <= v["live_max_gap"] else last
    now = math.log(p / float(ma.iloc[-1]))
    sd = float(m.std())
    z = (now - float(m.mean())) / sd if sd > 0 else 0.0
    name, colour = zone(z)
    return {**base, "status": "ok", "z": round(z, 3), "zone": name, "colour": colour, "ratio": p / float(ma.iloc[-1]),
            "ma": float(ma.iloc[-1]), "days": len(m), "typical_ratio": math.exp(float(m.mean()))}


REVENUE_LABEL = "Fully diluted value against the last year of fees, compared with its own history only"
APPROX = "approximate: past supply estimated"


def revenue(price, fees, cfg, rc, supply=None, circulating=None, total=None, price_now=None):
    """Price against revenue: fully diluted value / the last 365 days of fees, as a z-score of its log
    against the coin's own history of the same multiple.
    rc: the coin's revenue settings. supply: Ether's supply history when rc["supply"] == "history"."""
    v = cfg["valuations"]
    n, need = v["revenue_days"], v["revenue_min_days"]
    out = {"label": REVENUE_LABEL, "approximate": bool(rc.get("approximate")), "note": rc.get("note", "")}
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
    """One reading per coin, in the configured order. view: hub.signals.core.View."""
    out = []
    for c in cfg["valuations"]["coins"]:
        r = reading(view.s(c["history"]), cfg, price_now=view.live(c["live"]), today=view.now.normalize())
        st = stretch(view.s(c["history"]), cfg, price_now=view.live(c["live"]))
        rv = None
        if c.get("revenue"):
            rc = c["revenue"]
            last = lambda sid: (float(view.s(sid).iloc[-1]) if len(view.s(sid)) else None)
            rv = revenue(view.s(c["history"]), view.s(rc["fees"]), cfg, rc,
                         supply=view.s(rc["supply_series"]) if rc.get("supply_series") else None,
                         circulating=last(f"SUP_CIRC_{c['sym']}"), total=last(f"SUP_TOTAL_{c['sym']}"),
                         price_now=view.live(c["live"]))
        out.append({"sym": c["sym"], "name": c["name"], **r, "stretch": st, "revenue": rv, "methods": METHODS})
    return out
