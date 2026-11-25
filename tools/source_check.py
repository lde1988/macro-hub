"""Source check: fetch a small sample from every data source and report
whether it works from wherever this is running (a GitHub runner, usually).

Writes source_check.md and source_check.json into the folder given as the
first argument. Secrets are read from the environment, never printed, and
scrubbed from every piece of text before it is written.
"""
import datetime as dt
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import pandas as pd
import requests

FRED_KEY = os.environ.get("FRED_API_KEY", "").strip()
COINALYZE_KEY = os.environ.get("COINALYZE_API_KEY", "").strip()
SECRETS = [s for s in (FRED_KEY, COINALYZE_KEY, os.environ.get("NTFY_TOPIC", "").strip()) if s]
NOW = dt.datetime.now(dt.timezone.utc)
TODAY = NOW.date()

S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 (compatible; macro-hub source check)"
ROWS = []
NOTES = []


def scrub(text):
    text = str(text)
    for s in SECRETS:
        text = text.replace(s, "***")
    return re.sub(r"(api_key=)[^&\s'\"]+", r"\1***", text)


def get(url, **kw):
    kw.setdefault("timeout", 40)
    return S.get(url, **kw)


def age(d):
    if d is None:
        return ""
    if isinstance(d, str):
        d = dt.date.fromisoformat(d[:10])
    n = (TODAY - d).days
    return f"{n}d"


def row(sid, source, ok, value="", obs="", hist="", note=""):
    ROWS.append({
        "id": sid, "source": source, "ok": ok, "latest": scrub(value),
        "obs_date": str(obs)[:10] if obs else "", "age": age(obs) if obs else "",
        "history_from": str(hist)[:10] if hist else "", "note": scrub(note)[:300],
    })


def guard(sid, source):
    def deco(fn):
        try:
            fn()
        except Exception as e:  # report, never crash the whole check
            row(sid, source, False, note=f"{type(e).__name__}: {e}")
    return deco


# ---------------------------------------------------------------- FRED
FRED_IDS = [
    "SP500", "NASDAQ100", "SOFR", "IORB", "DGS2", "DGS10", "T10Y2Y", "DFF", "EFFR",
    "DFEDTARU", "DFEDTARL", "CPIAUCSL", "T5YIE", "WALCL", "ECBASSETSW", "JPNASSETS",
    "M2SL", "DEXUSEU", "DEXJPUS", "DEXUSUK", "DEXCAUS", "DEXSDUS", "DEXSZUS", "DEXCHUS",
    "DTWEXBGS", "BAMLH0A0HYM2", "BAMLH0A3HYC", "BAMLH0A1HYBB", "BAMLC0A4CBBB",
    "NFCI", "STLFSI4", "WLCFLPCL", "RPONTSYD", "WSHOBL", "WRESBAL",
]
FRED_SEARCHES = [
    "People's Bank of China total assets", "China M2", "euro area M3",
    "Japan M2", "standing repo facility", "discount window primary credit",
    "margin debt", "ICE BofA CCC option-adjusted spread",
]


def fred(path, **params):
    params.update(api_key=FRED_KEY, file_type="json")
    r = get("https://api.stlouisfed.org/fred/" + path, params=params)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:150]}")
    return r.json()


def check_fred():
    if not FRED_KEY:
        for sid in FRED_IDS:
            row(sid, "FRED", None, note="FRED_API_KEY not available here")
        return
    for sid in FRED_IDS:
        try:
            m = fred("series", series_id=sid)["seriess"][0]
            obs = fred("series/observations", series_id=sid, sort_order="desc", limit=10)["observations"]
            obs = [o for o in obs if o["value"] != "."]
            first = fred("series/observations", series_id=sid, sort_order="asc", limit=1)["observations"]
            row(sid, "FRED", True, f'{obs[0]["value"]} ({m["units_short"]})', obs[0]["date"],
                first[0]["date"] if first else "",
                f'{m["title"]} | {m["frequency_short"]} | updated {m["last_updated"][:10]}')
        except Exception as e:
            row(sid, "FRED", False, note=f"{type(e).__name__}: {e}")
    for q in FRED_SEARCHES:
        try:
            res = fred("series/search", search_text=q, limit=6, order_by="popularity", sort_order="desc")
            hits = [f'{x["id"]} "{x["title"][:60]}" {x["frequency_short"]} {x["units_short"][:20]} to {x["observation_end"]}'
                    for x in res["seriess"]]
            NOTES.append(f"FRED search '{q}': " + " || ".join(hits))
        except Exception as e:
            NOTES.append(scrub(f"FRED search '{q}' failed: {e}"))


