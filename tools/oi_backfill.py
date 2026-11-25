"""One-off: pull daily open-interest history for every perpetual market on
Coinalyze (about 1,500 days each) and work out altcoin / Bitcoin open interest.

Coinalyze allows 40 symbols a minute, so this takes about two and a half hours.
Writes summary.md plus compact tables into the folder given as the first argument.
The key is read from the environment and never printed.
"""
import datetime as dt
import os
import sys
import time

import pandas as pd
import requests

KEY = os.environ["COINALYZE_API_KEY"].strip()
CZ = "https://api.coinalyze.net/v1"
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
BUDGET_S = int(os.environ.get("BUDGET_MINUTES", "300")) * 60
SKIP_EXCHANGES = {"tradeXYZ", "Polymarket"}  # equity / prediction markets, not altcoins
ORDER = ["Binance", "Bybit", "OKX", "Hyperliquid", "Gate.io", "Huobi", "Deribit", "Coinbase", "Kraken",
         "Bitfinex", "dYdX", "Aster", "Lighter", "WOO X", "Phemex"]
T_START = time.time()
S = requests.Session()


def cz(path, **params):
    for _ in range(10):
        try:
            r = S.get(CZ + path, headers={"api_key": KEY}, params=params, timeout=120)
        except requests.RequestException:
            time.sleep(10)
            continue
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 30)) + 0.5)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        return r.json()
    raise RuntimeError("gave up after 10 tries")


