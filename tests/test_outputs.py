"""Feed, dashboard, alerts and the whole run, with made-up data. Nothing is fetched or sent."""
import datetime as dt
import json

import pandas as pd

from hub import alerts
from hub.outputs import dashboard, feed as feedmod, icons
from hub.run import main, update_since
from hub.signals.engine import evaluate
from hub.sources import Result
from hub.util import load_registry
from tests.helpers import cfg, flat, view, weekly_btc

C, REG = cfg(), load_registry()
NOW = pd.Timestamp("2026-11-25 09:00")


def small_feed(tmp_path, extra=None, state=None, now=NOW, status=None):
    data = {"BTCUSD": weekly_btc([80000, 61000]), "BV_REALIZED_PRICE": flat(53000, 30), "T5YIE": flat(2.1, 5), "NFCI": flat(-0.5, 5),
            "BV_STH_REALIZED_PRICE": flat(72400, 30)}
    data.update(extra or {})
    out = evaluate(view(tmp_path, data, now=now, live={"BTCUSD": 61000}), C, state)
    fd = feedmod.build(out, C, REG, now, status or {"fred": {"fails": 0, "last_ok": "2026-11-25T08:45:00+00:00"}},
                       {"reading": "2026-11-16", "regime": "2026-11-16", "trend_exit": None})
    fd["stale_minutes"] = 60
    return fd, out


# ------------------------------------------------------------------ feed
def test_feed_has_version_reading_regime_and_every_dial(tmp_path):
    fd, _ = small_feed(tmp_path)
    assert fd["version"] == "1.0" and fd["generated_at"] == "2026-11-25T09:00:00Z" and "HKT" in fd["generated_at_hkt"]
    assert fd["reading"]["label"] == "HOLD" and fd["reading"]["days_in_force"] == 9
    assert fd["trend_exit"]["state"] == "RISK-OFF" and fd["regime"]["name"] == "BREAK"
    assert len(fd["dials"]) == 39
    for d in fd["dials"]:
        assert {"id", "title", "group", "family", "value", "text", "colour", "word", "data_date", "data_age_days", "stale", "moves", "gauge"} <= set(d)
    json.dumps(fd, default=str)                                   # must be writable as JSON


def test_feed_sections_cover_every_dial_once_with_a_sentence(tmp_path):
    fd, _ = small_feed(tmp_path)
    ids = [i for s in fd["sections"] for i in s["dials"]]
    assert sorted(ids) == sorted(d["id"] for d in fd["dials"])
    assert [s["id"] for s in fd["sections"]][0] == "valuation" and fd["sections"][-1]["id"] == "turn"
    assert all(s["sentence"] and s["word"] for s in fd["sections"])
    credit = next(s for s in fd["sections"] if s["id"] == "credit")
    assert credit["colour"] == "green" and "no data yet" in credit["sentence"]


def test_stale_data_keeps_the_last_colour_greyed_and_cannot_change_it(tmp_path):
    _, out1 = small_feed(tmp_path)                                           # breakeven 2.1%: green
    old_and_red = {"T5YIE": flat(3.0, 5, end="2026-11-10")}                  # 15 days old, and would be red
    state = out1["state"]
    for i in range(3):                                                       # however many runs pass
        fd, out = small_feed(tmp_path / f"s{i}", old_and_red, state=state)
        state = out["state"]
    d = next(x for x in fd["dials"] if x["id"] == "breakeven")
    assert d["colour"] == "green" and d["stale"] is True and "15 days old" in d["stale_reason"]
    assert "Greyed out" in dashboard.render(fd)
    fresh, _ = small_feed(tmp_path / "b")
    assert next(x for x in fresh["dials"] if x["id"] == "breakeven")["stale"] is False


def test_stale_data_seen_for_the_first_time_gets_no_colour(tmp_path):
    fd, _ = small_feed(tmp_path, {"T5YIE": flat(3.0, 5, end="2026-11-10")})
    d = next(x for x in fd["dials"] if x["id"] == "breakeven")
    assert d["colour"] is None and "15 days old" in d["stale_reason"]


