"""Every dial, as a pure function: (view, config, previous colour) -> Raw.

One colour rule for all of them: green = supports buying crypto, amber = neutral,
red = argues against. Band edges live in config/thresholds.yaml.
"""
import pandas as pd

from hub.signals.core import (A, G, R, Raw, band, bn, change, dxy_from_ecb, finished_month_ends, gauge,
                              level_state, money, pct_change_days, percentile_of_last, value_days_ago,
                              weekly_closes, weekly_state)

DIALS = []  # filled by @dial, in dashboard order


def dial(id, group, title, confirm="run"):
    def deco(fn):
        DIALS.append({"id": id, "group": group, "title": title, "fn": fn, "confirm": confirm})
        return fn
    return deco


# ======================================================================= helpers
def realised_price(v, c):
    """(value, source label, date). Bitview first, Coin Metrics next, fixed level last."""
    for sid, label in (("BV_REALIZED_PRICE", "Bitview"), ("CM_REALIZED_PRICE", "Coin Metrics")):
        s = v.s(sid)
        if len(s):
            return float(s.iloc[-1]), label, s.index[-1]
    return float(c["levels"]["realised_price"]), "fixed level", pd.Timestamp(c["levels"]["levels_as_of"])


def btc_weekly(v):
    return weekly_closes(v.s("BTCUSD"))


def weekly_levels(v, c):
    """Break and reclaim lines. Returns (break, reclaim, latest break, latest reclaim, dynamic break, dynamic reclaim).
    Live: the fixed levels colour the dial. Replays: the lines follow short-term holder realised price."""
    dyn, sth = c["dynamic_levels"], v.s("BV_STH_REALIZED_PRICE")
    d_rec = float(sth.iloc[-1]) * dyn["reclaim_x_sth"] if len(sth) else None
    d_brk = float(sth.iloc[-1]) * dyn["break_x_sth"] if len(sth) else None
    if dyn["use_for_colours"]:
        return sth * dyn["break_x_sth"], sth * dyn["reclaim_x_sth"], d_brk, d_rec, d_brk, d_rec
    brk, rec = float(c["levels"]["btc_break"]), float(c["levels"]["btc_reclaim"])
    return brk, rec, brk, rec, d_brk, d_rec


def dxy(v):
    cols = [v.s(f"ECB_{k}") for k in ("USD", "JPY", "GBP", "CAD", "SEK", "CHF")]
    if any(len(x) == 0 for x in cols):
        return pd.Series(dtype=float)
    df = pd.concat(cols, axis=1, join="inner").dropna()
    df.columns = ["usd", "jpy", "gbp", "cad", "sek", "chf"]
    return dxy_from_ecb(df.usd, df.jpy, df.gbp, df.cad, df.sek, df.chf)


def dollar_state(v, c):
    """Shared by the dollar dial and the dollar-reversal dial."""
    d, s = c["dollar"], dxy(v)
    if len(s) < d["rising_days"] + 2:
        return None
    below, flips, last_flip = level_state(s, d["level"], d["margin"], d["fixings"])
    below100, _, _ = level_state(s, d["confirm_level"], d["margin"], d["fixings"])
    rising = bool(s.iloc[-1] > s.iloc[-1 - d["rising_days"]])
    return {"value": float(s.iloc[-1]), "obs": s.index[-1], "below": below, "below100": below100,
            "rising": rising, "last_flip": last_flip}


def margin_growth(v):
    s = v.s("MARGIN_DEBT")
    if len(s):
        s = s.asfreq("ME")   # a missing month becomes a gap instead of silently stretching "3 months"
    return ((s / s.shift(3)) ** 4 - 1).dropna()


def margin_fired_latched(v, c):
    """True when the margin-debt signal fired in any of the last `regime_latch_months` months."""
    m, ann = c["margin_debt"], margin_growth(v)
    for i in range(1, min(m["regime_latch_months"], len(ann)) + 1):
        upto = ann.iloc[:len(ann) - i + 1]
        if upto.iloc[-1] < m["now_below"] and upto.iloc[-m["within_months"]:].max() > m["fire_above"]:
            return True
    return False


def hike_spread(v):
    df = pd.concat([v.s("DGS2"), v.s("DFF")], axis=1, join="inner").dropna()
    return df.iloc[:, 0] - df.iloc[:, 1] if len(df) else pd.Series(dtype=float)


def stable_change(s, days):
    x = pct_change_days(s, days)
    return None if x is None else x * 100


