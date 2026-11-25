"""Plain-English wording for the dashboard, the pushes and the digest.

Presentation only: nothing here changes a rule, a threshold or a colour. Every sentence is
built from the live readings in the feed, not from fixed text.
"""
import pandas as pd

G, A, R = "green", "amber", "red"
LIGHT = {"BUY": ("BUY", G), "HOLD": ("HOLD", A), "FROTH WARNING": ("SELL", R)}
SYMBOL = {G: "▲", A: "●", R: "▼", None: "○"}
WORD = {G: "Supports buying", A: "Neutral", R: "Against buying", None: "No data"}

# What each dial is doing now, in plain words, by colour. Read as "…, and …".
PHRASE = {
    # ---- is it cheap?
    "btc_price": {G: "Bitcoin is in its cheap zone", A: "Bitcoin is neither cheap nor overheated", R: "Bitcoin looks overheated against what holders paid"},
    "btc_weekly": {G: "Bitcoin's weekly trend is up", A: "Bitcoin is sitting on its weekly trend line", R: "Bitcoin's weekly trend is down"},
    "weekly_move": {G: "last week's fall was unusually large, the kind seen in washouts", A: "last week's move was ordinary", R: "last week's rise was unusually large"},
    "lth_sopr": {G: "long-term holders are selling at a loss, as they did at past lows", A: "long-term holders are not selling at a loss", R: "long-term holders are cashing in large profits"},
    "net_loss": {G: "losses being taken are as heavy as at past lows", A: "losses being taken are not extreme", R: "losses being taken are not extreme"},
    "btc_ndx": {G: "Bitcoin is gaining on tech shares", A: "Bitcoin is moving in line with tech shares", R: "Bitcoin is losing ground to tech shares"},
    "alt_value": {G: "smaller coins are gaining on Bitcoin", A: "smaller coins are holding level with Bitcoin", R: "smaller coins are losing ground to Bitcoin"},
    "alt_watch": {G: "the watchlist coins are gaining on Bitcoin", A: "the watchlist coins are roughly level with Bitcoin", R: "the watchlist coins are losing ground to Bitcoin"},
    # ---- rates and the dollar
    "y2_chg": {G: "short-term interest rates are falling", A: "short-term interest rates are steady", R: "short-term interest rates are rising"},
    "y10_chg": {G: "long-term interest rates are falling", A: "long-term interest rates are steady", R: "long-term interest rates are rising"},
    "hike_pricing": {G: "markets are betting less on rate rises", A: "bets on rate rises are unchanged", R: "markets are betting more on rate rises"},
    "cpi_mom": {G: "the latest inflation figure was mild", A: "the latest inflation figure was middling", R: "the latest inflation figure was hot"},
    "breakeven": {G: "expected inflation is contained", A: "expected inflation is on the high side", R: "expected inflation is high"},
    "liquidity": {G: "central banks are adding money", A: "central-bank money is barely growing", R: "central-bank money is shrinking"},
    "dollar": {G: "the dollar is weak or has turned down", A: "the dollar is strong but no longer rising", R: "the dollar is strong and still rising"},
    # ---- money-market funding
    "sofr_iorb": {G: "overnight cash is plentiful", A: "overnight cash is a little tight", R: "overnight cash is scarce"},
    "discount_window": {G: "banks are not leaning on the Fed's emergency window", A: "banks are borrowing more from the Fed's emergency window", R: "banks are borrowing heavily from the Fed's emergency window"},
    "srf": {G: "dealers are not tapping the Fed for overnight cash", A: "dealers are tapping the Fed for some overnight cash", R: "dealers are tapping the Fed heavily for overnight cash"},
    # ---- credit spreads
    "hy_spread": {G: "risky companies can still borrow cheaply", A: "borrowing costs for risky companies are creeping up", R: "borrowing costs for risky companies are jumping"},
    "ccc_bb": {G: "the weakest borrowers are not being singled out", A: "the weakest borrowers are being charged noticeably more", R: "the weakest borrowers are being shut out"},
    "bbb_spread": {G: "solid companies can borrow cheaply", A: "borrowing costs for solid companies are edging up", R: "borrowing costs for solid companies are jumping"},
    "nfci": {G: "financial conditions are loose", A: "financial conditions are about average", R: "financial conditions are tight"},
    "stlfsi": {G: "the Fed's stress gauge is calm", A: "the Fed's stress gauge is raised", R: "the Fed's stress gauge is high"},
    # ---- AI and private credit
    "ai_basket": {G: "debt-funded AI shares are keeping up with the market", A: "debt-funded AI shares are lagging the market", R: "debt-funded AI shares are falling well behind the market"},
    "bizd": {G: "private-credit lenders are steady", A: "private-credit lenders have slipped", R: "private-credit lenders are falling hard"},
    # ---- banks
    "kre": {G: "regional bank shares are holding up", A: "regional bank shares are sliding", R: "regional bank shares are falling hard"},
    # ---- crypto leverage
    "funding": {G: "traders are paying to bet against Bitcoin", A: "bets on Bitcoin with borrowed money are moderate", R: "bets on Bitcoin with borrowed money are crowded"},
    "alt_oi": {G: "borrowed bets on smaller coins are light", A: "borrowed bets on smaller coins are moderate", R: "borrowed bets on smaller coins are stretched"},
    "stable_30d": {G: "money is flowing into crypto dollars", A: "money is trickling out of crypto dollars", R: "money is leaving crypto dollars"},
    # ---- equities
    "sp500": {G: "US shares are in an uptrend", A: "US shares have slipped below their trend", R: "US shares have broken their trend"},
    "margin_debt": {G: "borrowing to buy shares is not overheated", A: "borrowing to buy shares has cooled after a surge", R: "borrowing to buy shares has rolled over after a surge"},
    # ---- has the turn started?
    "dollar_reversal": {G: "the dollar has turned down", A: "the dollar has stopped rising", R: "the dollar is still rising"},
    "front_end": {G: "short-term rates have dropped sharply", A: "short-term rates have not moved much", R: "short-term rates have jumped"},
    "fed_bills": {G: "the Fed is buying Treasury bills", A: "the Fed is not adding to its bills", R: "the Fed is shedding Treasury bills"},
    "fed_reserves": {G: "bank reserves are rising", A: "bank reserves are flat", R: "bank reserves are falling"},
    "stable_turn": {G: "money has started flowing back into crypto dollars", A: "the outflow from crypto dollars is slowing", R: "the outflow from crypto dollars is getting worse"},
    "weekly_reclaim": {G: "Bitcoin has just climbed back above its weekly trend line", A: "Bitcoin has no broken trend to repair", R: "Bitcoin is still below its weekly trend line"},
    "buybacks": {G: "the Treasury has stepped up its bond buybacks", A: "Treasury buybacks are running at their usual pace", R: "Treasury buybacks have dropped off"},
    "hikes_out": {G: "markets have sharply cut their bets on rate rises", A: "bets on rate rises have not moved much", R: "markets are adding to bets on rate rises"},
}

