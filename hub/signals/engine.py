"""Turns dial calculations into the published picture: colours with the
no-flapping rule, families, the regime, and the buy / hold / sell reading.

Fixed, written rules only. No machine learning and no hidden weights.
"""
import numpy as np
import pandas as pd

from hub.signals.core import A, G, R, WORD, Raw, band
from hub.signals.dials import DIALS

GROUP_NAMES = {"A": "Is it cheap?", "B": "Is stress still building?", "C": "Credit-event risk", "D": "Has the turn started?"}
FAMILY_NAMES = {"rates_dollar": "rates and dollar", "money_market": "money-market funding", "credit": "credit spreads",
                "ai_private": "AI and private credit", "banks": "banks", "crypto_leverage": "crypto leverage",
                "equities": "equities"}


# dial facts carried from run to run, so a failed calculation cannot silently clear a BREAK, FRAGILE or RISK-OFF
KEEP = ("break_in_force", "break_level", "reclaim_level", "month_end_break", "fired_latched", "ratio_to_realised")


def step(prev, raw_colour, now, confirm_runs, mode="run"):
    """No-flapping rule for one dial. Returns (new state, colour it changed from or None).

    A dial changes colour only after `confirm_runs` runs in a row away from its current
    colour; it then takes the latest colour seen. A run with no data breaks the "in a row"
    count and keeps the last colour. mode "none" is for dials whose own calculation already
    confirms (weekly closes; the dollar's two-fixing rule). The very first colour is a silent baseline.
    """
    st = {"colour": prev.get("colour"), "pending": prev.get("pending"), "count": prev.get("count", 0),
          "since": prev.get("since"), "baseline": prev.get("baseline", False), "extra": prev.get("extra", {})}
    cur = st["colour"]
    if raw_colour is None:
        st.update(pending=None, count=0)        # no data: not "beyond the edge", so the count starts again
        return st, None
    if cur is None:
        st.update(colour=raw_colour, pending=None, count=0, since=str(now), baseline=True)
        return st, None
    if raw_colour == cur:
        st.update(pending=None, count=0)
        return st, None
    if mode != "none":
        st["count"] = st["count"] + 1           # another run away from the current colour (whichever other colour)
        st["pending"] = raw_colour
        if st["count"] < confirm_runs:
            return st, None
    st.update(colour=raw_colour, pending=None, count=0, since=str(now), baseline=False)
    return st, cur


def trading_days_between(a, b):
    return int(np.busday_count(pd.Timestamp(a).date(), pd.Timestamp(b).date()))


def evaluate_dials(view, cfg, state):
    """Run every dial. Returns (readings, new dial state)."""
    readings, new_state = {}, {}
    runs = cfg["general"]["confirm_runs"]
    for d in DIALS:
        prev = (state or {}).get(d["id"], {})
        try:
            raw = d["fn"](view, cfg, prev.get("colour"))
        except Exception as ex:  # one broken dial must never stop the others
            raw = Raw(text=f"calculation error ({type(ex).__name__})")
        # stale data must not move a dial: treat it as no data, so the last colour is kept (shown greyed out)
        limit = cfg["max_age_days"].get(d["id"], cfg["max_age_days"]["default"])
        age = (view.now.normalize() - pd.Timestamp(raw.obs).normalize()).days if raw.obs is not None else None
        too_old = bool(cfg["general"].get("enforce_max_age", True)) and age is not None and age > limit
        if too_old:
            raw.colour = None
        # facts the regime and reading rely on must not vanish when a dial has no data this run
        if raw.colour is None and not any(k in raw.extra for k in KEEP):
            raw.extra = {**prev.get("extra", {}), **raw.extra}
        st, changed_from = step(prev, raw.colour, view.now, runs, d["confirm"])
        st["extra"] = {k: raw.extra[k] for k in KEEP if k in raw.extra}
        new_state[d["id"]] = st
        fresh_red = (st["colour"] == R and not st["baseline"] and st["since"] is not None
                     and trading_days_between(st["since"], view.now) < cfg["general"]["fresh_red_trading_days"])
        fresh_green = (st["colour"] == G and not st["baseline"] and st["since"] is not None
                       and (view.now - pd.Timestamp(st["since"])).days < cfg["turn"]["fresh_weeks"] * 7)
        readings[d["id"]] = {
            "id": d["id"], "group": d["group"], "title": d["title"], "value": raw.value, "text": raw.text,
            "colour": st["colour"], "word": WORD[st["colour"]], "raw_colour": raw.colour, "moves": raw.moves,
            "obs_date": str(raw.obs)[:10] if raw.obs is not None else None, "since": st["since"],
            "changed_from": changed_from, "fresh_red": fresh_red, "fresh_green": fresh_green, "no_data": raw.colour is None,
            "too_old": too_old, "age_days": age,
            "gauge": raw.gauge, "extra": raw.extra,
        }
    # "price at or below 1.3x realised price" drives the reading, so it gets the same protection as a dial:
    # a 2% buffer and two runs in a row, otherwise a price sitting on the line would flip the reading every run.
    bp, mult = readings.get("btc_price"), cfg["btc_price"]["confirmed_buy_multiple"]
    if bp is not None:
        ratio, prev = bp["extra"].get("ratio_to_realised"), (state or {}).get("_near", {})
        raw = band(ratio, [mult], ["yes", "no"], prev.get("colour"), cfg["general"]["price_buffer"], rel=True)
        near, _ = step(prev, raw, view.now, runs)
        new_state["_near"] = near
        bp["extra"]["at_or_below_confirmed_multiple"] = (near["colour"] == "yes") if near["colour"] else None
    return readings, new_state