# ======================================================================= A. Is it cheap?
@dial("btc_price", "A", "Bitcoin price")
def btc_price(v, c, prev=None):
    price, pdate = v.latest("BTCUSD")
    if price is None:
        return Raw()
    rp, rp_src, rp_date = realised_price(v, c)
    dyn = c["dynamic_levels"]
    dyn_zone = rp * dyn["value_zone_x_realised"]
    zone = dyn_zone if dyn["use_for_colours"] else float(c["levels"]["btc_value_zone"])
    froth = rp * c["btc_price"]["froth_multiple"]
    buf = c["general"]["price_buffer"]
    col = band(price, [zone, froth], [G, A, R], prev, buf, rel=True)
    lth, sth = v.s("BV_LTH_REALIZED_PRICE"), v.s("BV_STH_REALIZED_PRICE")
    bv, cm = v.s("BV_REALIZED_PRICE"), v.s("CM_REALIZED_PRICE")
    notes = []
    if len(bv) and len(cm) and abs(bv.iloc[-1] / cm.iloc[-1] - 1) > c["general"]["cross_check_gap"]:
        notes.append(f"Sources disagree on realised price: Bitview {money(bv.iloc[-1])}, Coin Metrics {money(cm.iloc[-1])}")
    if rp_src == "fixed level":
        notes.append(f"Live realised price unavailable; using the fixed level from {c['levels']['levels_as_of']}")
    moves = {G: f"Turns amber above {money(zone * (1 + buf))}.",
             A: f"Turns green at or below {money(zone * (1 - buf))}; red above {money(froth * (1 + buf))}.",
             R: f"Turns amber below {money(froth * (1 - buf))}."}.get(col, "")
    drift = "" if dyn["use_for_colours"] else f" · value zone {money(zone)} fixed, {money(dyn_zone)} at 1.10x realised"
    return Raw(price, col, f"{money(price)} · {price / rp:.2f}x realised price{drift}", moves, pdate,
               gauge(rp * 0.7, froth * 1.15, [zone, froth], [G, A, R]),
               {"realised_price": rp, "realised_price_source": rp_src, "realised_price_date": str(rp_date)[:10],
                "ratio_to_realised": price / rp, "value_zone": zone, "dynamic_value_zone": dyn_zone, "froth_level": froth,
                "lth_cost": float(lth.iloc[-1]) if len(lth) else float(c["levels"]["lth_cost"]),
                "sth_cost": float(sth.iloc[-1]) if len(sth) else float(c["levels"]["sth_cost"]), "notes": notes})


@dial("btc_weekly", "A", "Bitcoin weekly close")
def btc_weekly_dial(v, c, prev=None):
    w = btc_weekly(v)
    brk_l, rec_l, brk, rec, d_brk, d_rec = weekly_levels(v, c)
    if not len(w) or brk is None:
        return Raw()
    in_break, _ = weekly_state(w, brk_l, rec_l)
    last = float(w.iloc[-1])
    col = R if in_break else (G if last > rec else A)
    moves = (f"Stays red until a weekly close above {money(rec)}." if in_break
             else f"Turns red on a weekly close below {money(brk)}.")
    drift = "" if (c["dynamic_levels"]["use_for_colours"] or d_rec is None) else \
        f" · lines {money(brk)} / {money(rec)} fixed, {money(d_brk)} / {money(d_rec)} from short-term holder cost"
    return Raw(last, col, f"{money(last)} on {w.index[-1]:%d %b}" + (" · break in force" if in_break else "") + drift,
               moves, w.index[-1], gauge(brk * 0.7, rec * 1.3, [brk, rec], [R, A, G]),
               {"break_in_force": in_break, "break_level": brk, "reclaim_level": rec,
                "dynamic_break_level": d_brk, "dynamic_reclaim_level": d_rec})


@dial("weekly_move", "A", "Size of latest weekly move")
def weekly_move(v, c, prev=None):
    w, k = btc_weekly(v), c["weekly_move"]
    r = w.pct_change().dropna()
    if len(r) < k["lookback_weeks"] + 1:
        return Raw()
    sd = r.iloc[-1 - k["lookback_weeks"]:-1].std()
    z = float(r.iloc[-1] / sd) if sd else None
    col = band(z, [k["green_at_or_below"], k["red_at_or_above"]], [G, A, R], right=[True, False])
    return Raw(z, col, f"{z:+.1f} standard deviations ({r.iloc[-1]:+.1%} week)",
               "Green on a weekly fall of 2 standard deviations or more; red on a rise that large.", r.index[-1],
               gauge(-4, 4, [k["green_at_or_below"], k["red_at_or_above"]], [G, A, R]), {"weekly_return": float(r.iloc[-1])})


@dial("lth_sopr", "A", "Long-term holder SOPR (30-day)")
def lth_sopr(v, c, prev=None):
    s, w, k = v.s("BV_LTH_SOPR_1M"), v.s("BV_LTH_SOPR_1W"), c["lth_sopr"]
    if not len(s):
        return Raw()
    x = float(s.iloc[-1])
    wk = float(w.iloc[-1]) if len(w) else None
    col = band(x, [k["green_at_or_below"], k["red_above"]], [G, A, R])
    return Raw(x, col, f"{x:.2f} · 7-day {wk:.2f}" if wk is not None else f"{x:.2f}",
               f"Green at or below {k['green_at_or_below']}: long-term holders selling at a loss as at past cycle lows.",
               s.index[-1], gauge(0.3, 4.0, [k["green_at_or_below"], k["red_above"]], [G, A, R]), {"sopr_7d": wk})


