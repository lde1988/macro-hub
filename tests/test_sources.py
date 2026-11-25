"""Source adapters: parsing, the fetch step, failure counting and secret safety.
No test touches the network; every payload is made up."""
import datetime as dt
import json

import pandas as pd
import pytest

from hub import fetch as F
from hub.signals.core import dxy_from_ecb, finished_month_ends, level_state, weekly_closes, weekly_state
from hub.sources import Ctx, Result, bitview, coinalyze, coinbase, coingecko, coinmetrics, defillama, dxycheck, ecb, finra, fred, nasdaq, treasury
from hub.util import SourceError, load_config, load_registry, scrub

NOW = dt.datetime(2026, 11, 25, 9, 0, tzinfo=dt.timezone.utc)
TODAY = pd.Timestamp("2026-11-25")
DAY = 86400


def ts(d):
    return int(pd.Timestamp(d, tz="UTC").timestamp())


# ------------------------------------------------------------------ parsers
def test_coinbase_separates_finished_candles_from_the_live_price():
    candles = [[ts("2026-11-25"), 1, 2, 3, 59170.0, 9], [ts("2026-11-24"), 1, 2, 3, 59741.0, 9], [ts("2026-11-23"), 1, 2, 3, 61190.0, 9]]
    done, live = coinbase.parse(candles, NOW.timestamp())
    assert list(done.index) == [pd.Timestamp("2026-11-23"), pd.Timestamp("2026-11-24")]
    assert done.iloc[-1] == 59741.0 and live == 59170.0


def test_bitview_drops_todays_unfinished_value():
    start = (pd.Timestamp("2026-11-23") - bitview.EPOCH).days
    s = bitview.parse({"start": start, "data": [1.0, 2.0, 3.0]}, TODAY)
    assert list(s.index) == [pd.Timestamp("2026-11-23"), pd.Timestamp("2026-11-24")] and list(s) == [1.0, 2.0]


def test_coinmetrics_realised_price_is_price_over_mvrv():
    s = coinmetrics.parse([{"time": "2026-11-24T00:00:00.000000000Z", "PriceUSD": "59790", "CapMVRVCur": "1.126"},
                           {"time": "2026-11-23T00:00:00.000000000Z", "PriceUSD": "x", "CapMVRVCur": "1.1"}])
    assert len(s) == 1 and round(s.iloc[0]) == round(59790 / 1.126)


def test_defillama_dollar_pegged_and_all_pegs():
    usd, allp = defillama.parse([{"date": str(ts("2026-11-24")), "totalCirculatingUSD": {"peggedUSD": 280e9, "peggedEUR": 1e9}},
                                 {"date": str(ts("2026-11-23")), "totalCirculatingUSD": {}}])
    assert usd.iloc[0] == 280e9 and allp.iloc[0] == 281e9 and len(usd) == 1


def test_ecb_xml_and_dollar_index_formula():
    xml = b"""<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
    <Cube><Cube time='2026-11-24'><Cube currency='USD' rate='1.0963'/><Cube currency='JPY' rate='174.39'/>
    <Cube currency='GBP' rate='0.8370'/><Cube currency='CAD' rate='1.5700'/><Cube currency='SEK' rate='11.2000'/>
    <Cube currency='CHF' rate='0.9200'/></Cube></Cube></gesmes:Envelope>"""
    r = ecb.parse(xml)
    assert r["USD"][pd.Timestamp("2026-11-24")] == 1.0963 and set(r) == {"USD", "JPY", "GBP", "CAD", "SEK", "CHF"}


def test_dollar_index_formula_matches_the_published_ice_definition():
    # EURUSD 1.10, USDJPY 150, GBPUSD 1.25, USDCAD 1.40, USDSEK 10.5, USDCHF 0.90
    want = 50.14348112 * 1.10 ** -0.576 * 150 ** 0.136 * 1.25 ** -0.119 * 1.40 ** 0.091 * 10.5 ** 0.042 * 0.90 ** 0.036
    got = dxy_from_ecb(usd=1.10, jpy=165.0, gbp=1.10 / 1.25, cad=1.54, sek=11.55, chf=0.99)
    assert abs(got - want) < 1e-9 and 95 < got < 110