def test_a_dial_going_stale_pushes_once(tmp_path):
    fd1, out1 = small_feed(tmp_path)
    fd2, _ = small_feed(tmp_path / "b", {"T5YIE": flat(2.1, 5, end="2026-11-10")}, state=out1["state"])
    p = alerts.plan(alerts.summary(fd1), fd2, C)
    assert len(p) == 1 and p[0]["title"] == "Stale data: 5-year breakeven inflation" and p[0]["priority"] == 3
    assert alerts.plan(alerts.summary(fd2), fd2, C) == []                    # not repeated
    assert "Stale dials: 5-year breakeven inflation" in alerts.digest(fd2, C)["message"]


def test_feed_keeps_last_colour_greyed_when_a_source_stops(tmp_path):
    _, out1 = small_feed(tmp_path)
    data = {"BTCUSD": weekly_btc([80000, 61000]), "BV_REALIZED_PRICE": flat(53000, 30)}     # T5YIE gone
    out2 = evaluate(view(tmp_path / "b", data, live={"BTCUSD": 61000}), C, out1["state"])
    fd = feedmod.build(out2, C, REG, NOW, {}, {})
    d = next(x for x in fd["dials"] if x["id"] == "breakeven")
    assert d["colour"] == "green" and d["stale"] is True and "last colour kept" in d["stale_reason"]


# ------------------------------------------------------------------ dashboard
def test_dashboard_is_self_contained_and_in_the_agreed_order(tmp_path):
    fd, _ = small_feed(tmp_path)
    page = dashboard.render(fd)
    assert "<script src" not in page and "http://" not in page and "@import" not in page and "fonts.googleapis" not in page
    assert page.count("https://") == 0                                   # no external resource at all
    order = [page.index(x) for x in ("Regime</p>", "Bitcoin reading", "Is it cheap?", "Rates and dollar", "Has the turn started?",
                                     "What they're watching", "Sources: last successful fetch")]
    assert order == sorted(order)
    assert "Framework reading, not financial advice" in page
    assert "Built to spot buy zones. Its exit signals have a weak record." in page
    assert "Trend exit" in page and "RISK-OFF" in page and "Bitview (bitview.space), CC BY 4.0" in page
    assert 'rel="manifest"' in page and "apple-touch-icon" in page


def test_dashboard_never_relies_on_colour_alone(tmp_path):
    fd, _ = small_feed(tmp_path)
    page = dashboard.render(fd)
    assert page.count('<article class="dial') == 39 and page.count("<svg") == 39
    for word in ("Supports", "Neutral", "Against"):
        assert word in page
    assert page.count('class="moves"') == 39                             # one sentence on what would move each dial


def test_dashboard_shows_froth_record_only_with_a_froth_warning(tmp_path):
    fd, _ = small_feed(tmp_path)
    assert "Record of this warning" not in dashboard.render(fd)
    fd["reading"].update(label="FROTH WARNING", headline="Froth warning (reduce-risk watch)", record="right on 3 of 8 past occasions")
    assert "Record of this warning: right on 3 of 8 past occasions" in dashboard.render(fd)


def test_dashboard_escapes_text(tmp_path):
    fd, _ = small_feed(tmp_path)
    fd["regime"]["detail"] = "<script>alert(1)</script>"
    assert "<script>alert(1)</script>" not in dashboard.render(fd)


def test_icons_are_valid_png_files(tmp_path):
    icons.write_all(tmp_path)
    for name in ("icon-192.png", "icon-512.png", "icon-maskable-512.png", "apple-touch-icon.png"):
        assert (tmp_path / name).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert {i["sizes"] for i in dashboard.MANIFEST["icons"]} == {"192x192", "512x512"} and dashboard.MANIFEST["display"] == "standalone"


# ------------------------------------------------------------------ alerts
def test_first_run_is_a_silent_baseline(tmp_path):
    fd, _ = small_feed(tmp_path)
    assert alerts.plan(None, fd, C) == []


def test_no_change_no_push(tmp_path):
    fd, _ = small_feed(tmp_path)
    assert alerts.plan(alerts.summary(fd), fd, C) == []