@dial("net_loss", "A", "Net realised losses")
def net_loss(v, c, prev=None):
    df = pd.concat([v.s("BV_NET_PNL_1M"), v.s("BV_REALIZED_CAP")], axis=1, join="inner").dropna()
    k = c["net_loss"]
    if len(df) < k["min_history_days"]:
        return Raw()
    df = df[df.iloc[:, 1] > 0]
    share = -df.iloc[:, 0] / df.iloc[:, 1] * 100  # positive = net losses, as % of realised cap
    x, pct = float(share.iloc[-1]), percentile_of_last(share)
    col = G if pct >= k["green_percentile"] else A
    feb = -float(df.iloc[-1, 0]) / float(c["levels"]["feb_2026_net_loss_peak"])
    what = f"net loss {x:.2f}% of realised cap" if x > 0 else f"net profit {-x:.2f}% of realised cap"
    return Raw(pct, col, f"{what} · {pct:.0f}th percentile",
               f"Green at or above the {k['green_percentile']}th percentile of all history: losses spiking as in a capitulation.",
               df.index[-1], gauge(0, 100, [k["green_percentile"]], [A, G]),
               {"net_loss_pct_of_realised_cap": x, "share_of_feb_2026_peak": feb})


@dial("btc_ndx", "A", "Bitcoin against the Nasdaq-100")
def btc_ndx(v, c, prev=None):
    k, ndx, btc = c["btc_ndx"], v.s("NASDAQ100"), v.s("BTCUSD")
    df = pd.concat([btc, ndx], axis=1, join="inner").dropna()
    if len(df) < k["average_days"]:
        return Raw()
    ratio = df.iloc[:, 0] / df.iloc[:, 1]
    dev = float(ratio.iloc[-1] / ratio.iloc[-k["average_days"]:].mean() - 1)
    col = band(dev, [k["red_below"], k["green_above"]], [R, A, G], right=[True, False])
    return Raw(dev, col, f"ratio {ratio.iloc[-1]:.2f} · {dev:+.1%} vs its 100-day average",
               "Green when Bitcoin is 2% or more above its 100-day trend against tech stocks; red when 2% or more below.",
               df.index[-1], gauge(-0.3, 0.3, [k["red_below"], k["green_above"]], [R, A, G]), {"ratio": float(ratio.iloc[-1])})


def alt_value_ratio(v):
    tot, dom, st = v.with_live("CG_TOTAL_MCAP"), v.with_live("CG_BTC_DOM"), v.with_live("STABLE_ALL")
    df = pd.concat([tot, dom], axis=1, join="inner").dropna()
    if not len(df) or not len(st):
        return pd.Series(dtype=float)
    stable = st.reindex(df.index.union(st.index)).ffill().reindex(df.index)
    btc = df.iloc[:, 0] * df.iloc[:, 1] / 100
    return ((df.iloc[:, 0] - btc - stable) / btc).dropna()


@dial("alt_value", "A", "Altcoin value against Bitcoin")
def alt_value(v, c, prev=None):
    k, r = c["alt_value"], alt_value_ratio(v)
    if not len(r):
        return Raw()
    x = float(r.iloc[-1])
    ch = pct_change_days(r, k["change_days"])
    g = gauge(-0.3, 0.3, [k["red_at_or_below"], k["green_at_or_above"]], [R, A, G])
    if ch is None:
        days = (r.index[-1] - r.index[0]).days
        return Raw(None, None, f"{x:.2f}x Bitcoin's value · collecting history ({days} of {k['change_days']} days)",
                   "No colour until the hub has 30 days of its own history (no free history exists).", r.index[-1], g, {"ratio": x})
    col = band(ch, [k["red_at_or_below"], k["green_at_or_above"]], [R, A, G], right=[True, False])
    return Raw(ch, col, f"{x:.2f}x Bitcoin's value · {ch:+.1%} in 30 days",
               "Green when altcoins gain 5% or more against Bitcoin in 30 days; red when they lose that much.", r.index[-1], g, {"ratio": x})


@dial("alt_watch", "A", "Altcoin watchlist in Bitcoin terms")
def alt_watch(v, c, prev=None):
    k, btc = c["alt_watch"], v.with_live("BTCUSD")
    each, last = {}, None
    for sid in k["coins"]:
        s = v.with_live(sid)
        df = pd.concat([s, btc], axis=1, join="inner").dropna()
        if len(df) < 2:
            continue
        ch = pct_change_days(df.iloc[:, 0] / df.iloc[:, 1], k["change_days"])
        if ch is not None:
            each[sid.replace("USD", "")] = ch
            last = df.index[-1]
    if not each:
        return Raw()
    x = sum(each.values()) / len(each)
    col = band(x, [k["red_at_or_below"], k["green_at_or_above"]], [R, A, G], right=[True, False])
    return Raw(x, col, f"{x:+.1%} in 30 days · " + ", ".join(f"{n} {ch:+.0%}" for n, ch in each.items()),
               "Green when the five coins gain 10% or more against Bitcoin in 30 days; red when they lose that much.",
               last, gauge(-0.4, 0.4, [k["red_at_or_below"], k["green_at_or_above"]], [R, A, G]), {"coins": each})