def test_fred_skips_missing_values():
    s = fred.parse([{"date": "2026-11-20", "value": "4.61"}, {"date": "2026-11-23", "value": "."}, {"date": "2026-11-24", "value": "4.63"}])
    assert list(s) == [4.61, 4.63]


def test_finra_manual_file_and_month_end_dating(tmp_path):
    p = tmp_path / "margin_debt.csv"
    p.write_text("# comment\nmonth,debit_usd_millions\n2026-09,1480054\n2026-10,1448360\n")
    s = finra.parse_manual(p)
    assert list(s.index) == [pd.Timestamp("2026-09-30"), pd.Timestamp("2026-10-31")] and s.iloc[-1] == 1448360
    assert finra.parse_manual(tmp_path / "missing.csv").empty


def test_finra_falls_back_to_the_manual_file_when_the_site_fails(tmp_path):
    (tmp_path / "manual").mkdir()
    (tmp_path / "manual" / "margin_debt.csv").write_text("month,debit_usd_millions\n2026-10,1448360\n")

    class Down:
        def get(self, *a, **k):
            raise SourceError("HTTP 503")
    res = finra.fetch([{"id": "MARGIN_DEBT", "start": "2010-02-01"}], Ctx(now=NOW, backfill=True, web=Down(), root=str(tmp_path)))
    assert res.history["MARGIN_DEBT"].iloc[-1] == 1448360 and "manual" in res.errors["MARGIN_DEBT"]


def test_treasury_splits_buybacks_by_type_and_skips_unfinished_rows():
    rows = [{"operation_date": "2026-11-19", "operation_type": "Liquidity Support", "total_par_amt_accepted": "254000000.00"},
            {"operation_date": "2026-11-19", "operation_type": "Liquidity Support", "total_par_amt_accepted": "1000000000.00"},
            {"operation_date": "2026-09-10", "operation_type": "Cash Management", "total_par_amt_accepted": "25000000000.00"},
            {"operation_date": "2026-12-02", "operation_type": "Liquidity Support", "total_par_amt_accepted": "null"},
            {"operation_date": "2023-03-30", "operation_type": "null", "total_par_amt_accepted": "24000000.00"}]
    out = treasury.parse(rows)
    assert out["Liquidity Support"][pd.Timestamp("2026-11-19")] == 1254000000.0 and len(out["Liquidity Support"]) == 1
    assert out["Cash Management"].iloc[0] == 25e9 and set(out) == {"Liquidity Support", "Cash Management"}


def test_nasdaq_price_strings():
    s = nasdaq.parse([{"date": "11/24/2026", "close": "$42.605"}, {"date": "11/23/2026", "close": "26,214.17"}, {"date": "bad", "close": "1"}])
    assert s[pd.Timestamp("2026-11-24")] == 42.605 and s[pd.Timestamp("2026-11-23")] == 26214.17 and len(s) == 2


def test_coingecko_snapshot_is_recorded_once_a_day():
    class W:
        def get(self, *a, **k):
            class R:
                def json(self):
                    return {"data": {"total_market_cap": {"usd": 2.0e12}, "market_cap_percentage": {"btc": 58.0}}}
            return R()
    entries = [{"id": "CG_TOTAL_MCAP", "code": "total_market_cap.usd"}, {"id": "CG_BTC_DOM", "code": "market_cap_percentage.btc"}]
    res = coingecko.fetch(entries, Ctx(now=NOW, web=W()))
    assert res.once == {"CG_TOTAL_MCAP", "CG_BTC_DOM"} and res.history["CG_BTC_DOM"][TODAY] == 58.0


def test_dxycheck_parse():
    j = {"chart": {"result": [{"timestamp": [ts("2026-11-23"), ts("2026-11-24")], "indicators": {"quote": [{"close": [104.32, None]}]}}]}}
    assert list(dxycheck.parse(j)) == [104.32]


