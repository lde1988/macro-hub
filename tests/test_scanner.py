"""Coin scanner (reports/18). Made-up data only; nothing here touches the network."""
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from hub.scanner import data as D, quality as Q, scan, trend as T, universe as U
from hub.util import ROOT

CFG = yaml.safe_load(open(ROOT / "config" / "scanner.yaml"))
TC, QC = CFG["trend"], CFG["quality"]
UTC = dt.timezone.utc


def series(values, start="2025-01-01"):
    return pd.Series(np.asarray(values, dtype=float), index=pd.date_range(start, periods=len(values)))


def trend_up(n=300, daily=0.01, start=100.0):
    return series(start * np.exp(daily * np.arange(n)))


# ------------------------------------------------------------------ config as approved
def test_config_as_approved():
    assert TC["ma_days"] == 50 and TC["position_band"] == 0.03 and TC["slope_band"] == 0.01
    assert TC["momentum_band"] == 0.75 and TC["confirm_days"] == 5
    assert QC["revenue_good"] == 0.20 and QC["revenue_bad"] == -0.20 and QC["revenue_relative"] is True
    assert CFG["regime"]["source"] == "hub_trend_exit" and CFG["universe"]["top_n"] == 100
    assert len(CFG["universe"]["owner_coins"]) == 10 and "binancecoin" in CFG["universe"]["exchange_ids"]


# ------------------------------------------------------------------ trend
def test_steady_rise_is_strong_bull_and_steady_fall_strong_bear():
    up = T.rating(trend_up(), TC)
    down = T.rating(series(100 * np.exp(-0.01 * np.arange(300))), TC)
    assert up["state"] == "Strong Bull" and up["tests"] == {"position": 1, "direction": 1, "momentum": 1}
    assert down["state"] == "Strong Bear"


def test_flat_price_is_neutral():
    rng = np.random.default_rng(1)
    flat = series(100 * np.exp(np.cumsum(rng.normal(0, 0.002, 300)) * 0.1))
    assert T.rating(flat, TC)["state"] == "Neutral"


@pytest.mark.parametrize("score,state", [(3, "Strong Bull"), (2, "Bull"), (1, "Neutral"), (0, "Neutral"), (-1, "Neutral"),
                                         (-2, "Bear"), (-3, "Strong Bear")])
def test_score_to_state(score, state):
    assert T.label(score) == state


def test_band_edges_position_test():
    # price exactly 3% above its average is not "above"; 3.1% is
    c = {**TC, "ma_days": 2, "slope_days": 1, "momentum_days": 1, "momentum_vol_days": 2}
    p = series([100, 100, 100, 100, 100, 106.09])            # average of last two = 103.045 -> +2.95%
    assert T.tests(p, c)["position"].iloc[-1] == 0
    p = series([100, 100, 100, 100, 100, 106.4])              # +3.1%
    assert T.tests(p, c)["position"].iloc[-1] == 1


def test_a_new_state_needs_five_closes_in_a_row():
    raw = pd.Series(["Bull"] * 3 + ["Bear"] * 4 + ["Bull"] + ["Bear"] * 5, index=pd.date_range("2026-01-01", periods=13))
    st, since = T.settle(raw, 5)
    assert list(st[:12]) == ["Bull"] * 12                      # 4 Bear closes, then a Bull: never confirmed
    assert st.iloc[-1] == "Bear" and since.iloc[-1] == pd.Timestamp("2026-01-13")


def test_too_little_history_gives_no_rating():
    assert T.rating(series(range(1, 100)), TC)["state"] is None


@pytest.mark.parametrize("own,vs,dual", [("Bull", "Strong Bull", True), ("Strong Bull", "Bull", True),
                                         ("Bull", "Neutral", False), ("Neutral", "Bull", False), (None, "Bull", False)])
def test_dual_bull(own, vs, dual):
    assert T.dual_bull(own, vs) is dual


# ------------------------------------------------------------------ quality
def test_revenue_growth_last_90_against_the_90_before():
    s = series([1000.0] * 90 + [1500.0] * 90)
    g, total = Q.revenue_growth(s, 90, 100000)
    assert g == pytest.approx(0.5) and total == 135000
    assert Q.revenue_growth(series([10.0] * 180), 90, 100000) == (None, 900.0)   # too small to judge
    assert Q.revenue_growth(series([1.0] * 100), 90, 0) == (None, None)        # under 180 days