# ======================================================================= B. Is stress still building?
@dial("margin_debt", "B", "Margin debt growth")
def margin_debt(v, c, prev=None):
    m, ann = c["margin_debt"], margin_growth(v)
    if len(ann) < m["within_months"]:
        return Raw()
    cur, peak = float(ann.iloc[-1]), float(ann.iloc[-m["within_months"]:].max())
    col = G if peak <= m["fire_above"] else (R if cur < m["now_below"] else A)
    return Raw(cur * 100, col, f"{cur:+.1%} annualised · 12-month peak {peak:+.0%}",
               "Red when growth drops below 0 within 12 months of a reading above +100%.", ann.index[-1],
               gauge(-60, 160, [0], [R, A] if peak > m["fire_above"] else [G, G]),
               {"peak_12m": peak, "fired_latched": margin_fired_latched(v, c)})


@dial("sofr_iorb", "B", "SOFR minus IORB")
def sofr_iorb(v, c, prev=None):
    k = c["sofr_iorb"]
    iorb = v.s("IORB").combine_first(v.s("IOER"))
    df = pd.concat([v.s("SOFR"), iorb], axis=1, join="inner").dropna()
    if len(df) < k["median_days"]:
        return Raw()
    x = float(((df.iloc[:, 0] - df.iloc[:, 1]) * 100).iloc[-k["median_days"]:].median())
    col = band(x, [k["green_at_or_below"], k["red_above"]], [G, A, R])
    return Raw(x, col, f"{x:+.0f}bp (5-day median)", "Red above +5bp: cash is getting scarce in money markets.",
               df.index[-1], gauge(-15, 20, [k["green_at_or_below"], k["red_above"]], [G, A, R]))


def _yield_change(v, c, sid, key, label, extra_text=""):
    k, s = c[key], v.s(sid)
    x = change(s, k["change_days"])
    if x is None:
        return Raw()
    x *= 100
    col = band(x, [k["green_at_or_below"], k["red_at_or_above"]], [G, A, R], right=[True, False])
    return Raw(x, col, f"{x:+.0f}bp in 20 days · now {s.iloc[-1]:.2f}%{extra_text}",
               f"Green if the {label} falls {abs(k['green_at_or_below']):.0f}bp or more in 20 trading days; red if it rises {k['red_at_or_above']:.0f}bp or more.",
               s.index[-1], gauge(-75, 75, [k["green_at_or_below"], k["red_at_or_above"]], [G, A, R]), {"level": float(s.iloc[-1])})


@dial("y2_chg", "B", "2-year Treasury yield")
def y2_chg(v, c, prev=None):
    return _yield_change(v, c, "DGS2", "yields", "2-year yield")


@dial("y10_chg", "B", "10-year Treasury yield")
def y10_chg(v, c, prev=None):
    curve = v.s("T10Y2Y")
    return _yield_change(v, c, "DGS10", "yields", "10-year yield", f" · curve {curve.iloc[-1]:+.2f}" if len(curve) else "")


def _hike(v, c, key):
    k, sp = c[key], hike_spread(v)
    x = change(sp, k["change_days"])
    if x is None:
        return Raw()
    x *= 100
    col = band(x, [k["green_at_or_below"], k["red_at_or_above"]], [G, A, R], right=[True, False])
    lo, hi = v.s("DFEDTARL"), v.s("DFEDTARU")
    tgt = f" · Fed target {lo.iloc[-1]:.2f}-{hi.iloc[-1]:.2f}%" if len(lo) and len(hi) else ""
    return Raw(x, col, f"{x:+.0f}bp in 20 days · 2-year is {sp.iloc[-1] * 100:+.0f}bp vs Fed funds{tgt}",
               f"Green if the gap falls {abs(k['green_at_or_below']):.0f}bp or more in 20 trading days (hikes priced out); red if it rises {k['red_at_or_above']:.0f}bp or more.",
               sp.index[-1], gauge(-60, 60, [k["green_at_or_below"], k["red_at_or_above"]], [G, A, R]), {"level_bp": float(sp.iloc[-1] * 100)})


@dial("hike_pricing", "B", "Rate-hike pricing")
def hike_pricing(v, c, prev=None):
    return _hike(v, c, "hike_pricing")


@dial("cpi_mom", "B", "Inflation (CPI, month on month)")
def cpi_mom(v, c, prev=None):
    k, s = c["cpi"], v.s("CPIAUCSL")
    if len(s) < 2 or (s.index[-1].to_period("M") - s.index[-2].to_period("M")).n != 1:
        return Raw(text="no data (latest two months not consecutive)") if len(s) >= 2 else Raw()
    x = round(float(s.iloc[-1] / s.iloc[-2] - 1) * 100, 1)
    col = band(x, [k["green_at_or_below"], k["red_at_or_above"]], [G, A, R], right=[True, False])
    return Raw(x, col, f"{x:+.1f}% in {s.index[-1]:%b %Y}", "Green at 0.2% or less; red at 0.4% or more.", s.index[-1],
               gauge(-0.2, 0.8, [k["green_at_or_below"] + 0.05, k["red_at_or_above"] - 0.05], [G, A, R]))


@dial("breakeven", "B", "5-year breakeven inflation")
def breakeven(v, c, prev=None):
    k, s = c["breakeven"], v.s("T5YIE")
    if not len(s):
        return Raw()
    x = float(s.iloc[-1])
    return Raw(x, band(x, [k["green_at_or_below"], k["red_above"]], [G, A, R]), f"{x:.2f}%",
               "Red above 2.7%: markets expect inflation well over the Fed's target.", s.index[-1],
               gauge(1.5, 3.5, [k["green_at_or_below"], k["red_above"]], [G, A, R]))