def test_reading_change_is_priority_5_and_froth_is_4(tmp_path):
    fd, _ = small_feed(tmp_path)
    prev = alerts.summary(fd)
    prev.update(reading="Buy (staged)", label="BUY")
    p = alerts.plan(prev, fd, C)
    assert len(p) == 1 and p[0]["priority"] == 5 and "Buy (staged) →" in p[0]["message"] and "not financial advice" in p[0]["message"]
    fd["reading"].update(label="FROTH WARNING", headline="Froth warning (reduce-risk watch)", record="right on 3 of 8 past occasions")
    p = alerts.plan(alerts.summary(small_feed(tmp_path / "b")[0]), fd, C)
    assert p[0]["priority"] == 4 and "3 of 8" in p[0]["message"]


def test_caution_wording_alone_does_not_count_as_a_reading_change(tmp_path):
    fd, _ = small_feed(tmp_path)
    prev = alerts.summary(fd)
    fd["reading"]["headline"] = fd["reading"]["headline"].split(" (CAUTION")[0]
    assert [p for p in alerts.plan(prev, fd, C) if p["title"].startswith("Reading")] == []


def test_regime_and_trend_exit_changes_are_priority_5(tmp_path):
    fd, _ = small_feed(tmp_path)
    prev = alerts.summary(fd)
    prev.update(regime="CALM", trend_exit="RISK-ON")
    p = {x["title"]: x for x in alerts.plan(prev, fd, C)}
    assert p["Regime: CALM → BREAK"]["priority"] == 5 and p["Trend exit: RISK-OFF"]["priority"] == 5
    assert "$61,000" in p["Trend exit: RISK-OFF"]["message"]


def test_dial_change_priorities(tmp_path):
    fd, _ = small_feed(tmp_path)

    def pr(dial, old):
        prev = alerts.summary(fd)
        prev["dials"][dial] = old
        return alerts.plan(prev, fd, C)[0]
    assert pr("btc_weekly", "amber")["priority"] == 4          # turned red
    assert pr("breakeven", "amber")["priority"] == 2           # turned green: improvement
    assert pr("breakeven", "red")["priority"] == 2
    one = pr("btc_weekly", "green")
    assert "Supports → Against" in one["message"] and "$61,000" in one["message"]
    fd["dials"][0]["colour"] = "amber"
    prev = alerts.summary(fd)
    prev["dials"][fd["dials"][0]["id"]] = "red"
    assert alerts.plan(prev, fd, C)[0]["priority"] == 2        # amber from red: improvement
    prev["dials"][fd["dials"][0]["id"]] = "green"
    assert alerts.plan(prev, fd, C)[0]["priority"] == 3        # amber from green


def test_several_dial_changes_make_one_push_at_the_highest_priority(tmp_path):
    fd, _ = small_feed(tmp_path)
    prev = alerts.summary(fd)
    prev["dials"].update(btc_weekly="amber", breakeven="amber", nfci="amber")
    p = alerts.plan(prev, fd, C)
    assert len(p) == 1 and p[0]["title"] == "3 dials changed" and p[0]["priority"] == 4


def test_a_dial_gaining_its_first_colour_does_not_push(tmp_path):
    fd, _ = small_feed(tmp_path)
    prev = alerts.summary(fd)
    prev["dials"]["breakeven"] = None
    assert alerts.plan(prev, fd, C) == []


def test_source_down_after_four_failures_once_and_back_once():
    st = {"fred": {"fails": 3}, "dxycheck": {"fails": 9}}
    assert alerts.source_pushes(st, REG, C, []) == ([], [])
    st["fred"]["fails"] = 4
    p, down = alerts.source_pushes(st, REG, C, [])
    assert len(p) == 1 and p[0]["title"].startswith("Source down: FRED") and down == ["fred"]      # check-only source never alerts
    st["fred"]["fails"] = 7
    assert alerts.source_pushes(st, REG, C, down) == ([], ["fred"])                                  # not repeated
    st["fred"]["fails"] = 0
    p, down = alerts.source_pushes(st, REG, C, down)
    assert p[0]["title"].startswith("Source back") and down == []


def test_digest_once_a_day_at_8am_hong_kong_time():
    assert alerts.digest_due(pd.Timestamp("2026-11-24 23:50", tz="UTC"), "2026-11-24", C) is False   # 07:50 HKT
    assert alerts.digest_due(pd.Timestamp("2026-11-25 00:05", tz="UTC"), "2026-11-24", C) is True    # 08:05 HKT on the 25th
    assert alerts.digest_due(pd.Timestamp("2026-11-25 03:00", tz="UTC"), "2026-11-25", C) is False   # already sent today
    assert alerts.digest_due(pd.Timestamp("2026-11-25 09:00", tz="UTC"), "2026-11-24", C) is True    # runs were late: still sent


