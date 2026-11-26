"""Log-regression channel, with made-up price histories. Nothing is fetched."""
import math

import numpy as np
import pandas as pd
import pytest

from hub import alerts
from hub.outputs import dashboard
from hub.signals.valuation import DRIFT, LABEL, NO_FIT, all_coins, fit, reading, zone
from hub.util import load_config
from tests.helpers import view

C = load_config()


def exp_series(years, growth=1.0, noise=None, end="2026-11-25", start_price=10.0):
    """Daily closes growing at `growth` a year (1.0 = +100%), times exp(noise)."""
    idx = pd.date_range(end=end, periods=int(years * 365.25) + 1, freq="D")
    t = np.arange(len(idx))
    y = math.log(start_price) + t * math.log(1 + growth) / 365
    if noise is not None:
        y = y + noise(t)
    return pd.Series(np.exp(y), index=idx)


def wave(amp, period_days=1461):
    return lambda t: amp * np.sin(2 * math.pi * t / period_days)


# ------------------------------------------------------------------ the arithmetic
def test_a_clean_exponential_is_recovered_exactly():
    s = exp_series(8, growth=1.0)
    f = fit(s)
    assert abs((math.exp(f["slope"] * 365) - 1) - 1.0) < 1e-6 and f["r2"] > 0.999999 and f["sd"] < 1e-9


def test_reading_is_log_distance_over_residual_sd():
    s = exp_series(8, growth=0.6, noise=wave(0.5))
    f = fit(s)
    t = np.array((s.index - s.index[0]).days, dtype=float)
    resid = np.log(s.values) - (f["intercept"] + f["slope"] * t)
    assert abs(f["sd"] - resid.std(ddof=0)) < 1e-12                        # population standard deviation
    r = reading(s, C)
    fair = math.exp(f["intercept"] + f["slope"] * t[-1])
    assert abs(r["fair_value"] - fair) < 1e-6 * fair
    assert abs(r["z"] - round((math.log(s.iloc[-1]) - math.log(fair)) / f["sd"], 3)) < 1e-9
    for k in (-3, -2, -1, 1, 2, 3):                                         # price at each band
        assert abs(r["bands"][f"{k:+d}"] - fair * math.exp(k * f["sd"])) < 1e-6 * fair
    assert abs(r["growth_per_year"] - (math.exp(f["slope"] * 365) - 1)) < 1e-12 and 0.4 < r["growth_per_year"] < 0.8 and r["r2"] > 0.8


def test_log_base_and_price_units_do_not_change_the_reading():
    s = exp_series(6, growth=0.8, noise=wave(0.4))
    a, b = reading(s, C), reading(s * 1000, C)
    assert a["z"] == b["z"] and abs(b["fair_value"] / a["fair_value"] - 1000) < 1e-6


def test_a_price_below_the_line_reads_oversold_and_above_reads_overbought():
    base = exp_series(6, growth=0.8, noise=wave(0.3))
    low, high = base.copy(), base.copy()
    low.iloc[-1] *= math.exp(-0.9)
    high.iloc[-1] *= math.exp(0.9)
    assert reading(low, C)["z"] < -1 and reading(low, C)["colour"] == "green"
    assert reading(high, C)["z"] > 1 and reading(high, C)["colour"] == "red"


@pytest.mark.parametrize("z,name,colour", [
    (-3.4, "-3 SD oversold", "green"), (-3.0, "-2 SD oversold", "green"), (-2.5, "-2 SD oversold", "green"),
    (-2.0, "-1 SD oversold", "green"), (-1.01, "-1 SD oversold", "green"), (-1.0, "fair value", "amber"),
    (0.0, "fair value", "amber"), (1.0, "fair value", "amber"), (1.5, "+1 SD overbought", "red"),
    (2.2, "+2 SD overbought", "red"), (3.0, "+2 SD overbought", "red"), (3.01, "+3 SD overbought", "red"), (9.0, "+3 SD overbought", "red")])
def test_seven_zones_with_edges_belonging_to_the_zone_nearer_fair_value(z, name, colour):
    assert zone(z) == (name, colour)


def test_live_price_is_used_for_now_but_a_wild_print_is_ignored():
    s = exp_series(6, growth=0.8, noise=wave(0.3))
    last = s.iloc[-1]
    r = reading(s, C, price_now=last * 1.05, today=s.index[-1] + pd.Timedelta(days=1))
    assert r["price"] == last * 1.05 and r["price_is_live"] is True
    bad = reading(s, C, price_now=last * 3, today=s.index[-1])
    assert bad["price"] == last and bad["price_is_live"] is False


def test_fair_value_is_for_today_not_the_last_close():
    s = exp_series(6, growth=1.0)
    a = reading(s, C, today=s.index[-1])
    b = reading(s, C, today=s.index[-1] + pd.Timedelta(days=365))
    assert abs(b["fair_value"] / a["fair_value"] - 2.0) < 1e-6              # one year of +100% growth