def liquidity_totals(v):
    """(total now, total a year earlier, oldest weekly date), in millions of dollars: Fed + ECB +
    Bank of Japan assets and US M2. Each part is compared with its OWN value 365 days before its
    own latest figure, so a part that is published late does not shorten the year."""
    def pair(sid):
        s = v.s(sid)
        if not len(s):
            return None
        old = s[s.index <= s.index[-1] - pd.Timedelta(days=365)]
        return (float(s.iloc[-1]), float(old.iloc[-1]), s.index[-1]) if len(old) else None
    parts = {k: pair(k) for k in ("WALCL", "ECBASSETSW", "JPNASSETS", "M2SL", "ECB_USD", "ECB_JPY")}
    if any(p is None for p in parts.values()):
        return None
    usd, jpy = parts["ECB_USD"], parts["ECB_JPY"]

    def total(i):
        return (parts["WALCL"][i] + parts["ECBASSETSW"][i] * usd[i] + parts["JPNASSETS"][i] * 100 / (jpy[i] / usd[i])
                + parts["M2SL"][i] * 1000)
    return total(0), total(1), min(parts["WALCL"][2], parts["ECBASSETSW"][2])


@dial("liquidity", "B", "Global liquidity proxy")
def liquidity(v, c, prev=None):
    k, tot = c["liquidity"], liquidity_totals(v)
    if not tot:
        return Raw()
    now_, then, obs = tot
    x = (now_ / then - 1) * 100
    col = band(x, [k["red_below"], k["green_at_or_above"]], [R, A, G], right=False)
    return Raw(x, col, f"{x:+.1f}% year on year · ${now_ / 1e6:,.1f}tn (proxy)",
               "Green at +5% a year or more; red when shrinking. A proxy: not Coutts' own index.", obs,
               gauge(-10, 20, [k["red_below"], k["green_at_or_above"]], [R, A, G]), {"total_usd_millions": now_})


def _dollar(v, c, turn):
    st, d = dollar_state(v, c), c["dollar"]
    if st is None:
        return Raw()
    col = G if st["below"] else (R if st["rising"] else A)
    pub = v.s("DXY_PUB")
    chk = f" · published close {pub.iloc[-1]:.2f} ({pub.index[-1]:%d %b})" if len(pub) else ""
    tag = " · confirmed below 100" if st["below100"] else ""
    text = f"{st['value']:.2f} (ECB fixing, not the New York close){tag}{chk}"
    moves = (f"Turns amber or red after two fixings at or above {d['level'] + d['margin']:.1f}." if st["below"]
             else f"Turns green after two fixings in a row at or below {d['level'] - d['margin']:.1f}.")
    return Raw(st["value"], col, text, moves, st["obs"], gauge(95, 110, [d["confirm_level"], d["level"]], [G, G, R if st["rising"] else A]),
               {"below_level": st["below"], "confirmed": st["below100"], "rising": st["rising"],
                "last_reversal": str(st["last_flip"])[:10] if st["last_flip"] is not None else None})


@dial("dollar", "B", "Dollar index")
def dollar(v, c, prev=None):
    return _dollar(v, c, False)


@dial("sp500", "B", "S&P 500")
def sp500(v, c, prev=None):
    k, s = c["sp500"], v.s("SP500")
    me = finished_month_ends(s)
    if len(me) < k["average_months"] or len(s) < 200:
        return Raw()
    avg = float(me.iloc[-k["average_months"]:].mean())
    last, last_me = float(s.iloc[-1]), float(me.iloc[-1])
    fall = 1 - last / float(s[s.index > s.index[-1] - pd.Timedelta(days=365)].max())
    month_break = last_me < avg
    fall_col = band(fall, [k["amber_fall"], k["red_fall"]], [G, A, R], right=False)
    col = R if (month_break or fall_col == R) else (A if (last < avg or fall_col == A) else G)
    txt = f"{last:,.0f} · {fall:.1%} below 1-year high · 10-month average {avg:,.0f}"
    same_day = None
    spy = v.s("SPY")
    if len(spy) and spy.index[-1] > s.index[-1] and s.index[-1] in spy.index:
        # FRED posts the index a day late. Nasdaq does not carry the index itself, so the same-day
        # figure is FRED's last close moved by the SPY fund's change since then. Display only.
        same_day = last * float(spy.iloc[-1] / spy[s.index[-1]])
        txt += f" · unofficial, same day ({spy.index[-1]:%d %b}): about {same_day:,.0f}, from the SPY fund"
    if month_break:
        txt += f" · {me.index[-1].strftime('%b')} closed below it"
    return Raw(last, col, txt, "Red on a finished month-end close below the 10-month average, or a 20% fall from the 1-year high.",
               s.index[-1], gauge(avg * 0.8, avg * 1.2, [avg], [A, G]),
               {"month_end_break": month_break, "ten_month_average": avg, "fall_from_high": fall,
                "last_month_end": float(last_me), "last_month": str(me.index[-1]), "same_day_estimate": same_day})