def test_open_interest_job_sums_the_market_list_and_drops_days_without_bitcoin(tmp_path):
    from hub.sources import coinalyze_oi
    (tmp_path / "registry").mkdir()
    (tmp_path / "registry" / "oi_universe.yaml").write_text("btc: [BTCUSDT_PERP.A]\nalt: [ETHUSDT_PERP.A, SOLUSDT_PERP.A]\n")

    class W:
        def get(self, url, **k):
            class R:
                status_code = 200
                headers = {}

                def json(self):
                    return [{"symbol": "BTCUSDT_PERP.A", "history": [{"t": ts("2026-11-22"), "c": 0.0}, {"t": ts("2026-11-23"), "c": 5.0}, {"t": ts("2026-11-24"), "c": 6.0}]},
                            {"symbol": "ETHUSDT_PERP.A", "history": [{"t": ts("2026-11-22"), "c": 9.0}, {"t": ts("2026-11-23"), "c": 3.0}, {"t": ts("2026-11-24"), "c": 4.0}]},
                            {"symbol": "SOLUSDT_PERP.A", "history": [{"t": ts("2026-11-23"), "c": 1.0}, {"t": ts("2026-11-24"), "c": 2.0}, {"t": ts("2026-11-25"), "c": 99.0}]}]
            return R()
    entries = [{"id": "OI_BTC", "code": "oi:btc", "start": "2022-10-16"}, {"id": "OI_ALT", "code": "oi:alt", "start": "2022-10-16"}]
    res = coinalyze_oi.fetch(entries, Ctx(now=NOW, backfill=True, web=W(), env={"COINALYZE_API_KEY": "k"}, root=str(tmp_path)))
    assert list(res.history["OI_BTC"]) == [5.0, 6.0] and list(res.history["OI_ALT"]) == [4.0, 6.0]   # zero-Bitcoin day and today's unfinished day dropped


def test_open_interest_is_not_part_of_the_15_minute_run(tmp_path):
    called = []
    reg = {"sources": {"coinalyze_oi": {"every": 1440, "scheduled": False}}, "series": [{"id": "OI_ALT", "source": "coinalyze_oi", "start": "2022-10-16"}]}
    f = {"coinalyze_oi": lambda e, c: called.append(1) or Result()}
    F.run_fetch(tmp_path, now=NOW, registry=reg, fetchers=f)
    assert called == []
    F.run_fetch(tmp_path, now=NOW, registry=reg, fetchers=f, only=["coinalyze_oi"])
    assert called == [1]


def test_coinalyze_history_and_universe_sum():
    items = [{"symbol": "BTCUSDT_PERP.A", "history": [{"t": ts("2026-11-23"), "c": 5.0}, {"t": ts("2026-11-24"), "c": 6.0}, {"t": ts("2026-11-25"), "c": 9.0}]},
             {"symbol": "ETHUSDT_PERP.A", "history": [{"t": ts("2026-11-23"), "c": 3.0}, {"t": ts("2026-11-24"), "c": 4.0}]},
             {"symbol": "SOLUSDT_PERP.A", "history": [{"t": ts("2026-11-23"), "c": 1.0}]}]
    h = coinalyze.parse_history(items, TODAY)
    assert len(h["BTCUSDT_PERP.A"]) == 2                                   # today's unfinished day dropped
    btc, alt = coinalyze.sum_universe(h, ["BTCUSDT_PERP.A"], ["ETHUSDT_PERP.A", "SOLUSDT_PERP.A", "MISSING.X"])
    assert list(btc) == [5.0, 6.0] and list(alt) == [4.0, 5.0]             # SOL's missing day carried forward


# ------------------------------------------------------------------ calendar logic
def test_weekly_close_is_the_sunday_candle():
    s = pd.Series(range(14), index=pd.date_range("2026-11-09", periods=14), dtype=float)   # Monday 9 Nov onward
    w = weekly_closes(s)
    assert list(w.index) == [pd.Timestamp("2026-11-15"), pd.Timestamp("2026-11-22")]