def test_relative_revenue_marks_terciles_and_no_data():
    g = {"a": -0.50, "b": -0.40, "c": -0.30, "d": -0.25, "e": -0.22, "f": -0.21, "x": None}
    m = Q.relative_marks(g)
    assert [m[k][0] for k in "abcdef"] == ["bad", "bad", "neutral", "neutral", "good", "good"]
    assert m["f"][1:] == (1, 6) and m["x"] == (None, None, 6)
    # in a bear market every fixed mark is bad, but the best still stand out relatively
    assert all(Q.fixed_mark(v, QC) == "bad" for k, v in g.items() if v is not None and v <= -0.2)
    assert Q.fixed_mark(0.8 / 1.0 - 1, QC) == "bad" and Q.fixed_mark(0.2000000001, QC) == "good"


def test_dilution_marks():
    s = lambda g: series(np.linspace(100, 100 * (1 + g), 366))  # noqa: E731
    assert Q.dilution(s(0.01), 100, 105, QC)[0] == "good"
    assert Q.dilution(s(0.05), 100, 105, QC)[0] == "neutral"
    assert Q.dilution(s(0.15), 100, 105, QC)[0] == "bad"
    assert Q.dilution(s(0.01), 40, 100, QC)[0] == "bad"          # 40% circulating: a large overhang
    assert Q.dilution(None, None, None, QC) == (None, None, None)


def test_accrual_and_pass_rules():
    assert Q.accrual(100, 60, QC) == ("good", 0.6) and Q.accrual(100, 5, QC)[0] == "bad" and Q.accrual(100, 30, QC)[0] == "neutral"
    assert Q.accrual(None, 5, QC) == (None, None) and Q.accrual(100, None, QC) == (None, None)
    assert Q.passes(["good", None, None]) == (True, 1)
    assert Q.passes([None, None, None]) == (False, 0)            # no data is not a pass, nor a fail mark
    assert Q.passes(["good", "bad", "neutral"]) == (False, 3)


# ------------------------------------------------------------------ universe
def mk(cid, sym, rank, **kw):
    return {"id": cid, "symbol": sym, "name": cid.title(), "market_cap_rank": rank, "current_price": 1.0, "market_cap": 1e9,
            "circulating_supply": 100, "total_supply": 100, "max_supply": None, **kw}


def test_universe_exclusions_labels_and_owner_coins():
    cfg = {**CFG, "universe": {**CFG["universe"], "top_n": 3}}
    markets = [mk("bitcoin", "btc", 1), mk("tether", "usdt", 2), mk("binancecoin", "bnb", 3), mk("dogecoin", "doge", 4),
               mk("usyc", "usyc", 5), mk("pegged-x", "pgx", 6), mk("cardano", "ada", 7), mk("walrus-2", "wal", 400)]
    members = {"stablecoins": {"tether"}, "meme-token": {"dogecoin"}, "layer-1": {"cardano", "bitcoin"}}
    peg = series([1.0, 1.001] * 20)                              # 0.1% a day: pegged
    rows, excluded, missing = U.build(markets, members, cfg, prices={"pegged-x": peg}, coin_cats={"cardano": ["layer-1"]})
    ids = [r["id"] for r in rows]
    assert ids == ["bitcoin", "binancecoin", "dogecoin", "walrus-2"]       # top 3 kept, plus the owner's coin
    by = {r["id"]: r for r in rows}
    assert by["dogecoin"]["meme"] and by["dogecoin"]["sector"] == "Meme"
    assert by["binancecoin"]["exchange"] and by["walrus-2"]["owner"]
    reasons = {e["id"]: e["reasons"] for e in excluded}
    assert reasons["tether"] == ["category: stablecoins"] and reasons["usyc"] == ["tokenized fund or security"]
    assert "pegged" in reasons["pegged-x"][0]
    assert "deep" in missing


def test_a_quiet_real_coin_is_not_mistaken_for_a_pegged_one():
    quiet = series(100 * np.exp(np.cumsum(np.tile([0.006, -0.005], 20))))   # about 0.55% a day, like Bitcoin in mid-2023
    rows, excluded, _ = U.build([mk("litecoin", "ltc", 1)], {}, CFG, prices={"litecoin": quiet})
    assert [r["id"] for r in rows] == ["litecoin"] and excluded == []