def test_digest_text(tmp_path):
    fd, _ = small_feed(tmp_path)
    d = alerts.digest(fd, C)
    assert d["priority"] == 2 and "Regime: BREAK" in d["message"] and "Trend exit: RISK-OFF" in d["message"] and "All sources answering" in d["message"]


def test_since_dates_move_only_when_something_changes():
    since = {"reading": "2026-11-16", "regime": "2026-11-16", "trend_exit": None}
    prev = {"reading": "Hold: x", "regime": "BREAK", "trend_exit": "RISK-OFF"}
    cur = {"reading": "Hold: x", "regime": "CALM", "trend_exit": "RISK-OFF"}
    out = update_since(dict(since), prev, cur, NOW)
    assert out["reading"] == "2026-11-16" and out["regime"] == "2026-11-25T09:00Z" and out["trend_exit"] is None


# ------------------------------------------------------------------ the whole run, twice
def fake_sources(btc_weeks, breakeven):
    def coinbase(entries, ctx):
        return Result(history={"BTCUSD": weekly_btc(btc_weeks)}, live={"BTCUSD": (float(btc_weeks[-1]), ctx.now.isoformat())})

    def bitview(entries, ctx):
        return Result(history={"BV_REALIZED_PRICE": flat(53000, 400), "BV_STH_REALIZED_PRICE": flat(72400, 400)})

    def fred(entries, ctx):
        return Result(history={"T5YIE": flat(breakeven, 300)})
    empty = lambda entries, ctx: Result()
    names = ["coinmetrics", "defillama", "ecb", "finra", "treasury", "nasdaq", "coingecko", "coinalyze", "dxycheck"]
    return {"coinbase": coinbase, "bitview": bitview, "fred": fred, **{n: empty for n in names}}


def test_full_run_baseline_then_change_then_failed_push_is_retried(tmp_path):
    data, site, rt = tmp_path / "data", tmp_path / "site", tmp_path / "rt"
    sent = []

    def sender(title, message, priority, tags=None):
        sent.append((title, priority))
        return True, "sent"
    t0 = dt.datetime(2026, 11, 25, 9, 0, tzinfo=dt.timezone.utc)
    fd = main(data, site, rt, now=t0, fetchers=fake_sources([80000] * 30, 2.1), sender=sender)
    assert sent == []                                                     # first run: silent baseline
    assert fd["trend_exit"]["state"] == "RISK-ON" and (site / "index.html").exists() and (site / "feed" / "latest.json").exists()
    assert (site / "feed" / "history" / "BTCUSD.csv").exists() and (site / "manifest.webmanifest").exists() and (site / "icons" / "icon-512.png").exists()
    assert (data / "log" / "verdicts.csv").read_text().count("\n") == 2   # header + first-run row
    assert not (data / "state" / "sources.json").exists() and (rt / "sources.json").exists()   # fast bookkeeping stays out of git

    # a weekly close below the break line arrives; the push fails once and is retried
    def broken(title, message, priority, tags=None):
        return False, "ntfy answered HTTP 500"
    t1 = dt.datetime(2026, 11, 30, 0, 20, tzinfo=dt.timezone.utc)
    weeks = [80000] * 30 + [61000]
    import tests.helpers as H
    src = fake_sources(weeks, 2.1)
    src["coinbase"] = lambda entries, ctx: Result(history={"BTCUSD": H.weekly_btc(weeks, last_sunday="2026-11-29")},
                                                   live={"BTCUSD": (61000.0, ctx.now.isoformat())})
    fd = main(data, site, rt, now=t1, fetchers=src, sender=broken)
    st = json.loads((data / "state" / "hub.json").read_text())
    titles = [p["title"] for p in st["outbox"]]
    assert "Trend exit: RISK-OFF" in titles and any(t.startswith("Regime: ") for t in titles) and "macro-hub daily digest" in titles
    assert fd["trend_exit"]["since"] == "2026-11-30T00:20Z"
    fd = main(data, site, rt, now=t1 + dt.timedelta(minutes=15), fetchers=src, sender=sender)
    assert {"Trend exit: RISK-OFF", "macro-hub daily digest"} <= {t for t, _ in sent}
    assert json.loads((data / "state" / "hub.json").read_text())["outbox"] == []
    log = (data / "log" / "verdicts.csv").read_text()
    # one row for the trend/regime change (the digest shared it), then one when the reading itself
    # changed a run later: the "at or below 1.3x" test waits for two runs in a row, like every dial
    assert "RISK-OFF" in log and log.count("\n") == 4 and "fairly cheap" in log.splitlines()[-1]
    assert "btc_weekly" in (data / "log" / "dial_changes.csv").read_text()