def test_a_month_is_finished_only_when_the_next_month_has_data():
    s = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(["2026-09-30", "2026-10-30", "2026-10-31"]))
    assert list(finished_month_ends(s)) == [1.0]                           # October not finished: no November data yet
    s[pd.Timestamp("2026-11-02")] = 4.0
    assert list(finished_month_ends(s)) == [1.0, 3.0]


def test_level_state_counts_reversals():
    s = pd.Series([103, 103, 102, 102, 103, 103, 102, 102], index=pd.date_range("2026-01-01", periods=8), dtype=float)
    below, flips, last = level_state(s, 102.5, 0.3, 2)
    assert below is True and flips == 2 and last == pd.Timestamp("2026-01-08")


def test_weekly_state_reclaim_then_new_break():
    w = pd.Series([69000, 74000, 68000], index=pd.date_range("2026-01-04", periods=3, freq="7D"), dtype=float)
    assert weekly_state(w.iloc[:2], 70000, 73000) == (False, pd.Timestamp("2026-01-11"))
    assert weekly_state(w, 70000, 73000) == (True, None)


# ------------------------------------------------------------------ fetch step
def fake(history=None, fail=None, errors=None):
    def f(entries, ctx):
        if fail:
            raise SourceError(fail)
        return Result(history=history or {}, errors=errors or {})
    return f


MINI = {"sources": {"ecb": {"every": 30}, "fred": {"every": 60}},
        "series": [{"id": "ECB_USD", "source": "ecb", "start": "2026-01-01"}, {"id": "DGS2", "source": "fred", "start": "2026-01-01"}]}


def test_fetch_writes_history_and_marks_the_source_healthy(tmp_path):
    s = pd.Series({pd.Timestamp("2026-11-24"): 1.0963})
    store, live, status = F.run_fetch(tmp_path, now=NOW, registry=MINI, fetchers={"ecb": fake({"ECB_USD": s}), "fred": fake(fail="HTTP 500")})
    assert store.series("ECB_USD").iloc[-1] == 1.0963
    assert status["ecb"]["fails"] == 0 and status["ecb"]["last_ok"]
    assert (tmp_path / "history" / "ECB_USD" / "2026.csv").exists()


def test_fetch_counts_failures_in_a_row_and_resets_on_success(tmp_path):
    for i in range(4):
        _, _, status = F.run_fetch(tmp_path, now=NOW + dt.timedelta(minutes=15 * i), registry=MINI,
                                   fetchers={"ecb": fake(), "fred": fake(fail="HTTP 500")})
    assert status["fred"]["fails"] == 4 and "HTTP 500" in status["fred"]["last_error"]
    s = pd.Series({pd.Timestamp("2026-11-24"): 4.63})
    _, _, status = F.run_fetch(tmp_path, now=NOW + dt.timedelta(hours=2), registry=MINI, fetchers={"ecb": fake(), "fred": fake({"DGS2": s})})
    assert status["fred"]["fails"] == 0


def test_a_healthy_source_is_not_asked_again_too_soon(tmp_path):
    calls = []

    def counting(entries, ctx):
        calls.append(ctx.now)
        return Result(history={"ECB_USD": pd.Series({pd.Timestamp("2026-11-24"): 1.1})})
    for m in (0, 15, 30):
        F.run_fetch(tmp_path, now=NOW + dt.timedelta(minutes=m), registry=MINI, fetchers={"ecb": counting, "fred": fake()})
    assert len(calls) == 2                                                  # every 30 minutes, not every run


def test_a_failing_source_is_retried_every_run(tmp_path):
    calls = []

    def failing(entries, ctx):
        calls.append(1)
        raise SourceError("down")
    for m in (0, 15, 30):
        F.run_fetch(tmp_path, now=NOW + dt.timedelta(minutes=m), registry=MINI, fetchers={"ecb": fake(), "fred": failing})
    assert len(calls) == 3