def test_owner_coin_is_never_excluded():
    cfg = {**CFG, "universe": {**CFG["universe"], "top_n": 1}}
    rows, excluded, _ = U.build([mk("hyperliquid", "hype", 9)], {"wrapped-tokens": {"hyperliquid"}}, cfg)
    assert [r["id"] for r in rows] == ["hyperliquid"] and excluded == []


# ------------------------------------------------------------------ CoinGecko dating and Coin Metrics matching
def test_coingecko_daily_points_are_dated_to_the_close_and_today_is_dropped():
    day = lambda d, h=0: int(pd.Timestamp(d).replace(hour=h).timestamp() * 1000)  # noqa: E731

    class R:
        status_code = 200

        def json(self):
            return {"prices": [[day("2026-11-25"), 100.0], [day("2026-11-26"), 110.0], [day("2026-11-26", 9), 111.0]],
                    "market_caps": [[day("2026-11-25"), 1000.0], [day("2026-11-26"), 1210.0], [day("2026-11-26", 9), 1.0]],
                    "total_volumes": [[day("2026-11-25"), 5e7], [day("2026-11-26"), 6e7], [day("2026-11-26", 9), 1.0]]}

    class Api:
        def get(self, *a, **k):
            return R()
    p, s, v = D.cg_year(Api(), "x")
    assert list(p.index.strftime("%Y-%m-%d")) == ["2026-11-24", "2026-11-25"] and list(p) == [100.0, 110.0]
    assert list(s) == [10.0, 11.0] and list(v) == [5e7, 6e7]


def test_coin_metrics_is_used_only_when_it_is_the_same_coin():
    cg = series(np.linspace(10, 20, 60))
    assert D.same_coin(cg * 1.01, cg) and not D.same_coin(cg * 3, cg) and not D.same_coin(cg[:10], cg)


# ------------------------------------------------------------------ the day's table, watchlist, alert, snapshot
def rows_for(ids):
    return [{"id": i, "symbol": i.upper(), "name": i, "rank": n + 1, "sector": "L1", "meme": i == "doge", "exchange": False,
             "owner": i == "sol", "market_cap": 1e9, "circulating": 100, "total": 100, "max": None, "change_7d": 1.5}
            for n, i in enumerate(ids)]


def test_rate_builds_rows_with_ratings_quality_and_relative_revenue():
    btc = series(60000 * np.exp(-0.002 * np.arange(300)))
    sol = series(100 * np.exp(0.004 * np.arange(300)))
    eth = series(3000 * np.exp(-0.004 * np.arange(300)))
    revs = {"sol": {"revenue": series([1e5] * 90 + [0.8e5] * 90), "kind": "revenue", "holders": series([0.6e5] * 180)},
            "eth": {"revenue": series([1e5] * 90 + [0.5e5] * 90), "kind": "revenue", "holders": None},
            "ada": {"revenue": series([1e5] * 90 + [0.7e5] * 90), "kind": "fees", "holders": None}}
    table, med = scan.rate(rows_for(["bitcoin", "sol", "eth", "ada"]), {"bitcoin": btc, "sol": sol, "eth": eth, "ada": eth},
                           {}, revs, CFG, {"on": False}, pd.Timestamp("2025-10-28"))
    by = {r["id"]: r for r in table}
    assert by["sol"]["own"]["state"] == "Strong Bull" and by["sol"]["vs_btc"]["state"] == "Strong Bull" and by["sol"]["dual_bull"]
    assert by["eth"]["own"]["state"] == "Strong Bear" and by["bitcoin"]["vs_btc"]["why"] == "Bitcoin itself"
    q = by["sol"]["quality"]
    assert q["revenue_growth"] == pytest.approx(-0.2) and q["revenue_fixed"] == "bad" and q["revenue_relative"] == "good"
    assert q["revenue_rank"] == 1 and q["revenue_of"] == 3 and q["accrual"] == "good" and q["pass"]
    assert by["eth"]["quality"]["revenue_relative"] == "bad" and not by["eth"]["quality"]["pass"]
    assert med == pytest.approx(-0.3)