def families(readings, cfg):
    out = {}
    for fam, ids in cfg["families"].items():
        got = [readings[i] for i in ids if i in readings]
        out[fam] = {"name": FAMILY_NAMES.get(fam, fam), "red": any(r["colour"] == R for r in got),
                    "fresh_red": [r["title"] for r in got if r["fresh_red"]],
                    "red_dials": [r["title"] for r in got if r["colour"] == R]}
    return out


def turn_status(readings, cfg):
    """The turn is confirmed when the dollar reversal dial is freshly green, or when two of the
    three turn families (rates; Fed and Treasury; crypto liquidity) are freshly green together.

    "Fresh" = the dial turned green within the last 13 weeks. A dial that has simply been
    green for a long time (a low dollar, growing stablecoins) is a state, not a turn.
    Bank reserves are in no family, so on their own they never confirm a turn."""
    fresh = lambda i: bool(readings.get(i, {}).get("fresh_green"))
    fams = {f: any(fresh(i) for i in ids) for f, ids in cfg["turn_families"].items()}
    dollar = fresh("dollar_reversal")
    fired = [r["title"] for r in readings.values() if r["group"] == "D" and r.get("fresh_green")]
    return {"confirmed": dollar or sum(fams.values()) >= 2, "dollar_reversal": dollar, "families": fams,
            "any_signal": bool(fired), "fresh_signals": fired}


def regime(readings, cfg):
    """TURN is shown only when the turn is confirmed. Otherwise the underlying regime is
    shown (first match wins: BREAK > STRESS BUILDING > FRAGILE > CALM) with a line
    listing any early turn signals (freshly green group D dials).
    STRESS BUILDING = two or more stress families red, or any one of the buy-blocking families red."""
    turn = turn_status(readings, cfg)
    x = lambda i, k: bool(readings.get(i, {}).get("extra", {}).get(k))
    red_bc = [r["title"] for r in readings.values() if r["group"] in "BC" and r["colour"] == R]
    fam = families(readings, cfg)
    red_fams = [f for f, v in fam.items() if v["red"]]
    # stress needs two or more families red, or any one of the buy-blocking families (funding, credit spreads, banks)
    stress = len(red_fams) >= 2 or any(f in cfg["buy_blocking_families"] for f in red_fams)
    early = turn["fresh_signals"]
    n = len(early)
    early_line = "" if not n else f"{n} early turn signal{'s' if n > 1 else ''}: " + ", ".join(early)
    if turn["confirmed"]:
        how = "the dollar has reversed" if turn["dollar_reversal"] else "two turn families are green together"
        out = {"name": "TURN", "detail": f"confirmed ({how}): " + ", ".join(early)}
    elif x("sp500", "month_end_break") or x("btc_weekly", "break_in_force"):
        why = [n_ for n_, f in (("S&P 500 month-end close below its 10-month average", x("sp500", "month_end_break")),
                                ("Bitcoin weekly close below the break level", x("btc_weekly", "break_in_force"))) if f]
        out = {"name": "BREAK", "detail": "; ".join(why)}
    elif stress:
        out = {"name": "STRESS BUILDING", "detail": "red: " + ", ".join(red_bc)}
    elif x("margin_debt", "fired_latched"):
        out = {"name": "FRAGILE", "detail": "the margin-debt signal fired within the past 12 months"}
    else:
        out = {"name": "CALM", "detail": "no stress, break or turn signal"}
    out.update(early_signals=early, early_line="" if turn["confirmed"] else early_line)
    return out


