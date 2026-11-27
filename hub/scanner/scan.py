"""The daily coin-scanner job (reports/18).

    python -m hub.scanner.scan --data data [--no-push]

Reads the hub's own regime from the data branch (state/hub.json: the weekly trend exit), fetches free data, rates
every coin, and writes ONLY under data/scanner/: prices, supply, a point-in-time snapshot per day, latest.json for
the tab, and its own alert state. Context only: it never changes the reading, a dial, a band or a rule.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

import pandas as pd
import yaml

from hub import notify
from hub.scanner import data as D, quality as Q, trend as T, universe as U
from hub.store import Store
from hub.util import ROOT, Web, utcnow

SNAP_COLS = ["date", "id", "symbol", "rank", "price", "market_cap", "sector", "meme", "exchange", "owner",
             "own_state", "own_since", "vs_btc_state", "vs_btc_since", "dual_bull", "revenue_kind", "revenue_90d",
             "revenue_growth", "revenue_fixed", "revenue_rank", "revenue_of", "revenue_relative", "supply_growth",
             "float_share", "dilution", "holders_share", "accrual", "quality_pass", "parts_scored", "regime"]


def load_cfg():
    return yaml.safe_load(open(ROOT / "config" / "scanner.yaml"))


def regime(data):
    """The hub's weekly trend exit (decision A), the date it began, and the short-term holder cost line."""
    st = D.load_json(Path(data) / "state" / "hub.json", {})
    state = ((st.get("summary") or {}).get("trend_exit")) or "NO DATA"
    since = (st.get("since") or {}).get("trend_exit")
    line = None
    try:
        s = Store(data).series("BV_STH_REALIZED_PRICE")
        line = float(s.iloc[-1]) if len(s) else None
    except Exception:  # noqa: BLE001
        pass
    return {"on": state == "RISK-ON", "state": state, "since": since, "line": line,
            "line_name": "short-term holder cost (Bitview)"}