def test_all_series_failing_inside_a_source_counts_as_a_failure(tmp_path):
    _, _, status = F.run_fetch(tmp_path, now=NOW, registry=MINI, fetchers={"ecb": fake(errors={"ECB_USD": "boom"}), "fred": fake()})
    assert status["ecb"]["fails"] == 1


# ------------------------------------------------------------------ secrets
def test_secrets_are_scrubbed_from_errors_and_status(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FRED_API_KEY", "abcdef0123456789abcdef0123456789")
    msg = "HTTPSConnectionPool: /fred/series/observations?series_id=DGS2&api_key=abcdef0123456789abcdef0123456789&file_type=json"
    assert "abcdef0123456789" not in scrub(msg) and "abcdef0123456789" not in str(SourceError(msg))

    def leaky(entries, ctx):
        raise RuntimeError(msg)
    _, _, status = F.run_fetch(tmp_path, now=NOW, registry=MINI, fetchers={"ecb": fake(), "fred": leaky})
    saved = (tmp_path / "state" / "sources.json").read_text()
    assert "abcdef0123456789" not in saved and "abcdef0123456789" not in capsys.readouterr().out
    assert "***" in status["fred"]["last_error"]


def test_fred_without_a_key_fails_cleanly():
    with pytest.raises(SourceError):
        fred.fetch([{"id": "DGS2", "code": "DGS2", "freq": "D", "start": "2026-01-01"}], Ctx(now=NOW, env={}))


# ------------------------------------------------------------------ registry and config
def test_registry_entries_are_complete():
    reg = load_registry()
    for e in reg["series"]:
        assert {"id", "source", "code", "units", "freq", "lag_days", "start", "meaning"} <= set(e), e["id"]
        assert e["source"] in reg["sources"], e["id"]
        assert e["freq"] in "DWME"


def test_every_threshold_has_a_comment():
    for i, line in enumerate((F.ROOT / "config" / "thresholds.yaml").read_text().splitlines()):
        text = line.strip()
        if not text or text.startswith("#") or text.endswith(":"):      # blank, comment, or a section heading
            continue
        assert "#" in line, f"line {i + 1} has no comment: {line}"


def test_config_families_refer_to_real_dials():
    from hub.signals.dials import DIALS
    c, ids = load_config(), {d["id"] for d in DIALS}
    for group in (c["families"], c["turn_families"]):
        for fam, members in group.items():
            assert set(members) <= ids, fam
    assert "fed_reserves" not in [m for ms in c["turn_families"].values() for m in ms]


# ------------------------------------------------------------------ review fixes (point 8)
def test_look_back_reaches_the_last_stored_date_after_a_long_pause():
    e = {"id": "BTCUSD", "start": "2015-07-20"}
    assert Ctx(now=NOW).since(e, 20) == pd.Timestamp("2026-11-05")                                  # normal short look-back
    paused = Ctx(now=NOW, last={"BTCUSD": pd.Timestamp("2026-08-01")})
    assert paused.since(e, 20) == pd.Timestamp("2026-07-29")                                        # hub paused since August: no hole
    assert Ctx(now=NOW, last={"BTCUSD": pd.Timestamp("2026-11-24")}).since(e, 20) == pd.Timestamp("2026-11-05")
    assert Ctx(now=NOW, backfill=True).since(e, 20) == pd.Timestamp("2015-07-20")


def test_ecb_uses_the_full_file_after_a_long_pause():
    asked = []

    class W:
        def get(self, url, **k):
            asked.append(url)

            class R:
                content = b"<x/>"
            return R()
    entries = [{"id": "ECB_USD", "code": "USD", "start": "1999-01-04"}]
    ecb.fetch(entries, Ctx(now=NOW, web=W(), last={"ECB_USD": pd.Timestamp("2026-11-24")}))
    ecb.fetch(entries, Ctx(now=NOW, web=W(), last={"ECB_USD": pd.Timestamp("2026-07-01")}))
    ecb.fetch(entries, Ctx(now=NOW, web=W()))
    assert asked == [ecb.RECENT, ecb.FULL, ecb.FULL]


def test_live_values_expire_so_an_old_price_is_never_used_as_now(tmp_path):
    def with_live(entries, ctx):
        return Result(history={"ECB_USD": pd.Series({pd.Timestamp("2026-11-24"): 1.1})}, live={"ECB_USD": (1.2, ctx.now.isoformat())})
    _, live, _ = F.run_fetch(tmp_path, now=NOW, registry=MINI, fetchers={"ecb": with_live, "fred": fake()})
    assert live["ECB_USD"]["value"] == 1.2
    down = fake(fail="down")
    _, live, _ = F.run_fetch(tmp_path, now=NOW + dt.timedelta(minutes=45), registry=MINI, fetchers={"ecb": down, "fred": fake()})
    assert "ECB_USD" in live                                                # 45 minutes old: still within 2 x 30 + 15
    _, live, _ = F.run_fetch(tmp_path, now=NOW + dt.timedelta(minutes=90), registry=MINI, fetchers={"ecb": down, "fred": fake()})
    assert "ECB_USD" not in live                                            # too old: dropped, the dial falls back to stored history


def test_bookkeeping_can_live_outside_the_data_folder(tmp_path):
    rt = tmp_path / "rt"
    F.run_fetch(tmp_path / "data", now=NOW, registry=MINI, fetchers={"ecb": fake(), "fred": fake()}, state_dir=rt)
    assert (rt / "sources.json").exists() and not (tmp_path / "data" / "state" / "sources.json").exists()


def test_nasdaq_never_stores_a_session_that_is_still_trading():
    from hub.sources.nasdaq import last_finished_session
    assert last_finished_session(pd.Timestamp("2026-11-24 19:00", tz="UTC")) == pd.Timestamp("2026-11-23")   # 14:00 New York: Tuesday still trading
    assert last_finished_session(pd.Timestamp("2026-11-24 22:30", tz="UTC")) == pd.Timestamp("2026-11-24")   # 17:30 New York: Tuesday finished
    assert last_finished_session(pd.Timestamp("2026-11-25 03:00", tz="UTC")) == pd.Timestamp("2026-11-24")   # still Tuesday evening in New York
    assert last_finished_session(pd.Timestamp("2026-07-01 20:30", tz="UTC")) == pd.Timestamp("2026-06-30")   # summer time: 16:30 New York


def test_one_working_series_does_not_hide_another_that_keeps_failing(tmp_path):
    from hub import alerts
    from hub.util import load_config
    ok = pd.Series({pd.Timestamp("2026-11-24"): 4.6})
    reg = {"sources": {"fred": {"every": 60, "credit": "FRED"}},
           "series": [{"id": "DGS2", "source": "fred", "start": "2026-01-01"}, {"id": "DGS10", "source": "fred", "start": "2026-01-01"}]}
    part = lambda entries, ctx: Result(history={"DGS2": ok}, errors={"DGS10": "HTTP 500"})
    for i in range(4):
        _, _, status = F.run_fetch(tmp_path, now=NOW + dt.timedelta(hours=i), registry=reg, fetchers={"fred": part})
    assert status["fred"]["fails"] == 0 and status["fred"]["series_fails"] == {"DGS10": 4}
    pushes, down = alerts.source_pushes(status, reg, load_config(), [])
    assert len(pushes) == 1 and pushes[0]["title"] == "Source partly down: FRED" and "DGS10" in pushes[0]["message"]
    assert alerts.source_pushes(status, reg, load_config(), down)[0] == []                     # not repeated
    _, _, status = F.run_fetch(tmp_path, now=NOW + dt.timedelta(hours=5), registry=reg, fetchers={"fred": lambda e, c: Result(history={"DGS2": ok, "DGS10": ok})})
    assert status["fred"]["series_fails"] == {}