def test_watchlist_ranks_coins_against_bitcoin_since_the_regime_turned_off():
    btc = series([100.0] * 50 + [80.0] * 50)
    prices = {"bitcoin": btc, "a": series([10.0] * 100), "b": series([10.0] * 50 + [6.0] * 50)}
    table = [{"id": i, "symbol": i.upper(), "vs_btc": {"state": "Neutral"}, "meme": False, "exchange": False, "owner": False}
             for i in ("bitcoin", "a", "b")]
    wl = scan.watchlist(table, prices, {"since": "2025-01-20T00:00Z"}, 15)
    assert [w["id"] for w in wl] == ["a", "b"] and wl[0]["vs_btc_since_off_pct"] == 25.0


def coin(i, dual=True, ok=True):
    return {"id": i, "symbol": i.upper(), "sector": "L1", "dual_bull": dual, "quality": {"pass": ok, "parts_scored": 2}}


def test_alert_only_new_dual_bull_with_quality_while_regime_on_once_a_day():
    st = {"dual_ok": ["sol"]}
    push, st = scan.alert([coin("sol"), coin("eth"), coin("ada", ok=False), coin("doge", dual=False)], {"on": True}, st, "2026-12-01", CFG)
    assert "ETH" in push["message"] and "SOL" not in push["message"] and "ADA" not in push["message"]
    assert push["priority"] == 3 and st["last_alert"] == "2026-12-01" and st["dual_ok"] == ["eth", "sol"]
    push, st = scan.alert([coin("sol"), coin("eth"), coin("link")], {"on": True}, st, "2026-12-01", CFG)
    assert push is None                                         # already pushed today
    push, st = scan.alert([coin("near")], {"on": False}, {"dual_ok": []}, "2026-12-02", CFG)
    assert push is None                                         # regime OFF: no push at all


def test_snapshot_has_every_column_and_the_regime():
    table, _ = scan.rate(rows_for(["bitcoin", "sol"]), {"bitcoin": trend_up(), "sol": trend_up()}, {}, {}, CFG, {}, pd.Timestamp("2025-10-28"))
    snap = scan.snapshot_rows(table, {"state": "RISK-OFF"}, "2026-11-26")
    assert list(snap.columns) == scan.SNAP_COLS and set(snap["regime"]) == {"RISK-OFF"} and len(snap) == 2


def test_regime_comes_from_the_hubs_trend_exit(tmp_path):
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "hub.json").write_text(json.dumps({"summary": {"trend_exit": "RISK-OFF"},
                                                             "since": {"trend_exit": "2026-02-01T00:00Z"}}))
    r = scan.regime(tmp_path)
    assert r["on"] is False and r["state"] == "RISK-OFF" and r["since"].startswith("2026-02-01")
    (tmp_path / "state" / "hub.json").write_text(json.dumps({"summary": {"trend_exit": "RISK-ON"}}))
    assert scan.regime(tmp_path)["on"] is True
    assert scan.regime(tmp_path / "none")["state"] == "NO DATA"


# ------------------------------------------------------------------ the whole job, with a fake internet
class FakeResp:
    def __init__(self, obj, code=200):
        self.obj, self.status_code = obj, code

    def json(self):
        return self.obj