def reading(readings, cfg, rule="new"):
    """The buy / hold / sell reading. rule="new" is the two-level buy approved on
    25 Nov 2026; rule="old" is the original single buy rule, kept for comparison."""
    col = lambda i: readings.get(i, {}).get("colour")
    ex = lambda i, k, d=None: readings.get(i, {}).get("extra", {}).get(k, d)
    fam, turn = families(readings, cfg), turn_status(readings, cfg)

    froth = [n for n, f in (("funding at 30% a year or more", col("funding") == R),
                            ("altcoin open interest at or above its 90th percentile", col("alt_oi") == R),
                            ("price above 2.4x realised price", col("btc_price") == R)) if f]
    red_fams = [f["name"] for f in fam.values() if f["red"]]
    liq = [n for n, f in (("the margin-debt signal has fired", bool(ex("margin_debt", "fired_latched"))),
                          ("the dollar is above 102.5 and rising", col("dollar") == R),
                          (f"{len(red_fams)} families red ({', '.join(red_fams)})", len(red_fams) >= 2)) if f]
    cheap = col("btc_price") == G
    ratio = ex("btc_price", "ratio_to_realised")
    near = ex("btc_price", "at_or_below_confirmed_multiple")           # confirmed over two runs, with a 2% buffer
    if near is None:
        near = ratio is not None and ratio <= cfg["btc_price"]["confirmed_buy_multiple"]
    capit = [n for n, f in (("long-term holders are selling at a loss (LTH-SOPR green)", col("lth_sopr") == G),
                            ("net realised losses are spiking", col("net_loss") == G)) if f]
    block = [f"{fam[f]['name']} ({', '.join(fam[f]['fresh_red'])})" for f in cfg["buy_blocking_families"] if fam[f]["fresh_red"]]
    any_fresh = [r["title"] for r in readings.values() if r["group"] in "BC" and r["fresh_red"]]
    old_turned = [r["title"] for r in readings.values() if r["group"] == "D" and r["colour"] == G]  # original rule: any green
    turned = old_turned if rule == "old" else turn["fresh_signals"]
    out = {"rule": rule, "caution": bool(ex("btc_weekly", "break_in_force")) and not cheap, "turn": turn}

    not_cheap = not near                                               # frothy and cheap cannot both be true
    if froth and liq and not_cheap:
        out.update(label="FROTH WARNING", headline="Froth warning (reduce-risk watch)",
                   reasons=["Froth: " + "; ".join(froth), "Liquidity deteriorating: " + "; ".join(liq)],
                   change="Back to hold when the froth clears, liquidity stops deteriorating, or price falls to 1.3x realised price or below.",
                   record=cfg["froth_warning"]["record"])
    elif rule == "old" and cheap and turned and not any_fresh:
        out.update(label="BUY", headline="Buy (in stages)",
                   reasons=["Price is in the value zone", "Turn signal: " + ", ".join(turned), "No group B or C dial newly red in 5 trading days"],
                   change="Back to hold if price leaves the value zone, the turn signals fade, or a stress dial turns red.")
    elif rule == "new" and near and turn["confirmed"] and not block:
        how = "the dollar has reversed" if turn["dollar_reversal"] else "two turn families are green (" + ", ".join(f for f, g in turn["families"].items() if g) + ")"
        out.update(label="BUY", level="CONFIRMED", headline="Buy (confirmed)",
                   reasons=[f"Price is {ratio:.2f}x realised price (at or below 1.3x)" if ratio is not None else "Price is at or below 1.3x realised price", f"Turn confirmed: {how}",
                            "No fresh red in money-market funding, credit spreads or banks"],
                   change="Back to hold if the turn is no longer confirmed, price rises above 1.3x realised price, or fresh stress appears in funding, credit or banks.")
    elif rule == "new" and cheap and capit and not block:
        out.update(label="BUY", level="STAGED", headline="Buy (staged)",
                   reasons=["Price is in the value zone", "Capitulation sign: " + "; ".join(capit),
                            "No fresh red in money-market funding, credit spreads or banks",
                            "The turn is not confirmed yet, so buy in stages" if not turn["confirmed"] else "Turn confirmed"],
                   change="Becomes Buy (confirmed) when the dollar reverses or two turn families go green; back to hold if price leaves the value zone or fresh stress appears.")
    else:
        if froth:
            kind, reasons = "frothy, but liquidity is not deteriorating", ["Froth: " + "; ".join(froth)]
            change = "Froth warning if the margin-debt signal fires, the dollar rises through 102.5, or two families turn red (and price is above 1.3x realised price)."
        elif cheap:
            if rule == "old":
                why = "no turn signal has fired" if not turned else "a stress dial turned red in the past 5 trading days (" + ", ".join(any_fresh) + ")"
                change = "Buy when a group D turn signal goes green with no newly red stress dial."
            elif not capit:
                why = "no capitulation sign and the turn is not confirmed"
                change = "Buy (staged) when LTH-SOPR or net realised losses turn green; Buy (confirmed) when the turn is confirmed."
            else:
                why = "fresh stress in " + "; ".join(block)
                change = "Buy once that dial has been red for more than 5 trading days without a new one joining it, or it clears."
            kind, reasons = f"cheap, but {why}", ["Price is in the value zone"]
        elif rule == "new" and near:
            why = "the turn is not confirmed" if not turn["confirmed"] else "fresh stress in " + "; ".join(block)
            kind, reasons = f"fairly cheap, but {why}", [f"Price is {ratio:.2f}x realised price, not yet in the value zone" if ratio is not None else "Price is at or below 1.3x realised price"]
            change = "Buy (confirmed) when the dollar reverses or two turn families go green; Buy (staged) if price falls into the value zone with a capitulation sign."
        else:
            kind, reasons = "neither cheap nor frothy", ["Price is outside the value zone and below the froth level"]
            change = "Buy needs a cheaper price or a confirmed turn; a froth warning needs froth with deteriorating liquidity."
        if not turn["confirmed"]:
            reasons.append("Turn not confirmed" + (": " + ", ".join(turned) + " only" if turned else ": no turn signal is freshly green"))
        if liq:
            reasons.append("Liquidity deteriorating: " + "; ".join(liq))
        elif red_fams:
            reasons.append("Red family: " + ", ".join(red_fams))
        out.update(label="HOLD", headline="Hold: " + kind, reasons=reasons[:4], change=change)
    if out["caution"] and out["label"] == "HOLD":
        out["headline"] += " (CAUTION: weekly close below the break level)"

    alt_green = col("alt_oi") == G
    if out["label"] == "BUY" and alt_green:
        out["alts"] = {"label": "BUY", "headline": out["headline"], "why": "Bitcoin reading is Buy and altcoin open interest is below its 50th percentile"}
    elif out["label"] == "FROTH WARNING":
        out["alts"] = {"label": "FROTH WARNING", "headline": "Froth warning (reduce-risk watch)", "why": "altcoins take the brunt of a deleveraging"}
    else:
        why = ("the Bitcoin reading is not Buy" if out["label"] != "BUY"
               else "altcoin open interest is not below its 50th percentile" if col("alt_oi") else "altcoin open interest has no reading yet")
        out["alts"] = {"label": "HOLD", "headline": "Hold", "why": why}
    return out