# ---------------------------------------------------------------- Coinbase
def check_coinbase():
    r = get("https://api.exchange.coinbase.com/products/BTC-USD/candles", params={"granularity": 86400})
    r.raise_for_status()
    c = r.json()  # [time, low, high, open, close, volume], newest first
    done = [x for x in c if x[0] + 86400 <= NOW.timestamp()]
    d = dt.datetime.fromtimestamp(done[0][0], dt.timezone.utc).date()
    row("BTC-USD daily candles", "Coinbase", True, f"close {done[0][4]:,.0f}", d,
        note=f"{len(c)} candles per request; history pages back to 2015")
    sundays = [x for x in done if dt.datetime.fromtimestamp(x[0], dt.timezone.utc).weekday() == 6]
    wd = dt.datetime.fromtimestamp(sundays[0][0], dt.timezone.utc).date()
    row("BTC weekly close (Sunday candle)", "Coinbase", True, f"{sundays[0][4]:,.0f}", wd,
        note="close of the daily candle that ends Sunday 24:00 UTC")
    for p in ["SOL-USD", "SUI-USD", "NEAR-USD", "LINK-USD", "TAO-USD"]:
        try:
            t = get(f"https://api.exchange.coinbase.com/products/{p}/ticker").json()
            k = get(f"https://api.exchange.coinbase.com/products/{p}/candles",
                    params={"granularity": 86400, "start": "2019-01-01T00:00:00Z", "end": "2019-10-01T00:00:00Z"})
            row(p, "Coinbase", "price" in t, t.get("price", t), t.get("time", "")[:10],
                note="priced in BTC by dividing by BTC-USD")
        except Exception as e:
            row(p, "Coinbase", False, note=f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------- Bitview
BV = "https://bitview.space"
BV_SERIES = ["realized_price", "lth_realized_price", "sth_realized_price", "lth_sopr_24h",
             "lth_sopr_1w", "lth_sopr_1m", "realized_loss_sum_1m", "lth_realized_loss_sum_1m"]
BV_EPOCH = dt.date(2009, 1, 1)  # day1 index 0
REAL = {}


def check_bitview():
    v = get(BV + "/version").text.strip()[:40]
    NOTES.append(f"Bitview version: {v}")
    r = get(BV + "/api/series/bulk", params={"series": ",".join(BV_SERIES), "index": "day1", "start": -400})
    if r.status_code != 200:
        r = get(BV + "/api/series/bulk", params={"series": ",".join(BV_SERIES), "index": "day1",
                                                  "start": str(TODAY - dt.timedelta(days=400))})
    r.raise_for_status()
    for sid, blk in zip(BV_SERIES, r.json()):
        data = blk["data"]
        # the last element is today's still-moving value; the one before is the last finished day
        idx = blk["end"] - 2
        val = data[-2]
        d = BV_EPOCH + dt.timedelta(days=idx)
        note = f"today so far {data[-1]:,.4g}"
        if sid == "realized_price":
            REAL["bitview"] = (d, val)
        if sid == "realized_loss_sum_1m":
            s = pd.Series(data, index=[BV_EPOCH + dt.timedelta(days=blk["start"] + i) for i in range(len(data))])
            feb = s[(s.index >= dt.date(2026, 2, 1)) & (s.index <= dt.date(2026, 3, 15))]
            if len(feb):
                note += f"; Feb-Mar 2026 peak {feb.max():,.4g} on {feb.idxmax()}; now/peak = {val / feb.max():.2f}"
        if sid.startswith("lth_sopr"):
            s = pd.Series(data, index=[BV_EPOCH + dt.timedelta(days=blk["start"] + i) for i in range(len(data))])
            mid = s[(s.index >= dt.date(2026, 11, 10)) & (s.index <= dt.date(2026, 11, 20))]
            note += f"; 10-20 Nov 2026 range {mid.min():.3f}-{mid.max():.3f}"
        first = get(f"{BV}/api/series/{sid}/day1/len").text.strip()
        row(sid, "Bitview", True, f"{val:,.6g}", d, note=note + f"; {first} daily rows (from 2009)")


# ---------------------------------------------------------------- Coin Metrics
def check_coinmetrics():
    r = get("https://community-api.coinmetrics.io/v4/timeseries/asset-metrics",
            params={"assets": "btc", "metrics": "PriceUSD,CapMVRVCur", "frequency": "1d",
                    "page_size": 3, "paging_from": "end"})
    r.raise_for_status()
    x = r.json()["data"][-1]
    rp = float(x["PriceUSD"]) / float(x["CapMVRVCur"])
    d = dt.date.fromisoformat(x["time"][:10])
    REAL["coinmetrics"] = (d, rp)
    row("BTC realised price = PriceUSD / CapMVRVCur", "Coin Metrics community", True, f"{rp:,.0f}", d,
        "2010", f'price {float(x["PriceUSD"]):,.0f}, MVRV {float(x["CapMVRVCur"]):.3f}')
    r2 = get("https://community-api.coinmetrics.io/v4/timeseries/asset-metrics",
             params={"assets": "btc", "metrics": "CapRealUSD", "frequency": "1d", "page_size": 1})
    NOTES.append(f"Coin Metrics CapRealUSD (realised cap) on the free tier: HTTP {r2.status_code}")


def check_bgeometrics():
    r = get("https://bitcoin-data.com/v1/lth-sopr/last")
    j = r.json()
    row("lth-sopr", "BGeometrics (free)", r.status_code == 200, j.get("lthSopr"), j.get("d"),
        note="free plan withholds the latest 7 days" if j.get("delayed") else "")


# ---------------------------------------------------------------- DefiLlama
def check_defillama():
    r = get("https://stablecoins.llama.fi/stablecoincharts/all")
    r.raise_for_status()
    d = r.json()
    s = pd.Series({dt.datetime.fromtimestamp(int(x["date"]), dt.timezone.utc).date():
                   x["totalCirculatingUSD"]["peggedUSD"] for x in d if x.get("totalCirculatingUSD")})
    s_all = pd.Series({dt.datetime.fromtimestamp(int(x["date"]), dt.timezone.utc).date():
                       sum(x["totalCirculatingUSD"].values()) for x in d if x.get("totalCirculatingUSD")})
    last = s.index[-1]
    chg = s.iloc[-1] / s.iloc[-31] - 1
    row("stablecoin supply, USD-pegged", "DefiLlama", True, f"${s.iloc[-1] / 1e9:,.1f}bn; 30d {chg:+.1%}",
        last, s.index[0], f"all pegs ${s_all.iloc[-1] / 1e9:,.1f}bn; 30d {s_all.iloc[-1] / s_all.iloc[-31] - 1:+.1%}; "
        f"mid-Nov (15th) USD-pegged ${s.get(dt.date(2026, 11, 15), float('nan')) / 1e9:,.1f}bn")


# ---------------------------------------------------------------- ECB / DXY
def dxy_from_eur(r):
    usd = r["USD"]
    return (50.14348112 * usd ** -0.576 * (r["JPY"] / usd) ** 0.136 * (usd / r["GBP"]) ** -0.119
            * (r["CAD"] / usd) ** 0.091 * (r["SEK"] / usd) ** 0.042 * (r["CHF"] / usd) ** 0.036)


DXY = {}


def check_ecb():
    r = get("https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml")
    r.raise_for_status()
    root = ET.fromstring(r.content)
    for cube in root.iter("{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube"):
        if "time" in cube.attrib:
            rates = {c.attrib["currency"]: float(c.attrib["rate"]) for c in cube}
            DXY[cube.attrib["time"]] = dxy_from_eur(rates)
    days = sorted(DXY)
    row("ECB euro reference rates (USD JPY GBP CAD SEK CHF)", "ECB", True,
        f"computed DXY {DXY[days[-1]]:.2f}", days[-1], "1999",
        "set about 14:15 Frankfurt time each business day, published about 16:00")
    h = get("https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml", stream=True)
    NOTES.append(f"ECB full history file: HTTP {h.status_code}, {h.headers.get('content-length', '?')} bytes")
    NOTES.append("Computed DXY, last 8 fixings: " + ", ".join(f"{d} {DXY[d]:.2f}" for d in days[-8:]))


def check_dxy_published():
    """Verification only (not a production source): find a published DXY close to compare."""
    try:
        r = get("https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB", params={"range": "1mo", "interval": "1d"})
        j = r.json()["chart"]["result"][0]
        ts = [dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat() for t in j["timestamp"]]
        cl = j["indicators"]["quote"][0]["close"]
        pub = {d: c for d, c in zip(ts, cl) if c}
        cmp_ = [(d, pub[d], DXY[d], DXY[d] - pub[d]) for d in sorted(pub) if d in DXY]
        worst = max(abs(x[3]) for x in cmp_)
        NOTES.append("DXY check, published close (Yahoo DX-Y.NYB, verification only) vs computed from ECB: "
                     + ", ".join(f"{d} {p:.2f}/{c:.2f} ({g:+.2f})" for d, p, c, g in cmp_[-10:])
                     + f" | worst gap over {len(cmp_)} days: {worst:.2f}")
        row("DXY published close (verification only)", "Yahoo chart", True, f"{cl[-1]:.2f}", ts[-1],
            note=f"worst gap vs computed over {len(cmp_)} days: {worst:.2f}")
    except Exception as e:
        row("DXY published close (verification only)", "Yahoo chart", False, note=f"{type(e).__name__}: {e}")
    try:
        r = get("https://stooq.com/q/d/l/", params={"s": "dx.f", "i": "d"})
        df = pd.read_csv(io.StringIO(r.text))
        tail = df.tail(15)
        cmp_ = [(d, c, DXY[d]) for d, c in zip(tail["Date"], tail["Close"]) if d in DXY]
        NOTES.append("DXY check, Stooq dx.f vs computed: " + ", ".join(f"{d} {p:.2f}/{c:.2f} ({c - p:+.2f})" for d, p, c in cmp_))
        row("DXY future dx.f (verification only)", "Stooq", True, f"{df['Close'].iloc[-1]:.2f}", df["Date"].iloc[-1])
    except Exception as e:
        row("DXY future dx.f (verification only)", "Stooq", False, note=f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------- FINRA
def check_finra():
    r = get("https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx")
    r.raise_for_status()
    df = pd.read_excel(io.BytesIO(r.content))
    df = df.rename(columns={df.columns[0]: "month", df.columns[1]: "debit"})[["month", "debit"]].dropna()
    df["month"] = pd.to_datetime(df["month"], format="mixed")
    s = df.set_index("month")["debit"].astype(float).sort_index()
    ann = (s / s.shift(3)) ** 4 - 1
    pick = {m.strftime("%b %Y"): f"{ann[m]:+.1%}" for m in ann.index[-6:]}
    row("margin debt (debit balances, $m)", "FINRA xlsx", True, f"{s.iloc[-1]:,.0f}; 3m annualised {ann.iloc[-1]:+.1%}",
        s.index[-1].date(), s.index[0].date(), f"3m annualised, last 6 months: {pick}")


# ---------------------------------------------------------------- Treasury
def check_treasury():
    r = get("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/buybacks_operations",
            params={"page[size]": 300, "sort": "-operation_date"})
    r.raise_for_status()
    d = pd.DataFrame(r.json()["data"])
    d["amt"] = pd.to_numeric(d["total_par_amt_accepted"], errors="coerce")
    d["operation_date"] = pd.to_datetime(d["operation_date"])
    m = d.groupby(d["operation_date"].dt.to_period("M"))["amt"].sum().tail(8) / 1e9
    row("buyback operations (par accepted)", "Treasury fiscal data", True,
        f"${d['amt'].iloc[0] / 1e9:.2f}bn latest op", d["operation_date"].iloc[0].date(),
        d["operation_date"].min().date(),
        "monthly $bn: " + ", ".join(f"{k} {v:.1f}" for k, v in m.items()) + f" | types: {sorted(d['operation_type'].unique())}")


# ---------------------------------------------------------------- Nasdaq
def check_nasdaq():
    for sym, ac in [("CRWV", "stocks"), ("ORCL", "stocks"), ("BIZD", "etf"), ("KRE", "etf"), ("NDX", "index"),
                    ("NBIS", "stocks"), ("APLD", "stocks"), ("IREN", "stocks")]:
        try:
            r = get(f"https://api.nasdaq.com/api/quote/{sym}/historical",
                    params={"assetclass": ac, "fromdate": "2015-01-01", "todate": TODAY.isoformat(), "limit": 9999})
            rows = r.json()["data"]["tradesTable"]["rows"]
            d = dt.datetime.strptime(rows[0]["date"], "%m/%d/%Y").date()
            h = dt.datetime.strptime(rows[-1]["date"], "%m/%d/%Y").date()
            row(sym, "Nasdaq quote service (unofficial)", True, rows[0]["close"], d, h,
                "close is not adjusted for dividends")
        except Exception as e:
            row(sym, "Nasdaq quote service (unofficial)", False, note=f"{type(e).__name__}: {e}")


def check_stooq():
    for sym in ["kre.us", "crwv.us"]:
        try:
            r = get("https://stooq.com/q/d/l/", params={"s": sym, "i": "d"})
            df = pd.read_csv(io.StringIO(r.text))
            row(sym, "Stooq", True, df["Close"].iloc[-1], df["Date"].iloc[-1], df["Date"].iloc[0])
        except Exception as e:
            row(sym, "Stooq", False, note=f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------- CoinGecko
def check_coingecko():
    r = get("https://api.coingecko.com/api/v3/global")
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    d = r.json()["data"]
    tot = d["total_market_cap"]["usd"]
    dom = d["market_cap_percentage"]["btc"]
    row("BTC dominance / total crypto value", "CoinGecko (no key)", True,
        f"dominance {dom:.1f}%; total ${tot / 1e12:.2f}tn; alts ${tot * (1 - dom / 100) / 1e12:.2f}tn",
        dt.datetime.fromtimestamp(d["updated_at"], dt.timezone.utc).date(),
        note="current value only; no free history. alts here include stablecoins")


# ---------------------------------------------------------------- Coinalyze
def check_coinalyze():
    if not COINALYZE_KEY:
        row("funding rate, open interest", "Coinalyze", None, note="COINALYZE_API_KEY not set yet")
        return
    H = {"api_key": COINALYZE_KEY}
    base = "https://api.coinalyze.net/v1"
    mk = get(base + "/future-markets", headers=H)
    if mk.status_code != 200:
        raise RuntimeError(f"HTTP {mk.status_code} {mk.text[:100]}")
    mk = mk.json()
    perp = [m for m in mk if m.get("is_perpetual")]
    bases = {}
    for m in perp:
        bases.setdefault(m["base_asset"], []).append(m["symbol"])
    NOTES.append(f"Coinalyze: {len(mk)} futures markets, {len(perp)} perpetuals, {len(bases)} base assets; "
                 f"BTC perps: {len(bases.get('BTC', []))}; examples {bases.get('BTC', [])[:12]}")
    ex = get(base + "/exchanges", headers=H).json()
    NOTES.append("Coinalyze exchanges: " + ", ".join(f'{e["code"]}={e["name"]}' for e in ex))
    t1 = int(NOW.timestamp())
    for label, t0 in [("5 years", t1 - 5 * 365 * 86400), ("60 days", t1 - 60 * 86400)]:
        for kind, sym in [("funding-rate-history", "BTCUSDT_PERP.A"), ("open-interest-history", "BTCUSDT_PERP.A"),
                          ("open-interest-history", "ETHUSDT_PERP.A"), ("open-interest-history", "SOLUSDT_PERP.A")]:
            r = get(f"{base}/{kind}", headers=H,
                    params={"symbols": sym, "interval": "daily", "from": t0, "to": t1, "convert_to_usd": "true"})
            try:
                h = r.json()[0]["history"]
                d0 = dt.datetime.fromtimestamp(h[0]["t"], dt.timezone.utc).date()
                d1 = dt.datetime.fromtimestamp(h[-1]["t"], dt.timezone.utc).date()
                if label == "5 years":
                    row(f"{kind} {sym}", "Coinalyze", True, h[-1]["c"], d1, d0, f"{len(h)} daily rows asked back {label}")
            except Exception as e:
                row(f"{kind} {sym} ({label})", "Coinalyze", False, note=f"HTTP {r.status_code} {r.text[:120]}")
    NOTES.append("Coinalyze rate limit headers: " + str({k: v for k, v in r.headers.items() if "limit" in k.lower()}))


def check_misc():
    r = get("https://ntfy.sh/v1/health")
    row("ntfy health (no push sent)", "ntfy.sh", r.status_code == 200, r.text.strip()[:40])
    try:
        r = get("https://fapi.binance.com/fapi/v1/premiumIndex", params={"symbol": "BTCUSDT"})
        row("Binance futures (expected blocked)", "Binance", r.status_code == 200, f"HTTP {r.status_code}",
            note=r.text[:120])
    except Exception as e:
        row("Binance futures (expected blocked)", "Binance", False, note=f"{type(e).__name__}")
    try:
        ip = get("https://api.github.com/meta").status_code
        NOTES.append(f"Runner: {os.environ.get('RUNNER_OS', 'not a runner')} {os.environ.get('RUNNER_NAME', '')}; time {NOW.isoformat()[:19]}Z")
    except Exception:
        pass


CHECKS = [("FRED", check_fred), ("Coinbase", check_coinbase), ("Bitview", check_bitview),
          ("Coin Metrics", check_coinmetrics), ("BGeometrics", check_bgeometrics), ("DefiLlama", check_defillama),
          ("ECB", check_ecb), ("DXY published", check_dxy_published), ("FINRA", check_finra),
          ("Treasury", check_treasury), ("Nasdaq", check_nasdaq), ("Stooq", check_stooq),
          ("CoinGecko", check_coingecko), ("Coinalyze", check_coinalyze), ("misc", check_misc)]


def main(out):
    os.makedirs(out, exist_ok=True)
    for name, fn in CHECKS:
        try:
            fn()
        except Exception as e:
            row(name, name, False, note=f"{type(e).__name__}: {e}")
    if "bitview" in REAL and "coinmetrics" in REAL:
        b, c = REAL["bitview"], REAL["coinmetrics"]
        NOTES.append(f"Realised price cross-check: Bitview {b[1]:,.0f} ({b[0]}) vs Coin Metrics {c[1]:,.0f} ({c[0]}): "
                     f"gap {abs(b[1] / c[1] - 1):.2%}")
    mark = {True: "yes", False: "NO", None: "not tested"}
    lines = [f"Source check run {NOW.isoformat()[:19]}Z on {os.environ.get('RUNNER_NAME', 'local machine')}", "",
             "| id | source | works here? | latest value | value date | age | history from | note |",
             "|---|---|---|---|---|---|---|---|"]
    for r in ROWS:
        lines.append(f'| {r["id"]} | {r["source"]} | {mark[r["ok"]]} | {r["latest"]} | {r["obs_date"]} | {r["age"]} '
                     f'| {r["history_from"]} | {r["note"].replace("|", "/")} |')
    lines += ["", "Notes:"] + [f"- {scrub(n)}" for n in NOTES]
    text = scrub("\n".join(lines)) + "\n"
    open(os.path.join(out, "source_check.md"), "w").write(text)
    json.dump({"run": NOW.isoformat(), "rows": ROWS, "notes": [scrub(n) for n in NOTES]},
              open(os.path.join(out, "source_check.json"), "w"), indent=1)
    print(text)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "out")