def funding_daily(v):
    cols = [x for x in (v.s("FUND_BINANCE"), v.s("FUND_BYBIT"), v.s("FUND_OKX")) if len(x)]
    return pd.concat(cols, axis=1).mean(axis=1).dropna() if cols else pd.Series(dtype=float)


@dial("funding", "B", "Bitcoin funding rate")
def funding(v, c, prev=None):
    k, f = c["funding"], funding_daily(v)
    if len(f) < k["average_days"]:
        return Raw()
    w = f.iloc[-k["average_days"]:]
    x = float(w.mean() * k["intervals_per_day"] * 365)
    neg = int((w < 0).sum())
    col = band(x, [0, k["red_at_or_above"]], [G, A, R], right=False)
    return Raw(x, col, f"{x:+.1f}% a year (30-day average) · negative on {neg} of 30 days",
               "Green when the average is negative (shorts paying); red at 30% or more (crowded longs).", f.index[-1],
               gauge(-20, 60, [0, k["red_at_or_above"]], [G, A, R]), {"days_negative": neg})


@dial("alt_oi", "B", "Altcoin open interest against Bitcoin's")
def alt_oi(v, c, prev=None):
    k = c["alt_oi"]
    df = pd.concat([v.s("OI_ALT"), v.s("OI_BTC")], axis=1, join="inner").dropna()
    df = df[df.iloc[:, 1] > 0]
    if len(df) < k["min_history_days"]:
        return Raw()
    r = df.iloc[:, 0] / df.iloc[:, 1]
    pct = percentile_of_last(r)
    col = band(pct, [k["green_below"], k["red_at_or_above"]], [G, A, R], right=False)
    return Raw(pct, col, f"{r.iloc[-1]:.2f}x · {pct:.0f}th percentile since {r.index[0]:%b %Y}",
               "Green below its 50th percentile; red at or above the 90th (altcoin leverage is stretched).", df.index[-1],
               gauge(0, 100, [k["green_below"], k["red_at_or_above"]], [G, A, R]), {"ratio": float(r.iloc[-1])})


@dial("stable_30d", "B", "Stablecoin supply")
def stable_30d(v, c, prev=None):
    k, s = c["stablecoins"], v.with_live("STABLE_USD")
    x = stable_change(s, k["change_days"]) if len(s) else None
    if x is None:
        return Raw()
    col = band(x, [k["red_below"], 0], [R, A, G], right=[False, True])
    return Raw(x, col, f"{x:+.1f}% in 30 days · ${s.iloc[-1] / 1e9:,.0f}bn", "Green when supply is growing; red when it shrinks more than 3% in 30 days.",
               s.index[-1], gauge(-10, 10, [k["red_below"], 0], [R, A, G]), {"supply_usd": float(s.iloc[-1])})


# ======================================================================= C. Credit-event risk
def _spread_change(v, c, key, s, name):
    k = c[key]
    x = change(s, k["change_days"])
    if x is None:
        return Raw(text="no data (needs 3 months of history)") if len(s) else Raw()
    x *= 100
    col = band(x, [k["green_below"], k["red_above"]], [G, A, R], right=[False, True])
    return Raw(x, col, f"{x:+.0f}bp in 3 months · now {s.iloc[-1]:.2f}%",
               f"Red if the {name} widens more than {k['red_above']:.0f}bp in 3 months; green below +{k['green_below']:.0f}bp.",
               s.index[-1], gauge(-k["red_above"], 2 * k["red_above"], [k["green_below"], k["red_above"]], [G, A, R]),
               {"level": float(s.iloc[-1])})


@dial("hy_spread", "C", "High-yield spread")
def hy_spread(v, c, prev=None):
    return _spread_change(v, c, "hy_spread", v.s("BAMLH0A0HYM2"), "high-yield spread")


@dial("ccc_bb", "C", "CCC spread over BB")
def ccc_bb(v, c, prev=None):
    df = pd.concat([v.s("BAMLH0A3HYC"), v.s("BAMLH0A1HYBB")], axis=1, join="inner").dropna()
    gap = df.iloc[:, 0] - df.iloc[:, 1] if len(df) else pd.Series(dtype=float)
    return _spread_change(v, c, "ccc_bb", gap, "gap between the weakest and the better junk borrowers")


@dial("bbb_spread", "C", "BBB investment-grade spread")
def bbb_spread(v, c, prev=None):
    return _spread_change(v, c, "bbb_spread", v.s("BAMLC0A4CBBB"), "BBB spread")


def _level(v, c, key, sid, fmt, moves, lo, hi):
    k, s = c[key], v.s(sid)
    if not len(s):
        return Raw()
    x = float(s.iloc[-1])
    return Raw(x, band(x, [k["green_at_or_below"], k["red_above"]], [G, A, R]), fmt.format(x), moves, s.index[-1],
               gauge(lo, hi, [k["green_at_or_below"], k["red_above"]], [G, A, R]))


@dial("nfci", "C", "Chicago Fed financial conditions")
def nfci(v, c, prev=None):
    return _level(v, c, "nfci", "NFCI", "{:+.2f}", "Red above 0: conditions tighter than average.", -1.0, 1.5)


