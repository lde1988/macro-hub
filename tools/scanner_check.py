"""One-off, read-only check for the coin scanner plan (reports/18). Free sources only, no keys.
Writes a markdown table of what each free source covers for today's top 100 coins."""
import json
import sys
import time
from pathlib import Path

import requests

S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 (compatible; macro-hub scanner check)"
OUT = []
MINE = ["bitcoin", "ethereum", "solana", "sui", "chainlink", "near", "zcash", "hyperliquid", "walrus-2", "deep"]


def get(url, **kw):
    for i in range(4):
        try:
            r = S.get(url, timeout=60, **kw)
        except Exception as e:  # noqa: BLE001
            r = None
            err = type(e).__name__
        if r is not None and r.status_code == 429:
            time.sleep(30 * (i + 1))
            continue
        return r if r is not None else type("R", (), {"status_code": err, "text": "", "json": lambda s: None})()
    return r


def p(*a):
    OUT.append(" ".join(str(x) for x in a))


# ---- CoinGecko: top coins and categories
r = get("https://api.coingecko.com/api/v3/coins/markets", params={"vs_currency": "usd", "order": "market_cap_desc",
        "per_page": 250, "page": 1, "price_change_percentage": "7d"})
markets = r.json() if r.status_code == 200 else []
p(f"## CoinGecko markets: HTTP {r.status_code}, {len(markets)} coins")
time.sleep(8)
cats = get("https://api.coingecko.com/api/v3/coins/categories/list")
catlist = cats.json() if cats.status_code == 200 else []
p(f"categories list: HTTP {cats.status_code}, {len(catlist)} categories")
want = ["stablecoins", "wrapped-tokens", "liquid-staking-tokens", "liquid-staking", "liquid-restaking-tokens",
        "bridged-tokens", "exchange-based-tokens", "meme-token", "tokenized-gold", "tokenized-commodities",
        "crypto-backed-tokens", "bridged-stablecoins", "yield-bearing-stablecoins", "usd-stablecoin",
        "restaking", "tokenized-treasury-bonds-t-bills", "real-world-assets-rwa"]
ids = {c["category_id"] for c in catlist}
p("wanted categories present:", {w: w in ids for w in want})
members = {}
for c in want:
    if c not in ids:
        continue
    time.sleep(8)
    rr = get("https://api.coingecko.com/api/v3/coins/markets", params={"vs_currency": "usd", "category": c, "per_page": 250,
             "order": "market_cap_desc"})
    members[c] = {x["id"] for x in rr.json()} if rr.status_code == 200 else None
    p(f"category {c}: HTTP {rr.status_code}, {len(members[c] or [])} coins")
excl_cats = ["stablecoins", "wrapped-tokens", "liquid-staking-tokens", "liquid-staking", "liquid-restaking-tokens",
             "bridged-tokens", "exchange-based-tokens", "tokenized-gold", "tokenized-commodities", "crypto-backed-tokens",
             "bridged-stablecoins", "yield-bearing-stablecoins", "usd-stablecoin", "tokenized-treasury-bonds-t-bills"]
rows = []
for x in markets:
    why = [c for c in excl_cats if members.get(c) and x["id"] in members[c]]
    rows.append({"id": x["id"], "sym": x["symbol"].upper(), "name": x["name"], "rank": x.get("market_cap_rank"),
                 "mcap": x.get("market_cap"), "circ": x.get("circulating_supply"), "total": x.get("total_supply"),
                 "max": x.get("max_supply"), "fdv": x.get("fully_diluted_valuation"), "excluded": why,
                 "meme": bool(members.get("meme-token") and x["id"] in members["meme-token"])})
kept = [r for r in rows if not r["excluded"]][:100]
for m in MINE:
    if m not in {r["id"] for r in kept}:
        hit = next((r for r in rows if r["id"] == m), None)
        kept.append(hit or {"id": m, "sym": m, "name": m, "rank": None, "excluded": [], "meme": False})