# ------------------------------------------------------------------ honesty rules
def test_under_one_year_gives_no_dial():
    r = reading(exp_series(0.8, growth=1.0, noise=wave(0.2, 90)), C)
    assert r["status"] == "too_little" and "too little history" in r["text"] and "z" not in r


def test_under_three_years_is_greyed_with_months_used():
    r = reading(exp_series(1.9, growth=1.0, noise=wave(0.2, 200)), C)
    assert r["status"] == "greyed" and r["warnings"] == ["short history, low confidence (23 months used)"] and "z" in r


def test_a_poor_fit_is_greyed_with_the_agreed_wording():
    flat = exp_series(6, growth=0.0, noise=wave(1.0))                       # no trend at all: R squared near 0
    r = reading(flat, C)
    assert r["r2"] < 0.3 and r["status"] == "greyed" and r["warnings"] == [NO_FIT]
    assert NO_FIT == "the line does not fit this coin's history; reading not meaningful"


def test_short_and_poor_fit_both_say_so():
    r = reading(exp_series(2, growth=0.0, noise=wave(1.0, 200)), C)
    assert r["status"] == "greyed" and len(r["warnings"]) == 2


def test_a_good_long_fit_is_not_greyed():
    r = reading(exp_series(8, growth=0.8, noise=wave(0.3)), C)
    assert r["status"] == "ok" and r["warnings"] == [] and r["label"] == LABEL and r["drift_note"] == DRIFT
    assert LABEL == "Trend-based estimate. Assumes past growth continues."


# ------------------------------------------------------------------ all coins, page, digest, and staying out of the rules
def ten_coin_view(tmp_path):
    data, live = {}, {}
    for i, c in enumerate(C["valuations"]["coins"]):
        yrs = [16, 11, 6.6, 3.3, 9, 6, 10, 1.9, 1.5, 0.5][i]
        data[c["history"]] = exp_series(yrs, growth=0.7, noise=wave(0.4), end="2026-11-25")
    return view(tmp_path, data, now="2026-11-26 03:00", live=live)


def test_all_ten_coins_in_order(tmp_path):
    vals = all_coins(ten_coin_view(tmp_path), C)
    assert [v["sym"] for v in vals] == ["BTC", "ETH", "SOL", "SUI", "LINK", "NEAR", "ZEC", "HYPE", "WAL", "DEEP"]
    assert [v["status"] for v in vals][-3:] == ["greyed", "greyed", "too_little"]


def test_the_tab_has_one_card_per_coin_and_no_outside_scripts(tmp_path):
    from tests.test_outputs import small_feed
    fd, _ = small_feed(tmp_path / "f")
    fd["valuations"] = all_coins(ten_coin_view(tmp_path), C)
    page = dashboard.render(fd)
    assert page.count('class="cvcard') == 10 and page.count('class="cvstrip"') == 1 and page.count('data-i=') == 10
    assert "scroll-snap-type:x mandatory" in page and "<script src" not in page
    assert page.count(LABEL) == 10 and page.count(DRIFT.replace("'", "&#x27;")) == 10
    assert page.count("Short history, low confidence") == 2 and "too little history" in page
    for lab in ("−3 SD", "−2 SD", "−1 SD", "fair", "+1 SD", "+2 SD", "+3 SD"):
        assert lab in page
    assert "assumes +" in page and "% a year" in page and "Coin Metrics</a> community data, CC BY-NC 4.0" in page
    assert page.index('class="tabs"') < page.index('class="pane p1"') < page.index('class="pane p2"')


def test_cards_always_carry_a_word_and_symbol_not_just_colour(tmp_path):
    vals = all_coins(ten_coin_view(tmp_path), C)
    for v in vals:
        if v["status"] in ("ok", "greyed"):
            card = dashboard.valuation_card(v)
            assert v["zone"][3:] in card and any(sym in card for sym in "▲●▼")
            assert f'{v["z"]:+.2f} SD'.replace("-", "\u2212") in card
            assert card.index("Trend-based estimate") < card.index('<div class="cvdial"><svg', card.index("Log-regression channel") if "Log-regression channel" in card else 0)


def test_valuations_are_one_digest_line_and_never_a_push_or_part_of_the_reading(tmp_path):
    from tests.test_outputs import small_feed
    fd, out = small_feed(tmp_path / "f")
    before = (fd["reading"]["label"], fd["regime"]["name"], alerts.summary(fd))
    fd["valuations"] = all_coins(ten_coin_view(tmp_path), C)
    assert (fd["reading"]["label"], fd["regime"]["name"], alerts.summary(fd)) == before
    changed = [dict(v) for v in fd["valuations"]]
    for v in changed:
        if "z" in v:
            v.update(z=-v["z"], colour="red" if v["colour"] == "green" else "green")
    fd2 = dict(fd, valuations=changed)
    assert alerts.plan(alerts.summary(fd), fd2, C) == []                     # a valuation change pushes nothing
    d = alerts.digest(fd, C)["message"]
    lines = [l for l in d.split("\n") if l.startswith("Coin valuations")]
    assert len(lines) == 1 and "BTC " in lines[0] and "DEEP" in lines[0] and "(* greyed: short history or the line does not fit)" in lines[0]


