"""Trend ratings (reports/18, section 3). An open approximation, not Alex Cole's Trend Chameleon.

On each daily close, three tests, each +1, 0 or -1:
  position   price more than 3% above (+1) / below (-1) its 50-day average
  direction  the 50-day average up (+1) / down (-1) more than 1% over 10 days
  momentum   the 20-day move beyond +/-0.75 of its usual 20-day size (from the last 90 days)
Score +3 Strong Bull, +2 Bull, -1..+1 Neutral, -2 Bear, -3 Strong Bear. A new state counts only after it has
held for 5 daily closes in a row. Pure functions: no network.
"""
import numpy as np
import pandas as pd

STATES = ["Strong Bear", "Bear", "Neutral", "Bull", "Strong Bull"]
BULLISH = {"Bull", "Strong Bull"}


def label(score):
    return {3: "Strong Bull", 2: "Bull", -2: "Bear", -3: "Strong Bear"}.get(int(score), "Neutral")


def tests(p, c):
    """The three tests for every day: DataFrame with position, direction, momentum, score."""
    p = p.dropna().astype(float)
    ma = p.rolling(c["ma_days"]).mean()
    dev = p / ma - 1
    slope = ma / ma.shift(c["slope_days"]) - 1
    r = np.log(p).diff()
    usual = r.rolling(c["momentum_vol_days"]).std() * np.sqrt(c["momentum_days"])
    z = np.log(p / p.shift(c["momentum_days"])) / usual
    sign = lambda s, band: np.sign(s).where(s.abs() > band, 0.0)  # noqa: E731
    df = pd.DataFrame({"position": sign(dev, c["position_band"]), "direction": sign(slope, c["slope_band"]),
                       "momentum": sign(z, c["momentum_band"]), "dev": dev, "slope": slope, "z": z})
    ready = ma.notna() & slope.notna() & z.notna()
    df["score"] = (df["position"] + df["direction"] + df["momentum"]).where(ready)
    return df


def settle(raw, confirm):
    """Confirmed states: a new state replaces the current one only after `confirm` closes in a row.
    Returns (states, change dates) as Series over the same index (None before the first rating)."""
    out, since = [], []
    cur, cand, n, start = None, None, 0, None
    for day, v in raw.items():
        if v is None or (isinstance(v, float) and np.isnan(v)):
            out.append(cur)
            since.append(start)
            continue
        if cur is None:
            cur, start = v, day
        elif v != cur:
            n = n + 1 if v == cand else 1
            cand = v
            if n >= confirm:
                cur, start, n = v, day, 0
        else:
            n, cand = 0, None
        out.append(cur)
        since.append(start)
    return pd.Series(out, index=raw.index, dtype=object), pd.Series(since, index=raw.index, dtype=object)


def rating(p, c):
    """The confirmed state, the date it began and today's tests, for one price series (USD or vs BTC)."""
    p = p.dropna()
    if len(p) < c["min_history_days"]:
        return {"state": None, "since": None, "why": f"too little history ({len(p)} days)"}
    t = tests(p, c)
    raw = t["score"].map(lambda s: None if pd.isna(s) else label(s))
    st, since = settle(raw, c["confirm_days"])
    last = t.iloc[-1]
    return {"state": st.iloc[-1], "since": since.iloc[-1], "raw_today": raw.iloc[-1],
            "tests": {"position": int(last["position"]), "direction": int(last["direction"]), "momentum": int(last["momentum"])},
            "detail": {"vs_average_pct": round(float(last["dev"]) * 100, 1), "average_change_pct": round(float(last["slope"]) * 100, 1),
                       "momentum": round(float(last["z"]), 2)},
            "series": st}


def dual_bull(own, vs_btc):
    return own in BULLISH and vs_btc in BULLISH