class FakeWeb:
    """Answers CoinGecko, Coin Metrics and DefiLlama with made-up data."""

    def __init__(self, today):
        self.today, self.urls = today, []

    def get(self, url, params=None, **kw):
        self.urls.append(url)
        params = params or {}
        if url.endswith("/coins/markets"):
            if params.get("category"):
                return FakeResp([{"id": "tether"}] if params["category"] == "stablecoins" else [])
            ids = ["bitcoin", "tether", "solana", "dogecoin"] + list(CFG["universe"]["owner_coins"])
            ids = list(dict.fromkeys(ids))
            if params.get("ids"):
                ids = params["ids"].split(",")
            return FakeResp([{"id": i, "symbol": i[:4], "name": i, "market_cap_rank": n + 1, "current_price": 10.0,
                              "market_cap": 1e9, "circulating_supply": 1e8, "total_supply": 1e8, "max_supply": None,
                              "price_change_percentage_7d_in_currency": 2.0,
                              "total_volume": 5e6 if i == "dogecoin" else 5e7} for n, i in enumerate(ids)])
        if "/market_chart" in url:
            cid = url.split("/coins/")[1].split("/")[0]
            k = 0.01 if cid != "tether" else 0.0          # real coins move about 1% a day; tether not at all
            days = pd.date_range(end=self.today, periods=min(int(params.get("days", 365)), 365) + 1)
            p = [[int(d.timestamp() * 1000), 10 * np.exp(k * i) * (1 if cid != "bitcoin" else 1000)] for i, d in enumerate(days)]
            vol = 5e6 if cid == "dogecoin" else 5e7                     # dogecoin is "too thin" in this made-up world
            return FakeResp({"prices": p, "market_caps": [[t, v * 1e8] for t, v in p], "total_volumes": [[t, vol] for t, v in p]})
        if "coinmetrics" in url:
            return FakeResp({"data": []})
        if url.endswith("/overview/fees"):
            return FakeResp({"protocols": [{"gecko_id": "solana", "slug": "solana", "total30d": 5e6}]})
        if url.endswith("/v2/chains"):
            return FakeResp([])
        if "/summary/fees/" in url:
            days = pd.date_range(end=self.today, periods=200)
            return FakeResp({"totalDataChart": [[int(d.timestamp()), 1e5] for d in days]})
        return FakeResp({}, 404)


def test_whole_job_writes_only_inside_scanner_and_pushes_nothing_while_off(tmp_path):
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "hub.json").write_text(json.dumps({"summary": {"trend_exit": "RISK-OFF"}, "since": {"trend_exit": "2026-08-01"}}))
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    now = dt.datetime(2026, 11, 27, 1, 0, tzinfo=UTC)
    sent = []
    latest = scan.main(["--data", str(tmp_path)], now=now, web=FakeWeb(pd.Timestamp("2026-11-27")),
                       sender=lambda *a, **k: (sent.append(a), (True, "sent"))[1], sleep=lambda s: None)
    new = {p for p in tmp_path.rglob("*") if p.is_file()} - set(before)
    assert new and all(p.relative_to(tmp_path).parts[0] == "scanner" for p in new)
    assert all(p.read_bytes() == b for p, b in before.items())
    assert sent == [] and latest["regime"]["on"] is False and latest["candidates"] == []
    assert latest["day"] == "2026-11-26" and (tmp_path / "scanner" / "snapshots" / "2026-11-26.csv").exists()
    ids = {c["id"] for c in latest["coins"]}
    assert "tether" not in ids and {"bitcoin", "solana"} <= ids
    assert {e["id"] for e in latest["excluded"]} == {"tether"}
    assert latest["watchlist"]                                   # regime OFF: the relative-strength list instead
    assert "dogecoin" not in {w["id"] for w in latest["watchlist"]}            # $5M a day: too thin
    doge = next(c for c in latest["coins"] if c["id"] == "dogecoin")
    assert doge["eligible"] is False and "too thin" in doge["not_eligible_why"]
    assert (tmp_path / "scanner" / "volume" / "solana.csv").exists()
    # second day: only new closes are fetched (a few days), not the whole year again
    web2 = FakeWeb(pd.Timestamp("2026-11-28"))
    scan.main(["--data", str(tmp_path)], now=now + dt.timedelta(days=1), web=web2, sender=lambda *a, **k: (True, "x"),
              sleep=lambda s: None)
    assert sum("/market_chart" in u for u in web2.urls) == len(latest["coins"])
    assert (tmp_path / "scanner" / "snapshots" / "2026-11-27.csv").exists()


# ------------------------------------------------------------------ the tab
def test_tab_escapes_text_and_has_filters_and_sorting(tmp_path):
    from hub.outputs import scanner as pane
    table, _ = scan.rate(rows_for(["bitcoin", "sol"]), {"bitcoin": trend_up(), "sol": trend_up(daily=0.02)}, {}, {}, CFG, {},
                         pd.Timestamp("2025-10-28"))
    table[1]["name"] = table[1]["sector"] = '<script>alert(1)</script>'
    scanned = {"day": "2026-11-26", "regime": {"on": False, "state": "RISK-OFF", "since": "2026-02-01", "line": 72134.3},
               "coins": table, "watchlist": [], "candidates": [], "excluded": [{"symbol": "USDT", "name": "<b>x</b>", "reasons": ["category: stablecoins"]}]}
    page = pane.pane(json.loads(json.dumps(scanned, default=str)))
    assert "<script>" not in page and "&lt;script&gt;" in page and "&lt;b&gt;x&lt;/b&gt;" in page
    assert "No buy candidates: Bitcoin regime OFF" in page and "$72,134" in page
    assert 'data-f="dual"' in page and "Hide memecoins" in page and "Not advice" in page
    assert "survivorship" in page.lower()
    assert pane.pane(None).count("has not run yet") == 1


