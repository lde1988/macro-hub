"""Coin valuations, with made-up price histories. Nothing is fetched."""
import math

import numpy as np
import pandas as pd
import pytest

from hub import alerts
from hub.outputs import dashboard
from hub.signals.valuation import APPROX, LABEL, METHODS, NO_FIT, SHORT_LABEL, all_coins, channel, one_year, revenue, zone
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


# ------------------------------------------------------------------ zones
@pytest.mark.parametrize("z,name,colour", [
    (-3.4, "-3 SD oversold", "green"), (-3.0, "-2 SD oversold", "green"), (-2.5, "-2 SD oversold", "green"),
    (-2.0, "-1 SD oversold", "green"), (-1.01, "-1 SD oversold", "green"), (-1.0, "below fair value", "amber"),
    (-0.01, "below fair value", "amber"), (0.0, "above fair value", "amber"), (1.0, "above fair value", "amber"),
    (1.5, "+1 SD overbought", "red"), (2.2, "+2 SD overbought", "red"), (3.0, "+2 SD overbought", "red"),
    (3.01, "+3 SD overbought", "red"), (9.0, "+3 SD overbought", "red")])
def test_eight_zones_with_the_fair_band_split_at_zero(z, name, colour):
    assert zone(z) == (name, colour)


# ------------------------------------------------------------------ short term: 1-year z-score
def test_one_year_z_is_log_price_against_the_last_365_closes_sample_sd():
    s = exp_series(3, growth=0.5, noise=wave(0.3, 200))
    r = one_year(s, C)
    w = np.log(s.iloc[-365:].values)
    assert r["status"] == "ok"
    assert abs(r["z"] - round((math.log(s.iloc[-1]) - w.mean()) / w.std(ddof=1), 3)) < 1e-9
    assert abs(r["fair_value"] - math.exp(w.mean())) < 1e-9 * r["fair_value"]
    for k in (-3, -2, -1, 1, 2, 3):
        assert abs(r["bands"][f"{k:+d}"] - math.exp(w.mean() + k * w.std(ddof=1))) < 1e-9 * r["fair_value"]
    assert r["window_from"] == str(s.index[-365])[:10] and r["label"] == SHORT_LABEL


def test_one_year_uses_only_the_last_365_days():
    s = exp_series(3, growth=0.5, noise=wave(0.3, 200))
    t = s.copy()
    t.iloc[:-365] = t.iloc[:-365] * 50                       # anything older than a year makes no difference
    assert one_year(s, C)["z"] == one_year(t, C)["z"]


def test_one_year_needs_365_days():
    assert one_year(exp_series(0.99, growth=0.5), C)["status"] == "too_little"
    assert one_year(exp_series(1.0, growth=0.5), C)["status"] == "ok"            # 366 closes
    assert one_year(pd.Series(dtype=float), C)["text"] == "too little history"


def test_one_year_uses_a_live_price_but_ignores_a_wild_print():
    s = exp_series(2, growth=0.5, noise=wave(0.2, 100))
    last = s.iloc[-1]
    assert one_year(s, C, price_now=last * 1.05)["price_is_live"] is True
    bad = one_year(s, C, price_now=last * 3)
    assert bad["price"] == last and bad["price_is_live"] is False


def test_a_spike_reads_overbought_and_a_crash_oversold():
    base = exp_series(2, growth=0.0, noise=wave(0.2, 90))
    up, down = base.copy(), base.copy()
    up.iloc[-1] *= math.exp(0.6)
    down.iloc[-1] *= math.exp(-0.6)
    assert one_year(up, C)["colour"] == "red" and one_year(down, C)["colour"] == "green"


# ------------------------------------------------------------------ long term: 4-year trend channel
def test_channel_fits_only_the_last_1461_days():
    s = exp_series(8, growth=0.44, noise=wave(0.3, 500))
    r = channel(s, C)
    w = s.iloc[-1461:]
    t = (w.index - w.index[0]).days.values.astype(float)
    b, a = np.polyfit(t, np.log(w.values), 1)
    resid = np.log(w.values) - (a + b * t)
    assert r["window_from"] == str(w.index[0])[:10]
    assert abs(r["growth_per_year"] - (math.exp(b * 365) - 1)) < 1e-9
    assert abs(r["z"] - round((math.log(w.iloc[-1]) - (a + b * t[-1])) / resid.std(), 3)) < 1e-9
    older = s.copy()
    older.iloc[:-1461] = older.iloc[:-1461] * 10              # history older than 4 years makes no difference
    assert channel(older, C)["z"] == r["z"]


def test_channel_recovers_a_clean_trend():
    r = channel(exp_series(5, growth=0.44), C)
    assert abs(r["growth_per_year"] - 0.44) < 1e-6 and r["r2"] > 0.999
    assert r["label"] == LABEL


def test_channel_only_for_coins_with_four_years():
    assert channel(exp_series(3.9, growth=0.5), C) is None
    assert channel(exp_series(4.0, growth=0.5, noise=wave(0.2, 300)), C) is not None


