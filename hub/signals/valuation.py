"""Log-regression channel, as used by Raoul Pal and Real Vision. Pure functions; no network.

Fit a straight line to the natural log of the daily close against calendar days, over the coin's
full available history. Fair value is the line's value today. The reading is
(log price - log fair value) / standard deviation of the residuals (population form).
Context only: these readings never enter the buy / hold reading, the backdrop or any push.
"""
import math

import numpy as np
import pandas as pd

ZONES = ["-3 SD oversold", "-2 SD oversold", "-1 SD oversold", "fair value", "+1 SD overbought", "+2 SD overbought", "+3 SD overbought"]
LABEL = "Trend-based estimate. Assumes past growth continues."
DRIFT = "A constant-growth line drifts toward oversold as a coin's growth slows; read with care for older coins."
NO_FIT = "the line does not fit this coin's history; reading not meaningful"


def zone(z):
    """Seven zones: within 1 SD is fair value; 1 to 2 SD is the first band, 2 to 3 the second, beyond 3 the third.
    An exact edge belongs to the zone nearer fair value (exactly -1 SD is 'fair value', exactly -2 SD is '-1 SD oversold')."""
    if abs(z) <= 1:
        return "fair value", "amber"
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


def all_coins(view, cfg):
    """One reading per coin, in the configured order. view: hub.signals.core.View."""
    out = []
    for c in cfg["valuations"]["coins"]:
        r = reading(view.s(c["history"]), cfg, price_now=view.live(c["live"]), today=view.now.normalize())
        st = stretch(view.s(c["history"]), cfg, price_now=view.live(c["live"]))
        out.append({"sym": c["sym"], "name": c["name"], **r, "stretch": st})
    return out