def test_tab_shows_candidates_when_regime_on():
    from hub.outputs import scanner as pane
    table, _ = scan.rate(rows_for(["bitcoin", "sol"]), {"bitcoin": trend_up(daily=0.001), "sol": trend_up(daily=0.02)}, {}, {},
                         CFG, {}, pd.Timestamp("2025-10-28"))
    page = pane.pane({"day": "d", "regime": {"on": True, "state": "RISK-ON", "line": None}, "coins": table, "watchlist": [],
                      "candidates": ["sol"], "excluded": []})
    assert "Bitcoin regime ON: buy candidates" in page and "<b>SOL</b>" in page


def test_dashboard_has_the_third_tab_and_the_scanner_never_changes_the_reading(tmp_path):
    from hub.run import main as hub_main
    from tests.test_outputs import fake_sources
    t0 = dt.datetime(2026, 11, 25, 9, 0, tzinfo=UTC)
    snd = lambda *a, **k: (True, "sent")  # noqa: E731
    plain = hub_main(tmp_path / "a", tmp_path / "sa", tmp_path / "ra", now=t0, fetchers=fake_sources([80000] * 30, 2.1), sender=snd)
    (tmp_path / "b" / "scanner").mkdir(parents=True)
    table, _ = scan.rate(rows_for(["bitcoin", "sol"]), {"bitcoin": trend_up(), "sol": trend_up()}, {}, {}, CFG, {}, pd.Timestamp("2025-10-28"))
    (tmp_path / "b" / "scanner" / "latest.json").write_text(json.dumps(
        {"day": "2026-11-24", "regime": {"on": True, "state": "RISK-ON", "line": 1.0}, "coins": table, "watchlist": [],
         "candidates": ["sol"], "excluded": []}, default=str))
    with_scan = hub_main(tmp_path / "b", tmp_path / "sb", tmp_path / "rb", now=t0, fetchers=fake_sources([80000] * 30, 2.1), sender=snd)
    for k in ("reading", "regime", "trend_exit", "altcoins", "turn"):
        assert with_scan[k] == plain[k], k
    assert [(x["id"], x["colour"]) for x in with_scan["dials"]] == [(x["id"], x["colour"]) for x in plain["dials"]]
    page = (tmp_path / "sb" / "index.html").read_text()
    assert 'for="tab3">Coin scanner' in page and 'id="stab"' in page and plain["scanner"] is None


# ------------------------------------------------------------------ backtest pieces
def test_backtest_regime_replay_uses_weekly_closes_and_is_known_next_day():
    import importlib.util
    spec = importlib.util.spec_from_file_location("bt", ROOT / "tools" / "scanner_backtest.py")
    bt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bt)
    days = pd.date_range("2026-01-01", "2026-03-31")
    btc = pd.Series(100.0, index=days)
    btc[btc.index >= "2026-02-02"] = 90.0                        # falls below 0.96 x 100 = 96
    btc[btc.index >= "2026-03-02"] = 101.0                       # back above 100
    sth = pd.Series(100.0, index=days)
    reg = bt.regime_series(btc, sth)
    assert reg[pd.Timestamp("2026-02-08")] and not reg[pd.Timestamp("2026-02-09")]   # Sunday 8 Feb close, known Monday
    assert reg[pd.Timestamp("2026-03-09")] and not reg[pd.Timestamp("2026-03-08")]
    s = bt.stats(pd.Series([0.1, -0.5, 0.0]), "x")
    assert s["worst fall"] == "-50%" and s["growth"] == "0.55x"