def test_channel_r_squared_rule():
    flat = exp_series(5, growth=0.0, noise=wave(1.0, 700))
    r = channel(flat, C)
    assert r["r2"] < 0.3 and r["status"] == "greyed" and r["warnings"] == [NO_FIT]


def test_channel_fair_value_is_for_today():
    s = exp_series(5, growth=1.0)
    a = channel(s, C, today=s.index[-1])
    b = channel(s, C, today=s.index[-1] + pd.Timedelta(days=365))
    assert abs(b["fair_value"] / a["fair_value"] - 2.0) < 1e-6


# ------------------------------------------------------------------ all coins, page, digest, staying out of the rules
def ten_coin_view(tmp_path):
    data = {}
    for i, c in enumerate(C["valuations"]["coins"]):
        yrs = [16, 11, 6.6, 3.3, 9, 6, 10, 1.9, 0.6, 2]
        data[c["history"]] = exp_series(yrs[i], growth=0.7, noise=wave(0.4, 400), end="2026-11-25")
    return view(tmp_path, data, now="2026-11-26 03:00")


def test_all_ten_coins_in_order(tmp_path):
    vals = all_coins(ten_coin_view(tmp_path), C)
    assert [v["sym"] for v in vals] == ["BTC", "ETH", "SOL", "SUI", "LINK", "NEAR", "ZEC", "HYPE", "WAL", "DEEP"]
    assert [v["short"]["status"] for v in vals] == ["ok"] * 8 + ["too_little", "ok"]
    assert [v["long"] is not None for v in vals] == [True, True, True, False, True, True, True, False, False, False]
    assert all(v["methods"] == METHODS for v in vals)
    assert METHODS == "Short term: compared with the last year. Long term: trend over the last 4 years."


def test_the_tab_has_one_card_per_coin_and_no_outside_scripts(tmp_path):
    from tests.test_outputs import small_feed
    fd, _ = small_feed(tmp_path / "f")
    fd["valuations"] = all_coins(ten_coin_view(tmp_path), C)
    page = dashboard.render(fd)
    assert page.count('class="cvcard') == 10 and page.count('data-i=') == 10 and "<script src" not in page
    assert page.count("Short term: compared with the last year. Long term: trend over the last 4 years.") == 10
    assert page.count(">Short term: against the last year<") == 10 and page.count(">Long term: trend over the last 4 years<") == 10
    assert "Needs 4 years of prices" in page and "Needs 365 days of prices" in page
    assert "Pal" not in page and "200-day average" not in page.split('class="pane p2"')[1]
    for lab in ("−3 SD", "−2 SD", "−1 SD", "below", "above", "+1 SD", "+2 SD", "+3 SD"):
        assert lab in page
    assert "trend +" in page and "% a year" in page


def test_every_dial_shows_its_sd_number_large_and_a_word(tmp_path):
    for v in all_coins(ten_coin_view(tmp_path), C):
        card = dashboard.valuation_card(v)
        for r in (v["short"], v["long"]):
            if r and r.get("status") in ("ok", "greyed"):
                assert f'>{f"{r[chr(122)]:+.2f}".replace("-", chr(8722))}</text>' in card
                assert r["zone"][3:] in card and any(sym in card for sym in "▲●▼")


def test_short_term_always_leads_and_revenue_comes_last(tmp_path):
    for v in all_coins(ten_coin_view(tmp_path), C):
        card = dashboard.valuation_card(v)
        st, lt = card.index("Short term: against the last year"), card.index("Long term: trend over the last 4 years<")
        assert card.index("cvmethods") < st < lt
        if "Price against revenue" in card:
            assert lt < card.index("Price against revenue")


def test_valuations_are_one_digest_line_and_never_a_push_or_part_of_the_reading(tmp_path):
    from tests.test_outputs import small_feed
    fd, _ = small_feed(tmp_path / "f")
    before = (fd["reading"]["label"], fd["regime"]["name"], alerts.summary(fd))
    fd["valuations"] = all_coins(ten_coin_view(tmp_path), C)
    assert (fd["reading"]["label"], fd["regime"]["name"], alerts.summary(fd)) == before
    flipped = [dict(v, short=dict(v["short"], z=-v["short"].get("z", 0), colour="red")) for v in fd["valuations"]]
    assert alerts.plan(alerts.summary(fd), dict(fd, valuations=flipped), C) == []
    lines = [l for l in alerts.digest(fd, C)["message"].split("\n") if l.startswith("Coins against their last year")]
    assert len(lines) == 1 and "BTC " in lines[0] and "too little history: WAL" in lines[0]


def test_the_card_renders_from_the_published_json_too(tmp_path):
    import json
    v = all_coins(ten_coin_view(tmp_path), C)[0]
    back = json.loads(json.dumps(v, default=str))
    assert dashboard.valuation_card(back) == dashboard.valuation_card(v)


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


# ------------------------------------------------------------------ price against revenue
def flat_fees(days, per_day, end="2026-11-25"):
    return pd.Series(per_day, index=pd.date_range(end=end, periods=days, freq="D"))


RC_MAX = {"fees": "F", "supply": "max", "max_supply": 1_000_000.0}


