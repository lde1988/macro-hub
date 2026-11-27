"""Which coins are scanned (reports/18, section 2). Pure: works on data already fetched.

From CoinGecko's top 250 by market cap: leave out stablecoins, wrapped / bridged / staked copies, tokenized gold,
commodities, funds and stocks, and anything whose price hardly moves (pegged). Keep the first 100, and always
the owner's coins. Memecoins and exchange tokens are kept, labelled and hideable. Every exclusion has a reason.
"""
import numpy as np


def daily_vol(prices, days=30):
    p = prices.dropna().tail(days + 1)
    if len(p) < days // 2:
        return None
    return float(np.abs(np.log(p).diff().dropna()).mean())


def sector(cats, rules):
    for name, ids in rules.items():
        if any(c in cats for c in ids):
            return name
    return "Other"


def build(markets, members, cfg, prices=None, coin_cats=None):
    """markets: CoinGecko /coins/markets rows (rank order). members: {category id: set of coin ids}.
    prices: {coin id: Series} for the pegged test. coin_cats: {coin id: [category ids]} for sectors.
    Returns (kept, excluded): kept rows carry labels; excluded rows carry their reasons."""
    u = cfg["universe"]
    prices, coin_cats = prices or {}, coin_cats or {}
    kept, excluded = [], []
    by_id = {m["id"]: m for m in markets}
    for m in markets:
        why = [f"category: {c}" for c in u["exclude_categories"] if m["id"] in (members.get(c) or set())]
        if m["id"] in u["exclude_ids"]:
            why.append("tokenized fund or security")
        v = daily_vol(prices[m["id"]]) if m["id"] in prices else None
        if v is not None and v < u["pegged_max_vol_30d"]:
            why.append(f"price hardly moves (average daily move {v:.2%}): pegged")
        if why and m["id"] not in u["owner_coins"]:
            excluded.append({"id": m["id"], "symbol": m["symbol"].upper(), "name": m["name"],
                             "rank": m.get("market_cap_rank"), "reasons": why})
            continue
        if len(kept) < u["top_n"] or m["id"] in u["owner_coins"]:
            kept.append(m)
    have = {m["id"] for m in kept}
    missing = [c for c in u["owner_coins"] if c not in have]
    rows = []
    for m in kept:
        cats = set(coin_cats.get(m["id"], []))
        rows.append({"id": m["id"], "symbol": m["symbol"].upper(), "name": m["name"], "rank": m.get("market_cap_rank"),
                     "price": m.get("current_price"), "market_cap": m.get("market_cap"),
                     "circulating": m.get("circulating_supply"), "total": m.get("total_supply"), "max": m.get("max_supply"),
                     "change_7d": m.get("price_change_percentage_7d_in_currency"),
                     "meme": m["id"] in (members.get(u["meme_category"]) or set()),
                     "exchange": m["id"] in u["exchange_ids"], "owner": m["id"] in u["owner_coins"],
                     "sector": "Meme" if m["id"] in (members.get(u["meme_category"]) or set())
                     else "Exchange" if m["id"] in u["exchange_ids"] else sector(cats, cfg["sectors"])})
    return rows, excluded, missing
