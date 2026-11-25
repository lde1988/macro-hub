"""Rebuild registry/oi_universe.yaml from a full Coinalyze census (the files written by tools/oi_backfill.py).

    python tools/oi_universe.py CENSUS_DIR

The daily open-interest update cannot ask for all ~5,500 markets (40 a minute), so it uses the
largest crypto markets that together hold 97% of altcoin open interest, plus every Bitcoin market.
Shares, indices, commodities, metals, currencies, tokenised gold and stablecoins are not altcoins
and are left out (list below). Re-run this a few times a year: new listings are not picked up until then.
"""
import sys

import pandas as pd
import yaml

NON_CRYPTO = sorted("""XAU XAG CL BZ NVDA SOXL SOXS QQQ TQQQ SPY TSLA AAPL SNDK SKHYNIX SKHY SPCX MU GOOGL INTC CRCL MSTR
NBIS KORU EWY AMD AVGO DRAM SAMSUNG META ORCL MRVL MSFT SNXX DELL CRWV UNITREE ANT XAUT PAXG USDC USDT""".split())
COVERAGE = 0.97


def build(symbols_csv):
    s = pd.read_csv(symbols_csv, index_col=0)
    s = s[s["latest_usd"] > 0]
    is_btc = s["base"].isin(["BTC", "XBT"])
    btc = s[is_btc].sort_values("latest_usd", ascending=False)
    alt = s[~is_btc & ~s["base"].isin(NON_CRYPTO)].sort_values("latest_usd", ascending=False)
    share = alt["latest_usd"].cumsum() / alt["latest_usd"].sum()
    keep = alt[share.shift(1, fill_value=0) < COVERAGE]
    return {"note": "Written by tools/oi_universe.py. Do not edit by hand.",
            "coverage_of_altcoin_open_interest": COVERAGE,
            "excluded_non_crypto": NON_CRYPTO,
            "btc": list(btc.index), "alt": list(keep.index)}


if __name__ == "__main__":
    u = build(sys.argv[1] + "/symbols.csv")
    with open("registry/oi_universe.yaml", "w") as f:
        yaml.safe_dump(u, f, sort_keys=False, width=1000)
    print(len(u["btc"]), "Bitcoin markets,", len(u["alt"]), "altcoin markets")