def test_multiple_is_fully_diluted_value_over_365_days_of_fees():
    price = exp_series(4, growth=0.0, start_price=10.0)                   # flat $10
    fees = flat_fees(1000, 100.0)                                        # $100 a day: $36,500 a year
    r = revenue(price, fees, C, RC_MAX, circulating=250_000.0)
    assert r["status"] == "ok" and abs(r["multiple"] - 10.0 * 1_000_000 / 36_500) < 1e-9
    assert abs(r["z"]) < 1e-9 and r["zone"] == "above fair value" and abs(r["unlock"] - 0.75) < 1e-12


def test_a_jump_in_value_without_more_fees_reads_expensive():
    price = exp_series(4, growth=0.0, start_price=10.0, noise=wave(0.1, 200))
    price.iloc[-1] = price.iloc[-1] * 3
    r = revenue(price, flat_fees(1000, 100.0), C, RC_MAX)
    assert r["z"] > 2 and r["colour"] == "red"
    cheap = exp_series(4, growth=0.0, start_price=10.0, noise=wave(0.1, 200))
    fees = flat_fees(1000, 100.0)
    fees.iloc[-200:] = 400.0                                             # fees quadruple, price does not
    assert revenue(cheap, fees, C, RC_MAX)["colour"] == "green"


def test_needs_a_year_of_fees_plus_a_year_of_the_multiple():
    price = exp_series(4, growth=0.0)
    r = revenue(price, flat_fees(703, 100.0), C, RC_MAX)
    assert r["status"] == "waiting" and r["available_in"] == 26             # HYPE today: 703 days of fees
    assert revenue(price, flat_fees(729, 100.0), C, RC_MAX)["status"] == "ok"
    assert revenue(price, flat_fees(191, 100.0), C, RC_MAX)["available_in"] == 538


def test_supply_kinds():
    price = exp_series(4, growth=0.0, start_price=10.0)
    fees = flat_fees(1000, 100.0)
    sup = pd.Series(np.linspace(100.0, 200.0, len(price)), index=price.index)       # supply doubles over the period
    hist = revenue(price, fees, C, {"supply": "history"}, supply=sup)
    assert abs(hist["fdv"] - 10.0 * 200.0) < 1e-6 and hist["z"] > 1                # value rose with supply, fees did not
    cur = revenue(price, fees, C, {"supply": "current", "approximate": True}, total=200.0, circulating=150.0)
    assert cur["approximate"] is True and abs(cur["unlock"] - 0.25) < 1e-12 and abs(cur["z"]) < 1e-9
    assert APPROX == "approximate: past supply estimated"


def test_revenue_block_wording(tmp_path):
    price = exp_series(4, growth=0.0, start_price=10.0, noise=wave(0.1, 200))
    ok = revenue(price, flat_fees(1000, 100.0), C, {"supply": "current", "approximate": True}, total=200.0, circulating=150.0)
    html = dashboard.revenue_block(ok)
    assert "Approximate: past supply estimated." in html and "Still to unlock: 25% of supply." in html and "grey" in html
    eth = revenue(price, flat_fees(1000, 100.0), C, {"supply": "max", "max_supply": 100.0, "note": "Its fee history spans the move to rollups, which cut fees on Ethereum itself."})
    assert "spans the move to rollups" in dashboard.revenue_block(eth)
    wait = revenue(price, flat_fees(703, 100.0), C, RC_MAX)
    assert "available in 26 days" in dashboard.revenue_block(wait)


def test_revenue_is_never_the_lead_reading(tmp_path):
    price = exp_series(4, growth=0.0, start_price=10.0, noise=wave(0.1, 200))
    v = {"sym": "SOL", "name": "Solana", "methods": METHODS, "years": 4.0,
         "short": one_year(price, C), "long": channel(price, C),
         "revenue": revenue(price, flat_fees(1000, 100.0), C, {"supply": "current", "approximate": True}, total=200.0)}
    card = dashboard.valuation_card(v)
    assert card.index(">Short term: against the last year<") < card.index(">Long term: trend over the last 4 years<") < card.index("Price against revenue")



def test_link_revenue_is_labelled_short_fee_history_and_greyed():
    link = next(c for c in C["valuations"]["coins"] if c["sym"] == "LINK")
    price = exp_series(4, growth=0.0, start_price=10.0, noise=wave(0.1, 200))
    r = revenue(price, flat_fees(1000, 100.0), C, link["revenue"])
    assert r["caveat"] == "short fee history" and r["approximate"] is False
    html = dashboard.revenue_block(r)
    assert "Short fee history." in html and 'cvblock grey' in html
    for sym in ("SOL", "NEAR"):
        rc = next(c for c in C["valuations"]["coins"] if c["sym"] == sym)["revenue"]
        assert revenue(price, flat_fees(1000, 100.0), C, rc, total=100.0)["caveat"] == APPROX
    for sym in ("SUI", "ETH"):
        rc = next(c for c in C["valuations"]["coins"] if c["sym"] == sym)["revenue"]
        assert not rc.get("caveat") and not rc.get("approximate")