@dial("stlfsi", "C", "St. Louis Fed stress index")
def stlfsi(v, c, prev=None):
    return _level(v, c, "stlfsi", "STLFSI4", "{:+.2f}", "Red above 1: stress one standard deviation above normal.", -1.5, 3.0)


@dial("ai_basket", "C", "AI-debt canaries against the S&P 500")
def ai_basket(v, c, prev=None):
    k, sp = c["ai_basket"], v.s("SP500")
    n = k["change_days"]
    members = {m: v.s(m) for m in k["members"]}
    lasts = [s.index[-1] for s in members.values() if len(s)] + ([sp.index[-1]] if len(sp) else [])
    if not lasts or len(sp) <= n:
        return Raw()
    d = min(lasts)
    rets = {}
    for m, s in members.items():
        s = s[s.index <= d]
        if len(s) > n:
            rets[m] = float(s.iloc[-1] / s.iloc[-1 - n] - 1)
    spd = sp[sp.index <= d]
    if not rets or len(spd) <= n:
        return Raw()
    x = (sum(rets.values()) / len(rets) - float(spd.iloc[-1] / spd.iloc[-1 - n] - 1)) * 100
    col = band(x, [k["red_below"], k["green_above"]], [R, A, G], right=[False, True])
    return Raw(x, col, f"{x:+.0f} points vs S&P 500 over 3 months · " + ", ".join(f"{m} {r:+.0%}" for m, r in rets.items()),
               "Red when the basket trails the S&P 500 by more than 25 points in 3 months.", d,
               gauge(-60, 40, [k["red_below"], k["green_above"]], [R, A, G]), {"members": rets})


def _fall_from_high(v, c, key, sid, what):
    k, s = c[key], v.s(sid)
    if len(s) < k["high_days"]:
        return Raw()
    x = float(1 - s.iloc[-1] / s.iloc[-k["high_days"]:].max()) * 100
    col = band(x, [k["green_below"], k["red_at_or_above"]], [G, A, R], right=False)
    return Raw(x, col, f"{x:.1f}% below its {what} high · {money(s.iloc[-1], 2)}",
               f"Red at {k['red_at_or_above']:.0f}% or more below the {what} high; green under {k['green_below']:.0f}%.",
               s.index[-1], gauge(0, k["red_at_or_above"] * 2, [k["green_below"], k["red_at_or_above"]], [G, A, R]))


@dial("bizd", "C", "Private credit proxy (BIZD)")
def bizd(v, c, prev=None):
    return _fall_from_high(v, c, "bizd", "BIZD", "3-month")


@dial("kre", "C", "Regional banks (KRE)")
def kre(v, c, prev=None):
    return _fall_from_high(v, c, "kre", "KRE", "1-year")


@dial("discount_window", "C", "Fed discount window borrowing")
def discount_window(v, c, prev=None):
    k, s = c["discount_window"], v.s("WLCFLPCL")
    if len(s) < 5:
        return Raw()
    lvl, rise = float(s.iloc[-1]) / 1000, float(s.iloc[-1] - s.iloc[-5]) / 1000
    by_level = band(lvl, [k["amber_level"], k["red_level"]], [G, A, R])
    by_rise = band(rise, [k["amber_rise_4w"], k["red_rise_4w"]], [G, A, R], right=False)
    col = R if R in (by_level, by_rise) else (A if A in (by_level, by_rise) else G)
    return Raw(lvl, col, f"{bn(lvl)} · {rise:+.1f}bn in 4 weeks", "Red above $25bn or a $10bn jump in 4 weeks: banks are short of cash.",
               s.index[-1], gauge(0, 50, [k["amber_level"], k["red_level"]], [G, A, R]), {"rise_4w_bn": rise})


@dial("srf", "C", "Fed standing repo facility")
def srf(v, c, prev=None):
    k, s = c["srf"], v.s("RPONTSYD")
    if len(s) < k["median_days"]:
        return Raw()
    x = float(s.iloc[-k["median_days"]:].median())
    return Raw(x, band(x, [k["green_at_or_below"], k["red_above"]], [G, A, R]), f"{bn(x)} (5-day median)",
               "Red above $10bn: dealers are leaning on the Fed for overnight cash.", s.index[-1],
               gauge(0, 20, [k["green_at_or_below"], k["red_above"]], [G, A, R]))


# ======================================================================= D. Has the turn started?
# green = the turn signal has fired, amber = not fired, red = moving the wrong way
@dial("dollar_reversal", "D", "Dollar reversal")
def dollar_reversal(v, c, prev=None):
    return _dollar(v, c, True)


@dial("front_end", "D", "Front-end easing (2-year yield)")
def front_end(v, c, prev=None):
    r = _yield_change(v, c, "DGS2", "front_end", "2-year yield")
    return r


@dial("fed_bills", "D", "Fed buying: Treasury bills")
def fed_bills(v, c, prev=None):
    return _fed_change(v, c, "fed_bills", "WSHOBL", "the Fed's T-bill holdings")


@dial("fed_reserves", "D", "Fed buying: bank reserves")
def fed_reserves(v, c, prev=None):
    return _fed_change(v, c, "fed_reserves", "WRESBAL", "bank reserves")