# What the group's state means for crypto, by the group's colour.
MEANING = {
    "valuation": {G: "On price alone this is a good area to buy.", A: "On price alone there is no strong case either way.", R: "On price and trend this argues for waiting."},
    "rates_dollar": {G: "Easier money and a softer dollar tend to lift crypto, so this supports buying.",
                     A: "Rates and the dollar are not pushing crypto either way.",
                     R: "A rising dollar and tighter money drain cash from crypto, so this works against buying."},
    "money_market": {G: "The plumbing of the money markets is working normally, which is what crypto needs.",
                     A: "Slight strain in the money markets; worth watching, not yet a problem for crypto.",
                     R: "When cash gets scarce, risky assets are sold first, so this works against buying."},
    "credit": {G: "Calm credit markets mean no forced selling, which supports buying.",
               A: "Credit is tightening a little; not yet a threat to crypto.",
               R: "Trouble in credit spreads quickly to all risky assets, so this works against buying."},
    "ai_private": {G: "No sign of the AI borrowing boom cracking.",
                   A: "Some strain in AI and private lending; a warning, not yet a break.",
                   R: "This is where a credit accident could start, so it works against buying."},
    "banks": {G: "Banks are not under pressure.", A: "Banks are under some pressure; worth watching.", R: "Bank stress has hit crypto hard before, so this works against buying."},
    "crypto_leverage": {G: "Little borrowed money is at risk of being flushed out, which supports buying.",
                        A: "Borrowed money in crypto is neither stretched nor washed out.",
                        R: "Crowded borrowing or money leaving crypto makes sharp falls more likely, so this works against buying."},
    "equities": {G: "A healthy share market supports risk-taking in crypto.",
                 A: "Shares are wobbling; no clear message for crypto yet.",
                 R: "A broken share market usually drags crypto down with it, so this works against buying."},
    "turn": {G: "The turn in money conditions has started, which is when Bitcoin has tended to recover.",
             A: "The turn in money conditions has not started yet.",
             R: "Money conditions are still moving the wrong way."},
}