p(f"\n### Universe: {len(kept)} coins after exclusions (+ owner's 10)")
p("Excluded from the top 250 (first 40): " + "; ".join(f"{r['sym']} ({','.join(r['excluded'])})" for r in rows if r["excluded"])[:3000])
p("Memecoins kept but labelled: " + ", ".join(r["sym"] for r in kept if r.get("meme")))
p("Universe: " + ", ".join(f"{r['sym']}" for r in kept))

# ---- price history sources
time.sleep(8)
r = get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart", params={"vs_currency": "usd", "days": "max", "interval": "daily"})
p(f"\n## CoinGecko history days=max (keyless): HTTP {r.status_code} {r.text[:200] if r.status_code != 200 else str(len(r.json().get('prices', []))) + ' days'}")
time.sleep(8)
r = get("https://api.coingecko.com/api/v3/coins/solana/market_chart", params={"vs_currency": "usd", "days": 365, "interval": "daily"})
j = r.json() if r.status_code == 200 else {}
p(f"CoinGecko history days=365: HTTP {r.status_code}, {len(j.get('prices', []))} prices, {len(j.get('market_caps', []))} market caps (implied supply = cap/price)")

r = get("https://community-api.coinmetrics.io/v4/catalog-all/asset-metrics", params={"metrics": "PriceUSD,SplyCur"})
cm = {}
if r.status_code == 200:
    for m in r.json().get("data", []):
        for a in m.get("frequencies", []) and m.get("assets", []) or []:
            pass
    for m in r.json().get("data", []):
        for a in m.get("assets", []):
            cm.setdefault(a["asset"] if isinstance(a, dict) else a, set()).add(m["metric"])
p(f"Coin Metrics catalog: HTTP {r.status_code}, {len(cm)} assets")
r2 = get("https://community-api.coinmetrics.io/v4/catalog-all/assets")
allassets = {a["asset"]: a for a in (r2.json().get("data", []) if r2.status_code == 200 else [])}
p(f"Coin Metrics assets list: HTTP {r2.status_code}, {len(allassets)}; sample fields: {list(next(iter(allassets.values()), {}).keys())[:12]}")
r3 = get("https://api.exchange.coinbase.com/products")
cb = {x["base_currency"].upper() for x in (r3.json() if r3.status_code == 200 else []) if x.get("quote_currency") == "USD"}
p(f"Coinbase USD pairs: HTTP {r3.status_code}, {len(cb)} coins")

# Coin Metrics metric availability per asset via a small time-series test on the universe
syms = [r["sym"].lower() for r in kept]
have_price, have_sup = set(), set()
for i in range(0, len(syms), 40):
    chunk = ",".join(syms[i:i + 40])
    for metric, store in (("PriceUSD", have_price), ("SplyCur", have_sup)):
        rr = get("https://community-api.coinmetrics.io/v4/timeseries/asset-metrics",
                 params={"assets": chunk, "metrics": metric, "start_time": "2026-11-20", "end_time": "2026-11-25",
                         "frequency": "1d", "page_size": 10000, "ignore_unsupported_errors": "true"})
        if rr.status_code == 200:
            for row in rr.json().get("data", []):
                if row.get(metric):
                    store.add(row["asset"])
        time.sleep(1)
first = {}
for s in sorted(have_price):
    rr = get("https://community-api.coinmetrics.io/v4/timeseries/asset-metrics",
             params={"assets": s, "metrics": "PriceUSD", "frequency": "1d", "page_size": 1, "paging_from": "start"})
    if rr.status_code == 200 and rr.json().get("data"):
        first[s] = rr.json()["data"][0]["time"][:10]