def update_prices(api, folder, rows, today, log):
    """Keep scanner/prices/<id>.csv and scanner/supply/<id>.csv up to date. Returns {id: Series}."""
    prices, supplies = {}, {}
    pdir, sdir = Path(folder) / "prices", Path(folder) / "supply"
    cm_ids = D.load_json(Path(folder) / "coinmetrics_ids.json", {})
    for r in rows:
        cid = r["id"]
        p, s = D.read_csv(pdir / f"{cid}.csv", "close"), D.read_csv(sdir / f"{cid}.csv", "circulating")
        if len(p) == 0:                                    # first time: CoinGecko's free year, then Coin Metrics if same coin
            try:
                pr, sup = D.cg_year(api, cid)
            except Exception as e:  # noqa: BLE001
                log.append(f"{r['symbol']}: CoinGecko history failed: {D.safe(e)}")
                prices[cid], supplies[cid] = p, s
                continue
            p, s = pr, sup
            sym = r["symbol"].lower()
            try:
                cm = D.cm_prices(api, [sym], "2015-01-01").get(sym)
            except Exception:  # noqa: BLE001
                cm = None
            if cm is not None and D.same_coin(cm, pr):
                cm_ids[cid] = sym
                p = D.merge(pr, cm[cm.index < pr.index.min()]) if len(pr) else cm
                log.append(f"{r['symbol']}: history from Coin Metrics since {cm.index.min():%Y-%m-%d}")
            else:
                log.append(f"{r['symbol']}: history from CoinGecko's free year ({len(pr)} days)")
        prices[cid], supplies[cid] = p, s
    # new closes: Coin Metrics in one call for the coins it has, CoinGecko for the rest
    last = today - pd.Timedelta(days=1)
    cm_need = {cid: sym for cid, sym in cm_ids.items() if cid in prices and (not len(prices[cid]) or prices[cid].index.max() < last)}
    if cm_need:
        start = min(prices[c].index.max() for c in cm_need if len(prices[c])) if any(len(prices[c]) for c in cm_need) else last
        got = D.cm_prices(api, sorted(set(cm_need.values())), (start + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
        for cid, sym in cm_need.items():
            if sym in got:
                prices[cid] = D.merge(prices[cid], got[sym][got[sym].index < today])
    for r in rows:
        cid = r["id"]
        p = prices[cid]
        if len(p) and p.index.max() >= last:
            continue
        gap = (today - p.index.max()).days if len(p) else 365
        try:
            pr, sup = D.cg_year(api, cid, days=min(max(gap + 1, 2), 365))
        except Exception as e:  # noqa: BLE001
            log.append(f"{r['symbol']}: CoinGecko update failed: {D.safe(e)}")
            continue
        prices[cid] = D.merge(p, pr[pr.index < today])
        supplies[cid] = D.merge(supplies[cid], sup[sup.index < today])
    for r in rows:                                          # today's circulating supply from the markets call
        if r.get("circulating"):
            supplies[r["id"]] = D.merge(pd.Series({last: float(r["circulating"])}), supplies[r["id"]])
        D.write_series(pdir / f"{r['id']}.csv", prices[r["id"]], "close")
        D.write_series(sdir / f"{r['id']}.csv", supplies[r["id"]], "circulating")
    D.save_json(Path(folder) / "coinmetrics_ids.json", cm_ids)
    return prices, supplies


def rate(rows, prices, supplies, revs, cfg, reg, today):
    """Every coin's ratings, quality and the table row. Pure: no network."""
    tc, qc = cfg["trend"], cfg["quality"]
    prices = {k: D.clean_prices(v)[0] for k, v in prices.items()}      # impossible jumps never reach a rating
    btc = prices.get("bitcoin", pd.Series(dtype=float))
    growths, out = {}, []
    for r in rows:
        rv = revs.get(r["id"])
        g, total = Q.revenue_growth(rv["revenue"], qc["revenue_days"], qc["min_revenue_usd_90d"]) if rv else (None, None)
        growths[r["id"]] = g
    rel = Q.relative_marks(growths) if qc.get("revenue_relative") else {}
    for r in rows:
        p = prices.get(r["id"], pd.Series(dtype=float))
        own = T.rating(p, tc)
        vs = T.rating((p / btc).dropna(), tc) if r["id"] != "bitcoin" and len(btc) else \
            {"state": None, "since": None, "why": "Bitcoin itself"}
        rv = revs.get(r["id"])
        g = growths[r["id"]]
        total = None
        holders_share = acc = None
        if rv:
            _, total = Q.revenue_growth(rv["revenue"], qc["revenue_days"], qc["min_revenue_usd_90d"])
            h = rv.get("holders")
            if h is not None and total:
                acc, holders_share = Q.accrual(total, float(h.sort_index().iloc[-qc["revenue_days"]:].sum()), qc)
        rmark, rank, of = rel.get(r["id"], (None, None, None))
        dil, sgrowth, fshare = Q.dilution(supplies.get(r["id"]), r.get("circulating"), r.get("max") or r.get("total"), qc)
        revenue_part = rmark if qc.get("revenue_relative") else Q.fixed_mark(g, qc)
        ok, scored = Q.passes([revenue_part, dil, acc])
        since_own = own.get("since")
        pct_since = None
        if since_own is not None and len(p):
            base = p[p.index <= pd.Timestamp(since_own)]
            pct_since = (float(p.iloc[-1]) / float(base.iloc[-1]) - 1) * 100 if len(base) else None
        days = [d for d in (own.get("since"), vs.get("since")) if d is not None]
        last_change = max(days) if days else None
        out.append({**{k: r[k] for k in ("id", "symbol", "name", "rank", "sector", "meme", "exchange", "owner", "market_cap")},
                    "price": float(p.iloc[-1]) if len(p) else r.get("price"), "price_date": p.index[-1].strftime("%Y-%m-%d") if len(p) else None,
                    "change_7d": r.get("change_7d"), "pct_since_signal": round(pct_since, 1) if pct_since is not None else None,
                    "own": {k: own.get(k) for k in ("state", "since", "why", "tests", "detail")},
                    "vs_btc": {k: vs.get(k) for k in ("state", "since", "why", "tests", "detail")},
                    "days_since": (pd.Timestamp(today) - pd.Timestamp(last_change)).days if last_change is not None else None,
                    "dual_bull": T.dual_bull(own.get("state"), vs.get("state")),
                    "quality": {"revenue_kind": rv["kind"] if rv else None, "revenue_90d": total,
                                "revenue_growth": g, "revenue_fixed": Q.fixed_mark(g, qc), "revenue_rank": rank, "revenue_of": of,
                                "revenue_relative": rmark, "supply_growth": sgrowth, "float_share": fshare, "dilution": dil,
                                "holders_share": holders_share, "accrual": acc, "pass": ok, "parts_scored": scored}})
    for x in out:
        for side in ("own", "vs_btc"):
            if x[side]["since"] is not None:
                x[side]["since"] = pd.Timestamp(x[side]["since"]).strftime("%Y-%m-%d")
    return out, Q.median(list(growths.values()))


def watchlist(table, prices, reg, n):
    """While the regime is OFF: the coins holding up best against Bitcoin since it turned OFF."""
    btc = prices.get("bitcoin")
    if btc is None or not len(btc):
        return []
    start = pd.Timestamp(reg["since"][:10]) if reg.get("since") else btc.index[-1] - pd.Timedelta(days=90)
    rows = []
    for x in table:
        p = prices.get(x["id"])
        if x["id"] == "bitcoin" or p is None or not len(p):
            continue
        ratio = (p / btc).dropna()
        base = ratio[ratio.index <= start]
        if not len(base) or not len(ratio):
            continue
        rows.append({"id": x["id"], "symbol": x["symbol"], "vs_btc_since_off_pct": round((float(ratio.iloc[-1]) / float(base.iloc[-1]) - 1) * 100, 1),
                     "vs_btc_state": x["vs_btc"]["state"], "meme": x["meme"], "exchange": x["exchange"], "owner": x["owner"]})
    rows.sort(key=lambda r: -r["vs_btc_since_off_pct"])
    return rows[:n]


def snapshot_rows(table, reg, day):
    out = []
    for x in table:
        q = x["quality"]
        out.append({"date": day, "id": x["id"], "symbol": x["symbol"], "rank": x["rank"], "price": x["price"],
                    "market_cap": x["market_cap"], "sector": x["sector"], "meme": x["meme"], "exchange": x["exchange"],
                    "owner": x["owner"], "own_state": x["own"]["state"], "own_since": x["own"]["since"],
                    "vs_btc_state": x["vs_btc"]["state"], "vs_btc_since": x["vs_btc"]["since"], "dual_bull": x["dual_bull"],
                    "revenue_kind": q["revenue_kind"], "revenue_90d": q["revenue_90d"], "revenue_growth": q["revenue_growth"],
                    "revenue_fixed": q["revenue_fixed"], "revenue_rank": q["revenue_rank"], "revenue_of": q["revenue_of"],
                    "revenue_relative": q["revenue_relative"], "supply_growth": q["supply_growth"], "float_share": q["float_share"],
                    "dilution": q["dilution"], "holders_share": q["holders_share"], "accrual": q["accrual"],
                    "quality_pass": q["pass"], "parts_scored": q["parts_scored"], "regime": reg["state"]})
    return pd.DataFrame(out, columns=SNAP_COLS)


def alert(table, reg, state, day, cfg):
    """At most one push a day: coins that NEWLY became Dual Bull and pass quality, on a day the regime is ON."""
    now_ok = sorted(x["id"] for x in table if x["dual_bull"] and x["quality"]["pass"])
    new = [x for x in table if x["id"] in set(now_ok) - set(state.get("dual_ok", []))]
    push = None
    if reg["on"] and new and state.get("last_alert") != day:
        names = ", ".join(f"{x['symbol']} ({x['sector']}, quality {x['quality']['parts_scored']} part"
                          f"{'s' if x['quality']['parts_scored'] != 1 else ''} scored)" for x in new[:8])
        push = {"title": "macro-hub: coin scanner", "priority": cfg["alerts"]["priority"], "tags": ["mag"],
                "message": f"New Dual Bull with quality, Bitcoin regime ON: {names}. Context, not advice; "
                           "it never changes the buy / hold reading."}
        state["last_alert"] = day
    state["dual_ok"] = now_ok
    return push, state


def main(argv=None, now=None, web=None, sender=None, sleep=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args(argv)
    now = now or utcnow()
    today = pd.Timestamp(now).tz_localize(None).normalize() if pd.Timestamp(now).tzinfo else pd.Timestamp(now).normalize()
    day = (today - pd.Timedelta(days=1)).strftime("%Y-%m-%d")      # the snapshot is for the last finished day
    cfg = load_cfg()
    folder = Path(a.data) / "scanner"
    api = D.Free(web or Web(), sleep=sleep or __import__("time").sleep)
    log = []
    u = cfg["universe"]
    mk = D.markets(api, u["fetch_n"], u["owner_coins"])
    cats_p = folder / "categories.json"
    cats = D.load_json(cats_p, {})
    want = sorted(set(u["exclude_categories"]) | {u["meme_category"]} | {c for v in cfg["sectors"].values() for c in v})
    if not cats or (today - pd.Timestamp(cats.get("fetched", "2000-01-01"))).days >= u["categories_refresh_days"]:
        got = D.categories(api, want)
        cats = {"fetched": today.strftime("%Y-%m-%d"), "members": {k: v for k, v in got.items() if v is not None}}
        D.save_json(cats_p, cats)
    members = {k: set(v) for k, v in cats.get("members", {}).items()}
    coin_cats = {}
    for c, ids in members.items():
        for i in ids:
            coin_cats.setdefault(i, []).append(c)
    old = {p.stem: D.read_csv(p, "close") for p in (folder / "prices").glob("*.csv")} if (folder / "prices").exists() else {}
    rows, excluded, missing = U.build(mk, members, cfg, prices=old, coin_cats=coin_cats)
    if missing:
        log.append(f"owner's coins not found on CoinGecko: {missing}")
    prices, supplies = update_prices(api, folder, rows, today, log)
    rows2, excluded2, _ = U.build(mk, members, cfg, prices=prices, coin_cats=coin_cats)   # pegged test on fresh prices
    if len(excluded2) > len(excluded):
        rows, excluded = rows2, excluded2
    lmap = {**D.llama_maps(api), **cfg.get("defillama_map", {})}
    revs = {}
    for r in rows:
        slug = lmap.get(r["id"])
        if slug:
            try:
                rv = D.revenue(api, slug)
                if rv:
                    revs[r["id"]] = rv
            except Exception as e:  # noqa: BLE001
                log.append(f"{r['symbol']}: DefiLlama failed: {D.safe(e)}")
    reg = regime(a.data)
    table, med = rate(rows, prices, supplies, revs, cfg, reg, today)
    wl = watchlist(table, prices, reg, cfg["regime"]["watchlist_size"]) if not reg["on"] else []
    candidates = [x["id"] for x in table if reg["on"] and x["dual_bull"] and x["quality"]["pass"]]
    latest = {"version": 1, "generated_at": pd.Timestamp(now).strftime("%Y-%m-%dT%H:%M:%SZ"), "day": day, "regime": reg,
              "revenue_median_growth": med, "coins": table, "watchlist": wl, "candidates": candidates,
              "excluded": excluded, "calls": api.calls, "log": log[-60:],
              "note": "Context only: never part of the buy / hold reading. Not advice."}
    D.save_json(folder / "latest.json", latest)
    snaps = folder / "snapshots"
    snaps.mkdir(parents=True, exist_ok=True)
    snapshot_rows(table, reg, day).to_csv(snaps / f"{day}.csv", index=False)
    st = D.load_json(folder / "state.json", {})
    push, st = alert(table, reg, st, day, cfg)
    D.save_json(folder / "state.json", st)
    if push:
        ok, why = (sender or notify.send)(push["title"], push["message"], push["priority"], push["tags"]) if not a.no_push else (False, "pushes off")
        print(f'push "{push["title"]}": {why}')
    print(f"coin scanner {day}: {len(table)} coins, {len(excluded)} excluded, regime {reg['state']}, "
          f"{sum(1 for x in table if x['dual_bull'])} Dual Bull, {len(candidates)} candidates; calls {api.calls}")
    for line in log[-30:]:
        print(" -", line)
    return latest


if __name__ == "__main__":
    main()