def test_scanner_backstop(tmp_path):
    from hub.scanner import due
    t = dt.datetime(2026, 11, 28, 3, 0, tzinfo=UTC)
    assert due.overdue(tmp_path, t) and not due.overdue(tmp_path, t.replace(hour=2, minute=0))
    (tmp_path / "scanner" / "snapshots").mkdir(parents=True)
    (tmp_path / "scanner" / "snapshots" / "2026-11-27.csv").write_text("x")
    assert not due.overdue(tmp_path, t)


def test_scanner_workflow_schedule_and_no_secrets_but_ntfy():
    text = (ROOT / ".github" / "workflows" / "scanner.yml").read_text()
    assert 'cron: "50 0 * * *"' in text and "workflow_dispatch" in text
    assert "XAI_API_KEY" not in text and "GROQ" not in text           # free data only: no paid keys


def test_impossible_price_jumps_are_cleaned():
    p = series([0.001] * 5 + [1.0, 1.1, 1.2, 1.15] + [0.01] + [0.011, 0.012])   # listing artifact, then a redenomination
    clean, notes = D.clean_prices(p)
    assert list(clean.round(3)) == [0.01, 0.011, 0.012] and len(notes) == 1 and "x0.0087 on" in notes[0]
    real, notes = D.clean_prices(series([1.0, 3.1, 2.9]))                       # DOGE-style x3.1 day is real
    assert len(real) == 3 and notes == []
    assert len(D.clean_prices(series(range(1, 40)), skip_days=14)[0]) == 25


def test_figure_heloc_is_excluded():
    assert "figure-heloc" in CFG["universe"]["exclude_ids"]



# ------------------------------------------------------------------ owner's liquidity and age rule (27 Nov)
def test_eligibility_needs_20m_volume_and_180_days():
    p = series(range(1, 200))
    ok, avg, days, why = scan.eligibility(p, series([25e6] * 30), CFG)
    assert ok and avg == 25e6 and days == 199 and why is None
    ok, _, _, why = scan.eligibility(p, series([19e6] * 30), CFG)
    assert not ok and why.startswith("too thin: $19.0M a day")
    ok, _, _, why = scan.eligibility(series(range(1, 100)), series([50e6] * 30), CFG)
    assert not ok and why.startswith("too new: 99 days")
    ok, _, _, why = scan.eligibility(p, None, CFG)
    assert not ok and "no volume figures yet" in why


def test_thin_coins_never_alert():
    c = {**coin("thin"), "eligible": False}
    push, _ = scan.alert([c], {"on": True}, {"dual_ok": []}, "2026-12-01", CFG)
    assert push is None


def test_tab_shows_too_new_or_thin_greyed_not_hidden():
    from hub.outputs import scanner as pane
    table, _ = scan.rate(rows_for(["bitcoin", "sol", "new"]), {"bitcoin": trend_up(), "sol": trend_up(daily=0.02),
                         "new": trend_up(daily=0.03)}, {}, {}, CFG, {}, pd.Timestamp("2025-10-28"),
                         volumes={"sol": series([5e7] * 300), "new": series([1e6] * 300)})
    by = {c["id"]: c for c in table}
    assert by["sol"]["eligible"] and not by["new"]["eligible"]
    wl = [{"id": "sol", "symbol": "SOL", "vs_btc_since_off_pct": 5.0, "vs_btc_state": "Bull", "meme": False, "exchange": False, "owner": True}]
    thin = [{"id": "new", "symbol": "NEW", "vs_btc_since_off_pct": 50.0, "vs_btc_state": "Bull", "meme": False, "exchange": False, "owner": False}]
    page = pane.pane(json.loads(json.dumps({"day": "2026-11-26", "regime": {"on": False, "state": "RISK-OFF", "since": "2026-11-16", "line": 1.0},
                                            "coins": table, "watchlist": wl, "watchlist_too_new_or_thin": thin, "candidates": [],
                                            "excluded": []}, default=str)))
    assert "Too new / too thin" in page and 'class="thin"' in page and "<b>NEW</b>" in page
    page = pane.pane(json.loads(json.dumps({"day": "d", "regime": {"on": True, "state": "RISK-ON", "line": None}, "coins": table,
                                            "watchlist": [], "candidates": ["sol"], "candidates_too_new_or_thin": ["new"],
                                            "excluded": []}, default=str)))
    assert "Too new / too thin" in page and "NEW" in page