def test_go_live_does_not_push_changes_that_are_only_the_warm_up_settling(tmp_path):
    """The warm-up replay dates back-filled data later than a live run sees it (margin debt is the
    real case: the replay ended on September's figure, the live run saw October's). The baseline
    must be the settled live picture, so the runs after go-live stay silent."""
    data, site, rt = tmp_path / "data", tmp_path / "site", tmp_path / "rt"
    sent = []
    sender = lambda title, message, priority, tags=None: (sent.append(title), (True, "sent"))[1]
    months = pd.date_range(end="2026-10-31", periods=20, freq="ME")
    debt = pd.Series([1000.0] * 12 + [1080.0, 1160.0, 1250.0, 1255.0, 1250.0, 1230.0, 1225.0, 1262.0], index=months)   # last month back above 0
    src = fake_sources([80000] * 30, 2.1)
    src["finra"] = lambda entries, ctx: Result(history={"MARGIN_DEBT": debt})
    t0 = dt.datetime(2026, 11, 25, 9, 0, tzinfo=dt.timezone.utc)
    fd = main(data, site, rt, now=t0, fetchers=src, sender=sender)
    assert next(d for d in fd["dials"] if d["id"] == "margin_debt")["colour"] == "amber"      # already settled at the baseline
    for i in (1, 2, 3):
        main(data, site, rt, now=t0 + dt.timedelta(minutes=15 * i), fetchers=src, sender=sender)
    assert sent == [] and not (data / "log" / "dial_changes.csv").exists()


def test_with_pushes_switched_off_waiting_pushes_are_kept_not_discarded(tmp_path):
    data, site, rt = tmp_path / "data", tmp_path / "site", tmp_path / "rt"
    t0 = dt.datetime(2026, 11, 25, 9, 0, tzinfo=dt.timezone.utc)
    src = fake_sources([80000] * 30, 2.1)
    main(data, site, rt, now=t0, fetchers=src, sender=lambda *a, **k: (True, "sent"))
    hub = data / "state" / "hub.json"
    st = json.loads(hub.read_text())
    st["outbox"] = [{"title": "waiting", "message": "m", "priority": 3}]
    hub.write_text(json.dumps(st))
    main(data, site, rt, now=t0 + dt.timedelta(minutes=15), fetchers=src, push=False)
    assert [p["title"] for p in json.loads(hub.read_text())["outbox"]] == ["waiting"]


def test_a_long_silence_is_announced_when_the_hub_comes_back(tmp_path):
    data, site, rt = tmp_path / "data", tmp_path / "site", tmp_path / "rt"
    sent = []
    sender = lambda title, message, priority, tags=None: (sent.append((title, priority, message)), (True, "sent"))[1]
    src = fake_sources([80000] * 30, 2.1)
    t0 = dt.datetime(2026, 11, 25, 9, 0, tzinfo=dt.timezone.utc)
    main(data, site, rt, now=t0, fetchers=src, sender=sender)
    main(data, site, rt, now=t0 + dt.timedelta(minutes=15), fetchers=src, sender=sender)
    assert not [t for t, _, _ in sent if "running again" in t]              # a normal 15-minute gap says nothing
    main(data, site, rt, now=t0 + dt.timedelta(hours=7), fetchers=src, sender=sender)
    back = [x for x in sent if x[0] == "macro-hub is running again"]
    assert len(back) == 1 and back[0][1] == 4 and "7 hours" in back[0][2]