def main():
    os.makedirs(OUT, exist_ok=True)
    ex = {e["code"]: e["name"] for e in cz("/exchanges")}
    mk = [m for m in cz("/future-markets") if m.get("is_perpetual")]
    for m in mk:
        m["ex"] = ex.get(m["exchange"], m["exchange"])
    mk = [m for m in mk if m["ex"] not in SKIP_EXCHANGES]
    mk.sort(key=lambda m: (ORDER.index(m["ex"]) if m["ex"] in ORDER else 99, m["base_asset"] != "BTC"))
    meta = {m["symbol"]: m for m in mk}
    syms = list(meta)
    now = int(time.time())
    series, failed, done = {}, 0, 0
    for i in range(0, len(syms), 20):
        if time.time() - T_START > BUDGET_S:
            break
        chunk = syms[i:i + 20]
        try:
            res = cz("/open-interest-history", symbols=",".join(chunk), interval="daily",
                     convert_to_usd="true", **{"from": 1577836800, "to": now})
            for x in res:
                if x.get("history"):
                    series[x["symbol"]] = pd.Series({h["t"]: h["c"] for h in x["history"]})
        except Exception as e:
            failed += len(chunk)
            print(f"chunk {i} failed: {type(e).__name__}")
        done = i + len(chunk)
        if (i // 20) % 20 == 0:
            print(f"{done}/{len(syms)} symbols, {len(series)} with data, {int(time.time() - T_START)}s", flush=True)

    df = pd.DataFrame(series)
    df.index = pd.to_datetime(df.index, unit="s").date
    df = df.sort_index()
    cols = pd.DataFrame({"ex": [meta[c]["ex"] for c in df.columns], "base": [meta[c]["base_asset"] for c in df.columns]},
                        index=df.columns)
    is_btc = cols["base"].isin(["BTC", "XBT"])

    by_base = df.T.groupby(cols["base"]).sum(min_count=1).T
    top = by_base.max().sort_values(ascending=False)
    keep = list(top.index[:400])
    slim = by_base[keep].copy()
    slim["OTHER"] = by_base.drop(columns=keep).sum(axis=1)
    slim.round(0).to_csv(os.path.join(OUT, "oi_by_base.csv.gz"), compression="gzip")

    rows = []
    for e in sorted(cols["ex"].unique()):
        m = cols["ex"] == e
        rows.append(pd.DataFrame({"exchange": e, "btc": df.loc[:, m & is_btc].sum(axis=1, min_count=1),
                                  "alt": df.loc[:, m & ~is_btc].sum(axis=1, min_count=1),
                                  "markets": df.loc[:, m].notna().sum(axis=1)}))
    byx = pd.concat(rows).rename_axis("date").reset_index()
    byx.round(0).to_csv(os.path.join(OUT, "oi_by_exchange.csv"), index=False)

    last = df.ffill().iloc[-1]
    pd.DataFrame({"exchange": cols["ex"], "base": cols["base"], "latest_usd": last.round(0),
                  "first_day": df.apply(lambda s: s.first_valid_index()), "days": df.notna().sum()}
                 ).sort_values("latest_usd", ascending=False).to_csv(os.path.join(OUT, "symbols.csv"))

    def ratio(mask=None):
        d = df if mask is None else df.loc[:, mask]
        b = is_btc if mask is None else is_btc[mask]
        return (d.loc[:, ~b].sum(axis=1) / d.loc[:, b].sum(axis=1)).dropna()

    def describe(name, r):
        day = dt.date(2026, 9, 27)
        out = f"| {name} | {r.index[0]} | "
        if day in r.index:
            hist = r[r.index <= day]
            out += f"{r[day]:.2f}x | {(hist <= r[day]).mean() * 100:.0f} | "
        else:
            out += "n/a | n/a | "
        return out + f"{r.iloc[-2]:.2f}x | {(r <= r.iloc[-2]).mean() * 100:.0f} | {r.max():.2f}x on {r.idxmax()} |"

    stable_m = pd.Series([meta[c].get("margined") == "STABLE" for c in df.columns], index=df.columns)
    L = [f"Open-interest backfill finished {dt.datetime.now(dt.timezone.utc).isoformat()[:16]}Z",
         f"Markets asked: {done} of {len(syms)}; with data: {len(series)}; failed: {failed}; "
         f"days: {df.index[0]} to {df.index[-1]} ({len(df)})", "",
         "| universe | history from | ratio 27 Sep 2026 | its percentile to that date | latest finished day | percentile | highest |",
         "|---|---|---|---|---|---|---|",
         describe("all exchanges, all perps", ratio())]
    for name, exs in [("Binance only", ["Binance"]), ("Binance + Bybit + OKX", ["Binance", "Bybit", "OKX"]),
                      ("Binance + Bybit + OKX + Hyperliquid", ["Binance", "Bybit", "OKX", "Hyperliquid"]),
                      ("top 3 + Hyperliquid + Gate + Huobi + Deribit", ["Binance", "Bybit", "OKX", "Hyperliquid", "Gate.io", "Huobi", "Deribit"])]:
        try:
            L.append(describe(name, ratio(cols["ex"].isin(exs))))
        except Exception as e:
            L.append(f"| {name} | failed {type(e).__name__} | | | | | |")
    try:
        L.append(describe("all exchanges, stablecoin-margined only", ratio(stable_m)))
        eth = cols["base"] == "ETH"
        L.append(describe("all exchanges, alts excluding ETH", ratio(~eth)))
    except Exception as e:
        L.append(f"| variants failed {type(e).__name__} | | | | | | |")
    day = df.index[-2]
    tb = by_base.loc[day].sort_values(ascending=False).head(60)
    L += ["", f"Largest base assets by open interest on {day} ($bn): "
          + ", ".join(f"{k} {v / 1e9:.2f}" for k, v in tb.items()),
          "", f"Total on {day}: BTC ${df.loc[day, is_btc].sum() / 1e9:.1f}bn, alts ${df.loc[day, ~is_btc].sum() / 1e9:.1f}bn",
          "", "Coverage needed: share of alt open interest held by the largest N markets on that day: "
          + ", ".join(f"top {n}: {df.loc[day, ~is_btc].sort_values(ascending=False).head(n).sum() / df.loc[day, ~is_btc].sum():.0%}"
                      for n in (50, 100, 200, 400, 800))]
    r = ratio()
    pd.DataFrame({"alt_btc_oi_ratio_all": r.round(4),
                  "top3": ratio(cols["ex"].isin(["Binance", "Bybit", "OKX"])).round(4)}).to_csv(os.path.join(OUT, "ratio.csv"))
    open(os.path.join(OUT, "summary.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