p(f"Coin Metrics free daily price for {len(have_price)} of {len(syms)} universe coins; supply for {len(have_sup)}")
p(f"Coinbase USD pair for {sum(1 for s in syms if s.upper() in cb)} of {len(syms)}")
p(f"Neither: {', '.join(s.upper() for s in syms if s not in have_price and s.upper() not in cb)}")
p("Coin Metrics price history starts: " + ", ".join(f"{k.upper()} {v[:4]}" for k, v in sorted(first.items(), key=lambda kv: kv[1])))
p(f"History back to 1 Jan 2020 (Coin Metrics): {sum(1 for v in first.values() if v <= '2020-01-01')} coins")

# ---- DefiLlama: fees, revenue, holders revenue; unlocks
rr = get("https://api.llama.fi/protocols")
protos = rr.json() if rr.status_code == 200 else []
gecko = {}
for x in protos:
    if x.get("gecko_id"):
        gecko.setdefault(x["gecko_id"], []).append(x.get("slug") or x.get("name"))
rch = get("https://api.llama.fi/v2/chains")
chains = {x.get("gecko_id"): x.get("name") for x in (rch.json() if rch.status_code == 200 else []) if x.get("gecko_id")}
p(f"\n## DefiLlama: protocols HTTP {rr.status_code} ({len(protos)}), chains HTTP {rch.status_code} ({len(chains)})")
cov = {}
for dt in ("dailyFees", "dailyRevenue", "dailyHoldersRevenue"):
    rr = get("https://api.llama.fi/overview/fees", params={"excludeTotalDataChart": "true", "excludeTotalDataChartBreakdown": "true",
             "dataType": dt})
    got = rr.json().get("protocols", []) if rr.status_code == 200 else []
    ids_ = set()
    for x in got:
        if x.get("total30d"):
            for k in ("gecko_id",):
                if x.get(k):
                    ids_.add(x[k])
            if x.get("slug"):
                ids_.add("slug:" + x["slug"])
            if x.get("name"):
                ids_.add("name:" + x["name"].lower())
    cov[dt] = ids_
    p(f"overview/fees {dt}: HTTP {rr.status_code}, {len(got)} entries, {sum(1 for x in got if x.get('total30d'))} with 30-day totals")
rr = get("https://api.llama.fi/overview/fees", params={"excludeTotalDataChart": "true", "excludeTotalDataChartBreakdown": "true",
         "dataType": "dailyFees"})
chainfees = {x.get("name", "").lower() for x in (rr.json().get("protocols", []) if rr.status_code == 200 else []) if x.get("category") == "Chain"}


def covered(r, dt):
    gid = r["id"]
    names = {"name:" + r["name"].lower(), "slug:" + r["name"].lower().replace(" ", "-")} | {"slug:" + s for s in gecko.get(gid, [])}
    return gid in cov[dt] or bool(names & cov[dt]) or (chains.get(gid, "").lower() in {n[5:] for n in cov[dt] if n.startswith("name:")})


for dt in ("dailyFees", "dailyRevenue", "dailyHoldersRevenue"):
    hit = [r["sym"] for r in kept if covered(r, dt)]
    p(f"Universe coins with {dt} (matched by CoinGecko id, name or chain): {len(hit)}: {', '.join(hit)}")
p(f"Owner's 10: " + "; ".join(f"{r['sym']}: " + "/".join(k for k in ('dailyFees', 'dailyRevenue', 'dailyHoldersRevenue')
  if covered(r, k)) for r in kept if r["id"] in MINE))
for u in ("https://api.llama.fi/emissions", "https://api.llama.fi/emission/hyperliquid", "https://defillama-datasets.llama.fi/emissionsProtocolsList"):
    rr = get(u)
    p(f"Unlocks {u}: HTTP {rr.status_code} {(rr.text or '')[:120]!r}")
Path(sys.argv[1] if len(sys.argv) > 1 else "out").mkdir(exist_ok=True)
(Path(sys.argv[1] if len(sys.argv) > 1 else "out") / "scanner_check.md").write_text("\n".join(OUT) + "\n")
(Path(sys.argv[1] if len(sys.argv) > 1 else "out") / "universe.json").write_text(json.dumps(kept, indent=1))
print("\n".join(OUT))