def _fed_change(v, c, key, sid, what):
    k, s = c[key], v.s(sid)
    x = change(s, k["weeks"])
    if x is None:
        return Raw()
    x /= 1000  # FRED reports millions; shown in billions
    col = band(x, [k["red_at_or_below"], k["green_at_or_above"]], [R, A, G], right=[True, False])
    return Raw(x, col, f"{x:+.0f}bn in 4 weeks · now {bn(s.iloc[-1] / 1000, 0)}",
               f"Green when {what} rise ${k['green_at_or_above']:.0f}bn or more in 4 weeks.", s.index[-1],
               gauge(-2 * k["green_at_or_above"], 2 * k["green_at_or_above"], [k["red_at_or_below"], k["green_at_or_above"]], [R, A, G]))


@dial("stable_turn", "D", "Stablecoin supply turning")
def stable_turn(v, c, prev=None):
    k, s = c["stablecoins"], v.with_live("STABLE_USD")
    if not len(s):
        return Raw()
    now_ = stable_change(s, k["change_days"])
    earlier = stable_change(s[s.index <= s.index[-1] - pd.Timedelta(days=k["change_days"])], k["change_days"])
    if now_ is None or earlier is None:
        return Raw()
    col = G if now_ > 0 else (A if now_ > earlier else R)
    return Raw(now_, col, f"{now_:+.1f}% in 30 days (was {earlier:+.1f}% a month ago)",
               "Green when the 30-day change turns positive; amber while negative but improving.", s.index[-1],
               gauge(-10, 10, [0], [R if col == R else A, G]), {"change_30d_ago": earlier})


@dial("weekly_reclaim", "D", "Bitcoin weekly close reclaim")
def weekly_reclaim(v, c, prev=None):
    w = btc_weekly(v)
    if not len(w):
        return Raw()
    brk_l, rec_l, brk, rec, _, _ = weekly_levels(v, c)
    if brk is None:
        return Raw()
    in_break, when = weekly_state(w, brk_l, rec_l)
    fresh = when is not None and (w.index[-1] - when).days < c["weekly_reclaim"]["green_weeks"] * 7
    col = R if in_break else (G if fresh else A)
    text = (f"break in force (weekly close {money(w.iloc[-1])})" if in_break
            else f"reclaimed on {when:%d %b %Y}" if fresh else "no break to reclaim")
    return Raw(float(w.iloc[-1]), col, text, f"Green on a weekly close back above {money(rec)} after a break.",
               w.index[-1], gauge(brk * 0.7, rec * 1.3, [brk, rec], [R, A, G]), {"reclaim_date": str(when)[:10] if when is not None else None})


@dial("buybacks", "D", "Treasury buybacks (liquidity support)")
def buybacks(v, c, prev=None):
    """Driven by the calendar: with no new operations the latest-4-weeks total falls on its own.
    So its date is "today" (a quiet spell is information, not stale data); a Treasury outage is
    caught by the source-down alert instead."""
    k, s, cm, t = c["buybacks"], v.s("BUYBACK_LS"), v.s("BUYBACK_CM"), v.now.normalize()
    if not len(s):
        return Raw()
    a = t - pd.Timedelta(days=k["recent_days"])
    b = a - pd.Timedelta(days=k["prior_days"])
    recent = float(s[(s.index > a) & (s.index <= t)].sum())
    prior = float(s[(s.index > b) & (s.index <= a)].sum()) / (k["prior_days"] / k["recent_days"])
    cmr = float(cm[(cm.index > a) & (cm.index <= t)].sum()) if len(cm) else 0.0
    g = gauge(0, 3, [k["red_at_or_below"], k["green_at_or_above"]], [R, A, G])
    last = f"last operation {s.index[-1]:%d %b %Y}"
    extra = {"recent_usd": recent, "prior_avg_usd": prior, "cash_management_usd": cmr, "last_operation": str(s.index[-1])[:10]}
    moves = f"Green when the latest 4 weeks are {k['green_at_or_above']:.1f} times the average of the prior 12 weeks (a step up)."
    if prior <= 0:   # nothing to compare with: a restart from nothing is a step up, continued silence is neutral
        col = G if recent > 0 else A
        return Raw(None, col, f"{bn(recent / 1e9)} in 4 weeks; none in the 12 weeks before · {last}", moves, t, g, extra)
    x = recent / prior
    col = band(x, [k["red_at_or_below"], k["green_at_or_above"]], [R, A, G], right=[True, False])
    return Raw(x, col, f"{x:.1f}x · {bn(recent / 1e9)} in 4 weeks vs {bn(prior / 1e9)} average · cash-management {bn(cmr / 1e9)} · {last}",
               moves, t, g, extra)


@dial("hikes_out", "D", "Rate hikes being priced out")
def hikes_out(v, c, prev=None):
    return _hike(v, c, "hikes_out")


for _d in DIALS:  # the dollar dials change only on a new ECB fixing, handled inside level_state
    if _d["id"] in ("dollar", "dollar_reversal", "btc_weekly", "weekly_reclaim"):
        _d["confirm"] = "none"
