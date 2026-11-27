"""Quality score (reports/18, section 4, with the owner's change of 27 Nov). Pure functions: no network.

Three parts, each "good", "neutral", "bad" or None (no data). No data is never bad.
- revenue: last 90 days against the 90 before. Two marks: fixed (+20% / -20%) and relative (rank against every
  scanned coin with data: top third good, bottom third bad). The relative mark counts toward passing.
- dilution: circulating supply growth over a year (<2% good, >10% bad); also <50% of fully diluted circulating is bad.
- accrual: share of revenue going to holders over 90 days (>=50% good, <10% bad).
Passes = no part bad, and at least one part with data.
"""
import pandas as pd


def revenue_growth(daily, days, min_usd):
    """daily: pandas Series of daily revenue (USD). Returns (growth, last 90-day total) or (None, total)."""
    if daily is None or len(daily) < 2 * days:
        return None, None
    d = daily.sort_index()
    last, prev = float(d.iloc[-days:].sum()), float(d.iloc[-2 * days:-days].sum())
    if last < min_usd and prev < min_usd:
        return None, last
    if prev <= 0:
        return None, last
    return last / prev - 1, last


def fixed_mark(g, c):
    if g is None:
        return None
    g = round(g, 9)                       # -20% exactly is "down 20% or more", whatever the rounding
    return "good" if g >= c["revenue_good"] else "bad" if g <= c["revenue_bad"] else "neutral"


def relative_marks(growths):
    """{coin: growth or None} -> {coin: (mark, rank, of)}; rank 1 = best. Top third good, bottom third bad."""
    have = sorted(((g, k) for k, g in growths.items() if g is not None), reverse=True)
    n = len(have)
    out = {k: (None, None, n) for k, g in growths.items() if g is None}
    for i, (g, k) in enumerate(have):
        third = i * 3 // n if n else 1
        out[k] = ({0: "good", 1: "neutral", 2: "bad"}[third] if n >= 3 else "neutral", i + 1, n)
    return out


def median(values):
    v = sorted(x for x in values if x is not None)
    if not v:
        return None
    m = len(v) // 2
    return v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2


def dilution(supply, circulating, fully_diluted_supply, c):
    """supply: Series of circulating supply over the last year. Returns (mark, growth, float share)."""
    growth = None
    if supply is not None and len(supply.dropna()) >= 300:
        s = supply.dropna().sort_index()
        first = s[s.index <= s.index[-1] - pd.Timedelta(days=360)]
        if len(first) and float(first.iloc[-1]) > 0:
            growth = float(s.iloc[-1]) / float(first.iloc[-1]) - 1
    share = (circulating / fully_diluted_supply) if circulating and fully_diluted_supply else None
    if growth is None and share is None:
        return None, None, None
    if (growth is not None and growth > c["dilution_bad"]) or (share is not None and share < c["float_bad"]):
        mark = "bad"
    elif growth is not None and growth < c["dilution_good"]:
        mark = "good"
    else:
        mark = "neutral"
    return mark, growth, share


def accrual(revenue_90d, holders_90d, c):
    if not revenue_90d or holders_90d is None or revenue_90d <= 0:
        return None, None
    share = max(0.0, min(1.0, holders_90d / revenue_90d))
    return ("good" if share >= c["accrual_good"] else "bad" if share < c["accrual_bad"] else "neutral"), share


def passes(parts):
    scored = [m for m in parts if m is not None]
    return bool(scored) and "bad" not in scored, len(scored)