def _join(parts):
    parts = [p for p in parts if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def _cap(s):
    return s[:1].upper() + s[1:] if s else s


def _phrases(dials, colour, limit):
    seen, out = set(), []
    for d in dials:
        if d.get("colour") == colour and not d.get("stale"):
            p = PHRASE.get(d["id"], {}).get(colour)
            if p and p not in seen:
                seen.add(p)
                out.append(p)
    return out[:limit]


def group_sentence(section, dials):
    """One or two plain sentences: what the group is doing now, and what that means for crypto."""
    mine = [dials[i] for i in section["dials"] if i in dials]
    colour = section.get("colour")
    if colour is None or not any(d.get("colour") for d in mine):
        return "No data yet."
    red, amber, green = (_phrases(mine, c, n) for c, n in ((R, 3), (A, 2), (G, 3)))
    if colour == R:
        now = _join(red) or "at least one measure here is flashing red"
        if green:
            now += ", although " + green[0]
    elif colour == A:
        if green and amber:
            now = _join(green[:2]) + ", but " + amber[0]
        else:
            now = _join(amber) or _join(green[:2]) or "nothing here stands out"
    else:
        now = _join(green) or "everything here is in good shape"
    return _cap(now) + ". " + MEANING.get(section["id"], MEANING["turn"])[colour]


def turn_clause(dials):
    c = dials.get("dollar", {}).get("colour")
    if c == R:
        return "the dollar is still rising, so the turn has not started"
    if c == A:
        return "the dollar has stopped rising but has not turned down, so the turn has not started"
    return "money conditions have not clearly turned up yet"


def headline(feed):
    """The traffic light: one word, a colour, a symbol and one plain sentence saying why."""
    rd = feed["reading"]
    dials = {d["id"]: d for d in feed["dials"]}
    word, colour = LIGHT.get(rd["label"], ("HOLD", A))
    kind, where = rd.get("kind", ""), _join(rd.get("blocked_by") or [])
    turn = feed.get("turn", {})
    how = "the dollar has turned down" if turn.get("dollar_reversal") else "money conditions are turning up"
    sentence = {
        "buy_staged": "Buy, in stages. Bitcoin is cheap and holders are selling at a loss, which is what past lows looked like. Money conditions have not turned yet, so go slowly.",
        "buy_confirmed": f"Buy. Bitcoin is reasonably priced and {how}.",
        "froth": "Sell signal (reduce-risk watch). Bitcoin looks overheated and money conditions are getting worse.",
        "hold_froth": "Hold. Bitcoin looks overheated, but money conditions are not getting worse.",
        "hold_cheap_waiting": f"Hold. Bitcoin is cheap, but sellers have not given up yet and {turn_clause(dials)}.",
        "hold_cheap_stress": f"Hold. Bitcoin is cheap, but fresh stress has just appeared in {where or 'the financial system'}.",
        "hold_near_no_turn": f"Hold. Bitcoin is fairly cheap, but {turn_clause(dials)}.",
        "hold_near_stress": f"Hold. Bitcoin is fairly cheap and the turn has started, but fresh stress has just appeared in {where or 'the financial system'}.",
        "hold_neutral": "Hold. Bitcoin is neither cheap nor overheated.",
    }.get(kind, "Hold. " + rd.get("headline", "").replace("Hold: ", "").capitalize() + ".")
    if rd.get("caution") and word == "HOLD":
        sentence += " Its weekly trend is down, so take extra care."
    if kind == "buy_staged" and turn.get("confirmed"):
        sentence = "Buy, in stages. Bitcoin is cheap and holders are selling at a loss, which is what past lows looked like."
    return {"word": word, "colour": colour, "symbol": SYMBOL[colour], "sentence": sentence}


def what_would_change(feed):
    kind = feed["reading"].get("kind", "")
    return {
        "buy_staged": "It becomes a full Buy when the dollar turns down or two other signs of easier money appear. It goes back to Hold if Bitcoin leaves its cheap zone or fresh stress appears in funding, credit or banks.",
        "buy_confirmed": "It goes back to Hold if the signs of easier money fade, Bitcoin gets expensive, or fresh stress appears in funding, credit or banks.",
        "froth": "It goes back to Hold when Bitcoin cools off, money conditions stop getting worse, or the price falls back to a fair level.",
        "hold_froth": "It becomes a Sell signal if money conditions start getting worse while Bitcoin is still overheated.",
        "hold_cheap_waiting": "It becomes Buy (in stages) when long-term holders start selling at a loss or losses spike. It becomes a full Buy when the dollar turns down.",
        "hold_cheap_stress": "It becomes Buy once that stress has been in place for more than five trading days without spreading, or it clears.",
        "hold_near_no_turn": "It becomes Buy when the dollar turns down or two other signs of easier money appear, or if Bitcoin falls into its cheap zone while holders sell at a loss.",
        "hold_near_stress": "It becomes Buy once that stress has been in place for more than five trading days without spreading, or it clears.",
        "hold_neutral": "Buy needs a cheaper price or a clear turn in money conditions. A Sell signal needs an overheated price together with worsening money conditions.",
    }.get(kind, feed["reading"].get("change", ""))


def backdrop(feed):
    """The old regime names, in plain words. The names themselves stay in the feed for bots."""
    rg = feed["regime"]
    dials = {d["id"]: d for d in feed["dials"]}
    name = rg["name"]
    if name == "CALM":
        text = "Calm"
    elif name == "FRAGILE":
        text = "Leverage warning: borrowing to buy shares has rolled over"
    elif name == "STRESS BUILDING":
        groups = [s["name"].lower() for s in feed["sections"] if s["kind"] == "stress" and s["colour"] == R]
        groups = [g.replace("ai and", "AI and") for g in groups]
        text = "Stress is building in " + (_join(groups) or "parts of the financial system")
    elif name == "BREAK":
        btc = dials.get("btc_weekly", {}).get("extra", {}).get("break_in_force")
        spx = dials.get("sp500", {}).get("extra", {}).get("month_end_break")
        parts = (["Bitcoin is below its weekly trend line"] if btc else []) + \
                (["the S&P 500 closed last month below its 10-month average"] if spx else [])
        text = "Downtrend: " + (_join(parts) or "a trend line has been broken")
    elif name == "TURN":
        text = "Liquidity is turning up"
    else:
        text = name.capitalize()
    early = [PHRASE.get(d["id"], {}).get(G, d["title"]) for d in feed["dials"]
             if d.get("fresh_turn_signal") and d["colour"] == G]
    early_line = "" if (name == "TURN" or not early) else "Early signs of a turn: " + _join(early) + "."
    return {"text": text, "early": early_line}


def _day(stamp):
    t = pd.Timestamp(stamp)
    return f"{t.day} {t:%b}" + (f" {t.year}" if t.year != pd.Timestamp.now().year else "")


def trend(feed):
    tr = feed["trend_exit"]
    if tr["state"] == "NO DATA":
        return {"text": "Trend: no data", "colour": None}
    way, colour = ("down", R) if tr["state"] == "RISK-OFF" else ("up", G)
    since = f" since {_day(tr['since'])}" if tr.get("since") else " for more than five months"
    return {"text": f"Trend: {way}{since}", "colour": colour,
            "detail": ("Bitcoin's weekly close is below its trend line; it turns up again on a weekly close above "
                       f"${tr['reclaim_level']:,.0f}." if way == "down" else
                       f"Bitcoin's weekly close is above its trend line; it turns down on a weekly close below ${tr['break_level']:,.0f}.")}


def tally(feed):
    live = [s for s in feed["sections"] if s["colour"]]
    n = {c: sum(1 for s in live if s["colour"] == c) for c in (G, A, R)}
    return {"groups": len(live), **n,
            "text": f"Of the {len(live)} groups: {n[G]} support buying, {n[A]} neutral, {n[R]} against"}


def dial_change(d, old):
    """One plain sentence for a push when a dial changes colour."""
    main = (d.get("text") or "").split(" · ")[0]
    was = WORD[old].lower()
    now = WORD[d["colour"]].lower()
    return f"{d['title']}: now {now} (was {was}). {_cap(PHRASE.get(d['id'], {}).get(d['colour'], d['title']))} ({main})."


def build(feed):
    """Everything plain, in one place; added to the feed under "plain"."""
    dials = {d["id"]: d for d in feed["dials"]}
    return {"headline": headline(feed), "what_would_change": what_would_change(feed), "backdrop": backdrop(feed),
            "trend": trend(feed), "tally": tally(feed),
            "groups": {s["id"]: group_sentence(s, dials) for s in feed["sections"]},
            "weak_record": f"Exit signals have a weak record: {feed['reading'].get('record', '')}." if feed["reading"]["label"] == "FROTH WARNING" else ""}