def trend_exit(readings):
    """Coutts' regime filter as its own line, separate from buy / hold.
    RISK-OFF after a weekly close below the break line; back to RISK-ON on a weekly close above the reclaim line."""
    r = readings.get("btc_weekly", {})
    ex = r.get("extra", {})
    if r.get("colour") is None or "break_in_force" not in ex:
        return {"state": "NO DATA", "text": "no weekly close available"}
    off = bool(ex["break_in_force"])
    brk, rec = ex.get("break_level"), ex.get("reclaim_level")
    return {"state": "RISK-OFF" if off else "RISK-ON",
            "text": (f"weekly close below the break line; back to risk-on on a weekly close above ${rec:,.0f}" if off
                     else f"no break in force; risk-off on a weekly close below ${brk:,.0f}"),
            "break_level": brk, "reclaim_level": rec, "weekly_close": r.get("value")}


def evaluate(view, cfg, state=None):
    """Everything for one run. state: {"dials": {...}} from the previous run."""
    readings, dial_state = evaluate_dials(view, cfg, (state or {}).get("dials"))
    return {"readings": readings, "families": families(readings, cfg), "regime": regime(readings, cfg),
            "reading": reading(readings, cfg, "new"), "reading_old_rule": reading(readings, cfg, "old"),
            "trend_exit": trend_exit(readings), "turn": turn_status(readings, cfg),
            "state": {"dials": dial_state}}