def test_the_card_renders_from_the_published_json_too(tmp_path):
    import json
    v = {"sym": "BTC", "name": "Bitcoin", **reading(exp_series(8, growth=0.8, noise=wave(0.3)), C)}
    back = json.loads(json.dumps(v, default=str))
    assert dashboard.valuation_card(back) == dashboard.valuation_card(v)


# ------------------------------------------------------------------ stretch from trend
from hub.signals.valuation import STRETCH_LABEL, stretch  # noqa: E402


def test_stretch_is_log_price_over_200_day_average_scored_against_its_own_history():
    s = exp_series(4, growth=0.5, noise=wave(0.3, 400))
    st = stretch(s, C)
    ma = s.rolling(200).mean()
    m = np.log(s / ma).dropna()
    now = math.log(s.iloc[-1] / ma.iloc[-1])
    assert st["status"] == "ok" and st["days"] == len(m)
    assert abs(st["z"] - round((now - m.mean()) / m.std(ddof=0), 3)) < 1e-9
    assert abs(st["ratio"] - s.iloc[-1] / ma.iloc[-1]) < 1e-12 and st["label"] == STRETCH_LABEL
    assert STRETCH_LABEL == "Compared with its own recent trend, not a fair value"


def test_stretch_needs_365_days_of_the_measure():
    assert stretch(exp_series(1.5, growth=0.5), C)["status"] == "too_little"           # 548 days: 349 of the measure
    assert stretch(exp_series(1.55, growth=0.5), C)["status"] == "ok"                  # 567 days: 368 of the measure
    assert stretch(exp_series(0.3, growth=0.5), C)["text"] == "too little history"


def test_stretch_reads_high_after_a_spike_and_low_after_a_crash():
    base = exp_series(4, growth=0.5, noise=wave(0.2, 300))
    up, down = base.copy(), base.copy()
    up.iloc[-30:] *= np.exp(np.linspace(0, 0.8, 30))
    down.iloc[-30:] *= np.exp(np.linspace(0, -0.8, 30))
    assert stretch(up, C)["colour"] == "red" and stretch(down, C)["colour"] == "green"


def test_greyed_cards_lead_with_the_stretch_reading(tmp_path):
    vals = all_coins(ten_coin_view(tmp_path), C)
    for v in vals:
        card = dashboard.valuation_card(v)
        if v["status"] == "greyed" and v["stretch"]["status"] == "ok":
            assert card.index("Stretch from trend") < card.index("Log-regression channel")
        elif v["status"] == "ok":
            assert card.index("<svg") < card.index("Stretch from trend")            # under the log-regression dial
        assert "Stretch from trend" in card and "not a fair value" in card


# ------------------------------------------------------------------ Bitcoin moving averages (context only)
def test_btc_moving_average_dial_bands_and_200_week_marker(tmp_path):
    from hub.signals import dials as D
    from tests.helpers import daily
    for i, (last, want) in enumerate([(0.79, "green"), (0.8, "green"), (1.5, "amber"), (2.39, "amber"), (2.4, "red")]):
        s = daily([100.0] * 1500)                                  # 200-day average exactly 100; the live price is tested against it
        r = D.btc_ma(view(tmp_path / str(i), {"BTCUSD": s}, live={"BTCUSD": 100.0 * last}), C)
        assert r.colour == want, (last, r.colour)
    s = daily([50.0] * 1200 + [100.0] * 300)
    r = D.btc_ma(view(tmp_path / "w", {"BTCUSD": s}), C)
    assert r.extra["above_200w"] is True and "above the 200-week average" in r.text and r.extra["context_only"]
    assert abs(r.extra["ma200d"] - 100.0) < 1e-9


def test_btc_moving_average_dial_is_context_only(tmp_path):
    from hub.signals.engine import evaluate, reading
    from tests.helpers import daily
    from tests.test_outputs import small_feed
    fd, out = small_feed(tmp_path)
    d = next(x for x in fd["dials"] if x["id"] == "btc_ma")
    assert d["context_only"] is True
    sec = next(x for x in fd["sections"] if x["id"] == "valuation")
    assert "btc_ma" in sec["dials"]                                                  # shown in the group ...
    prev = alerts.summary(fd)
    prev["dials"]["btc_ma"] = "green" if d["colour"] != "green" else "red"
    assert [p for p in alerts.plan(prev, fd, C) if "moving" in p["title"]] == []    # ... never pushes
    r = out["readings"]
    before = reading(r, C)["headline"]
    r["btc_ma"].update(colour="red")
    assert reading(r, C)["headline"] == before                                       # ... and never moves the reading
