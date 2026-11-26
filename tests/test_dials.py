"""One test per dial band, with made-up data. Colour rule everywhere:
green = supports buying, amber = neutral, red = argues against."""
import pandas as pd
import pytest

from hub.signals import dials as D
from hub.signals.core import A, G, R, band
from tests.helpers import END, cfg, daily, ecb_for_dxy, flat, ramp, view, weekly_btc

C = cfg()


# ------------------------------------------------------------------ the band helper
def test_band_edges_are_inclusive_as_written():
    assert band(0.7, [0.7, 3.0], [G, A, R]) == G           # "at or below 0.7"
    assert band(0.71, [0.7, 3.0], [G, A, R]) == A
    assert band(3.0, [0.7, 3.0], [G, A, R]) == A            # "above 3.0" is red
    assert band(30.0, [0, 30], [G, A, R], right=False) == R  # "30% or more"
    assert band(None, [0], [G, R]) is None


def test_band_buffer_holds_the_previous_colour_near_an_edge():
    e, c = [58600, 127200], [G, A, R]
    assert band(59000, e, c, prev=G, buf=0.02, rel=True) == G    # within 2% above the edge: stays green
    assert band(59800, e, c, prev=G, buf=0.02, rel=True) == A    # more than 2% above: changes
    assert band(58000, e, c, prev=A, buf=0.02, rel=True) == A    # within 2% below: stays amber
    assert band(57400, e, c, prev=A, buf=0.02, rel=True) == G
    assert band(58000, e, c, prev=None, buf=0.02, rel=True) == G  # no history: plain bands


# ------------------------------------------------------------------ A. Is it cheap?
def price_view(tmp_path, price, rp=53000.0, **more):
    data = {"BTCUSD": flat(60000, 30), "BV_REALIZED_PRICE": flat(rp, 30)}
    data.update(more)
    return view(tmp_path, data, live={"BTCUSD": price})


@pytest.mark.parametrize("price,prev,want", [
    (58600, None, G), (58601, None, A), (127200, None, A), (127300, None, R),
    (59500, G, G), (59800, G, A), (58000, A, A), (57400, A, G), (126000, R, R), (124000, R, A)])
def test_btc_price_bands_and_two_percent_buffer(tmp_path, price, prev, want):
    assert D.btc_price(price_view(tmp_path, price), C, prev).colour == want


def test_btc_price_shows_ratio_and_live_cost_markers(tmp_path):
    r = D.btc_price(price_view(tmp_path, 59200, BV_LTH_REALIZED_PRICE=flat(48300, 5), BV_STH_REALIZED_PRICE=flat(72400, 5)), C)
    assert round(r.extra["ratio_to_realised"], 3) == round(59200 / 53000, 3)
    assert r.extra["lth_cost"] == 48300 and r.extra["sth_cost"] == 72400 and r.extra["notes"] == []


def test_btc_price_falls_back_to_coin_metrics_then_fixed_level(tmp_path):
    v = view(tmp_path, {"BTCUSD": flat(60000, 5), "CM_REALIZED_PRICE": flat(52000, 5)})
    assert D.btc_price(v, C).extra["realised_price_source"] == "Coin Metrics"
    v = view(tmp_path / "b", {"BTCUSD": flat(60000, 5)})
    r = D.btc_price(v, C)
    assert r.extra["realised_price"] == C["levels"]["realised_price"] and "fixed level" in r.extra["notes"][0]


def test_btc_price_flags_sources_more_than_five_percent_apart(tmp_path):
    r = D.btc_price(price_view(tmp_path, 60000, CM_REALIZED_PRICE=flat(56000, 5)), C)
    assert any("disagree" in n for n in r.extra["notes"])
    r = D.btc_price(price_view(tmp_path / "b", 60000, CM_REALIZED_PRICE=flat(53500, 5)), C)
    assert r.extra["notes"] == []


def test_replays_use_dynamic_levels_live_use_fixed_and_shows_both(tmp_path):
    replay = cfg(dynamic_levels={"use_for_colours": True})
    assert D.btc_price(price_view(tmp_path, 11000, rp=10000), replay).colour == G      # 1.10x realised price
    assert D.btc_price(price_view(tmp_path / "b", 11100, rp=10000), replay).colour == A
    live = D.btc_price(price_view(tmp_path / "c", 59200), C)                            # fixed 58,600 colours the dial
    assert live.extra["value_zone"] == 58600 and round(live.extra["dynamic_value_zone"]) == 58300
    assert "fixed" in live.text and "1.10x" in live.text


def test_weekly_lines_follow_short_term_holder_cost_in_replays(tmp_path):
    replay = cfg(dynamic_levels={"use_for_colours": True})
    data = {"BTCUSD": weekly_btc([12000, 9500, 9900, 10100]), "BV_STH_REALIZED_PRICE": flat(10000, 60)}
    assert D.btc_weekly_dial(view(tmp_path / "a", {**data, "BTCUSD": weekly_btc([12000, 9500])}), replay).colour == R       # below 0.96 x 10,000
    assert D.btc_weekly_dial(view(tmp_path / "b", {**data, "BTCUSD": weekly_btc([12000, 9500, 9900])}), replay).colour == R  # above break, below reclaim
    assert D.btc_weekly_dial(view(tmp_path / "c", data), replay).colour == G                                                  # above 10,000: reclaimed
    assert D.weekly_reclaim(view(tmp_path / "d", data), replay).colour == G
    assert D.btc_weekly_dial(view(tmp_path / "e", {**data, "BTCUSD": weekly_btc([12000, 9700])}), replay).colour == A


def test_live_weekly_dial_shows_the_dynamic_lines_beside_the_fixed_ones(tmp_path):
    r = D.btc_weekly_dial(view(tmp_path, {"BTCUSD": weekly_btc([80000, 61163]), "BV_STH_REALIZED_PRICE": flat(72410, 30)}), C)
    assert r.colour == R and r.extra["reclaim_level"] == 73000 and r.extra["dynamic_reclaim_level"] == 72410
    assert round(r.extra["dynamic_break_level"]) == round(72410 * 0.96) and "short-term holder cost" in r.text


@pytest.mark.parametrize("weeks,want,brk", [
    ([80000, 69000], R, True),                 # weekly close below 70,000: break
    ([80000, 69000, 72000], R, True),          # back above 70,000 but not above 73,000: still a break
    ([80000, 69000, 72000, 74000], G, False),  # reclaimed above 73,000
    ([80000, 71000], A, False),                # between the levels with no break in force
    ([80000, 75000], G, False)])
def test_btc_weekly_break_and_reclaim(tmp_path, weeks, want, brk):
    r = D.btc_weekly_dial(view(tmp_path, {"BTCUSD": weekly_btc(weeks)}), C)
    assert r.colour == want and r.extra["break_in_force"] == brk


def test_btc_weekly_uses_the_sunday_candle_only(tmp_path):
    s = weekly_btc([80000, 80000])
    s[pd.Timestamp("2026-11-24")] = 60000      # a Tuesday dip is not a weekly close
    assert D.btc_weekly_dial(view(tmp_path, {"BTCUSD": s}), C).colour == G


@pytest.mark.parametrize("last,want", [(0.90, G), (1.10, R), (1.005, A)])
def test_weekly_move_in_standard_deviations(tmp_path, last, want):
    weeks, p = [], 60000.0
    for i in range(60):
        p *= 1.01 if i % 2 else 0.99
        weeks.append(p)
    weeks.append(p * last)
    assert D.weekly_move(view(tmp_path, {"BTCUSD": weekly_btc(weeks)}), C).colour == want


@pytest.mark.parametrize("x,want", [(0.47, G), (0.70, G), (0.71, A), (3.0, A), (3.01, R)])
def test_lth_sopr_bands(tmp_path, x, want):
    r = D.lth_sopr(view(tmp_path, {"BV_LTH_SOPR_1M": flat(x, 5), "BV_LTH_SOPR_1W": flat(0.6, 5)}), C)
    assert r.colour == want and r.extra["sopr_7d"] == 0.6


def test_net_loss_is_green_only_when_losses_are_extreme_against_history(tmp_path):
    cap = flat(1e12, 500)
    quiet = [(-1) ** i * 1e9 * (i % 50) for i in range(499)]            # mixed small profits and losses
    spike = view(tmp_path, {"BV_NET_PNL_1M": daily(quiet + [-60e9]), "BV_REALIZED_CAP": cap})
    r = D.net_loss(spike, C)
    assert r.colour == G and r.value == 100.0
    assert round(r.extra["net_loss_pct_of_realised_cap"], 2) == 6.0
    assert round(r.extra["share_of_feb_2026_peak"], 2) == 2.0             # marker only: 60bn against the 30bn February peak
    calm = view(tmp_path / "b", {"BV_NET_PNL_1M": daily(quiet + [-10e9]), "BV_REALIZED_CAP": cap})
    assert D.net_loss(calm, C).colour == A                                 # never red


def test_net_loss_needs_enough_history(tmp_path):
    v = view(tmp_path, {"BV_NET_PNL_1M": flat(-1e9, 100), "BV_REALIZED_CAP": flat(1e12, 100)})
    assert D.net_loss(v, C).colour is None


@pytest.mark.parametrize("last,want", [(1.10, G), (0.90, R), (1.0, A)])
def test_btc_against_nasdaq_trend(tmp_path, last, want):
    btc = daily([60000] * 149 + [60000 * last], freq="B")
    v = view(tmp_path, {"BTCUSD": btc, "NASDAQ100": flat(25000, 150, freq="B")})
    assert D.btc_ndx(v, C).colour == want


def test_alt_value_has_no_colour_until_30_days_of_history(tmp_path):
    def mk(n, growth):
        return {"CG_TOTAL_MCAP": ramp(2.0e12, 2.0e12 * growth, n), "CG_BTC_DOM": flat(50.0, n), "STABLE_ALL": flat(0.2e12, n)}
    r = D.alt_value(view(tmp_path, mk(10, 1.0)), C)
    assert r.colour is None and "collecting history" in r.text
    assert D.alt_value(view(tmp_path / "b", mk(40, 1.0)), C).colour == A


def test_alt_value_removes_stablecoins(tmp_path):
    n = 40
    v = view(tmp_path, {"CG_TOTAL_MCAP": flat(2.0e12, n), "CG_BTC_DOM": flat(50.0, n), "STABLE_ALL": flat(0.2e12, n)})
    assert round(D.alt_value(v, C).extra["ratio"], 2) == 0.80   # (2.0 - 1.0 - 0.2) / 1.0


@pytest.mark.parametrize("mult,want", [(1.15, G), (0.85, R), (1.02, A)])
def test_alt_watchlist_against_bitcoin(tmp_path, mult, want):
    data = {"BTCUSD": flat(60000, 60)}
    for c in C["alt_watch"]["coins"]:
        data[c] = daily([10.0] * 59 + [10.0 * mult])
    r = D.alt_watch(view(tmp_path, data), C)
    assert r.colour == want and len(r.extra["coins"]) == 5


# ------------------------------------------------------------------ B. Is stress still building?
def margin_series(tail):
    """12 flat months, a 25% jump over 3 months (about +144% annualised), then `tail`."""
    vals = [1000.0] * 12 + [1080.0, 1160.0, 1250.0] + list(tail)
    return daily(vals, end="2026-10-31", freq="ME")


def test_margin_debt_red_once_fired_amber_while_fading_green_without_a_spike(tmp_path):
    assert D.margin_debt(view(tmp_path / "a", {"MARGIN_DEBT": margin_series([1255.0, 1250.0, 1230.0])}), C).colour == R
    assert D.margin_debt(view(tmp_path / "b", {"MARGIN_DEBT": margin_series([1260.0, 1270.0, 1280.0])}), C).colour == A
    assert D.margin_debt(view(tmp_path / "c", {"MARGIN_DEBT": ramp(1000, 1100, 24, end="2026-10-31", freq="ME")}), C).colour == G


def test_margin_signal_stays_fired_for_the_regime_for_12_months(tmp_path):
    fired_then_bounced = margin_series([1255.0, 1250.0, 1230.0, 1260.0, 1290.0])
    v = view(tmp_path / "a", {"MARGIN_DEBT": fired_then_bounced})
    r = D.margin_debt(v, C)
    assert r.colour == A and r.extra["fired_latched"] is True          # dial back to amber, regime still fired
    long_after = margin_series([1255.0, 1250.0, 1230.0] + [1260.0 + 10 * i for i in range(13)])
    assert D.margin_fired_latched(view(tmp_path / "b", {"MARGIN_DEBT": long_after}), C) is False


@pytest.mark.parametrize("spread,want", [(0.00, G), (-0.02, G), (0.03, A), (0.05, A), (0.06, R)])
def test_sofr_minus_iorb_bands(tmp_path, spread, want):
    v = view(tmp_path, {"SOFR": flat(3.90 + spread, 10, freq="B"), "IORB": flat(3.90, 10, freq="B")})
    assert D.sofr_iorb(v, C).colour == want


def test_sofr_iorb_uses_a_median_and_the_older_reserves_rate(tmp_path):
    sofr = daily([3.90, 3.90, 3.90, 3.90, 4.20], freq="B")     # one spike day does not move a 5-day median
    assert D.sofr_iorb(view(tmp_path, {"SOFR": sofr, "IORB": flat(3.90, 5, freq="B")}), C).colour == G
    v = view(tmp_path / "b", {"SOFR": flat(1.60, 10, end="2020-03-02", freq="B"), "IOER": flat(1.60, 10, end="2020-03-02", freq="B")},
             now="2020-03-03")
    assert D.sofr_iorb(v, C).colour == G


@pytest.mark.parametrize("move,want", [(-0.15, G), (-0.14, A), (0.24, A), (0.25, R)])
def test_yield_change_bands(tmp_path, move, want):
    s = daily([4.50] * 25 + [4.50 + move], freq="B")
    v = view(tmp_path, {"DGS2": s, "DGS10": s, "T10Y2Y": flat(0.28, 5, freq="B")})
    assert D.y2_chg(v, C).colour == want and D.y10_chg(v, C).colour == want


@pytest.mark.parametrize("move,want", [(-0.20, G), (-0.19, A), (0.09, A), (0.10, R)])
def test_rate_hike_pricing_bands(tmp_path, move, want):
    v = view(tmp_path, {"DGS2": daily([4.60] * 25 + [4.60 + move], freq="B"), "DFF": flat(3.88, 26, freq="B"),
                        "DFEDTARL": flat(3.75, 5), "DFEDTARU": flat(4.0, 5)})
    r = D.hike_pricing(v, C)
    assert r.colour == want and "Fed target 3.75-4.00%" in r.text


@pytest.mark.parametrize("move,want", [(-0.30, G), (-0.29, A), (0.09, A), (0.10, R)])
def test_hikes_priced_out_needs_a_30bp_fall(tmp_path, move, want):
    v = view(tmp_path, {"DGS2": daily([4.60] * 25 + [4.60 + move], freq="B"), "DFF": flat(3.88, 26, freq="B")})
    assert D.hikes_out(v, C).colour == want


@pytest.mark.parametrize("mom,want", [(0.2, G), (0.3, A), (0.4, R), (-0.1, G)])
def test_cpi_bands(tmp_path, mom, want):
    s = pd.Series({pd.Timestamp("2026-09-01"): 300.0, pd.Timestamp("2026-10-01"): 300.0 * (1 + mom / 100)})
    assert D.cpi_mom(view(tmp_path, {"CPIAUCSL": s}), C).colour == want


def test_cpi_with_a_missing_month_gives_no_reading(tmp_path):
    s = pd.Series({pd.Timestamp("2026-08-01"): 300.0, pd.Timestamp("2026-10-01"): 301.0})
    assert D.cpi_mom(view(tmp_path, {"CPIAUCSL": s}), C).colour is None


@pytest.mark.parametrize("x,want", [(2.11, G), (2.4, G), (2.5, A), (2.7, A), (2.71, R)])
def test_breakeven_bands(tmp_path, x, want):
    assert D.breakeven(view(tmp_path, {"T5YIE": flat(x, 5)}), C).colour == want


@pytest.mark.parametrize("growth,want", [(1.06, G), (1.03, A), (0.98, R)])
def test_liquidity_proxy_year_on_year(tmp_path, growth, want):
    n = 420
    data = {"WALCL": ramp(6.0e6, 6.0e6 * growth, n), "ECBASSETSW": ramp(6.0e6, 6.0e6 * growth, n),
            "JPNASSETS": ramp(6.0e6, 6.0e6 * growth, n), "M2SL": ramp(22000, 22000 * growth, n),
            "ECB_USD": flat(1.10, n), "ECB_JPY": flat(165.0, n)}
    assert D.liquidity(view(tmp_path, data), C).colour == want


def test_liquidity_proxy_converts_everything_to_dollars(tmp_path):
    data = {"WALCL": flat(6.0e6, 400), "ECBASSETSW": flat(5.0e6, 400), "JPNASSETS": flat(6.0e6, 400), "M2SL": flat(20000, 400),
            "ECB_USD": flat(1.10, 400), "ECB_JPY": flat(165.0, 400)}
    total, then, _ = D.liquidity_totals(view(tmp_path, data))
    # Fed 6.0tn + ECB 5.0tn euros x 1.10 + BoJ 600tn yen / 150 yen per dollar + M2 20tn  (in millions of dollars)
    assert round(total) == round(6.0e6 + 5.5e6 + 4.0e6 + 20.0e6)


def dollar_view(tmp_path, tail, lead=103.5):
    return view(tmp_path, ecb_for_dxy([lead] * 30 + list(tail)))


def test_dollar_red_above_and_rising_amber_above_and_falling(tmp_path):
    assert D.dollar(view(tmp_path / "a", ecb_for_dxy([103.0 + 0.03 * i for i in range(40)])), C).colour == R
    assert D.dollar(view(tmp_path / "b", ecb_for_dxy([104.5 - 0.03 * i for i in range(40)])), C).colour == A


def test_dollar_needs_two_fixings_at_least_0_3_beyond_the_level(tmp_path):
    assert D.dollar(dollar_view(tmp_path / "a", [102.2]), C).colour != G           # one fixing is not enough
    assert D.dollar(dollar_view(tmp_path / "b", [102.3, 102.3, 102.3]), C).colour != G  # 0.2 below: inside the margin
    assert D.dollar(dollar_view(tmp_path / "c", [102.2, 102.6, 102.2]), C).colour != G  # not in a row
    r = D.dollar(dollar_view(tmp_path / "d", [102.2, 102.1]), C)
    assert r.colour == G and r.extra["confirmed"] is False
    assert D.dollar_reversal(dollar_view(tmp_path / "e", [102.2, 102.1]), C).colour == G


def test_dollar_stays_green_until_two_fixings_back_above(tmp_path):
    assert D.dollar(dollar_view(tmp_path / "a", [102.0, 102.0, 102.7]), C).colour == G   # inside the margin
    assert D.dollar(dollar_view(tmp_path / "b", [102.0, 102.0, 102.9]), C).colour == G   # one fixing only
    assert D.dollar(dollar_view(tmp_path / "c", [102.0, 102.0, 102.9, 102.9]), C).colour != G


def test_dollar_confirmed_below_100(tmp_path):
    r = D.dollar_reversal(dollar_view(tmp_path, [101.0, 99.6, 99.5]), C)
    assert r.colour == G and r.extra["confirmed"] is True


def test_dollar_shows_the_published_close_as_a_check_only(tmp_path):
    data = ecb_for_dxy([103.0 + 0.03 * i for i in range(40)])
    data["DXY_PUB"] = flat(90.0, 5)                       # an absurd published value must not change the colour
    r = D.dollar(view(tmp_path, data), C)
    assert r.colour == R and "published close 90.00" in r.text


def sp_series(month_closes, last_days=None):
    """Daily S&P with one value per month (every business day equal), plus optional days in a new month."""
    idx, vals = [], []
    months = pd.period_range(end="2026-10", periods=len(month_closes), freq="M")
    for m, x in zip(months, month_closes):
        days = pd.bdate_range(m.start_time, m.end_time)
        idx += list(days)
        vals += [x] * len(days)
    for i, x in enumerate(last_days or []):
        idx.append(pd.bdate_range("2026-11-02", periods=len(last_days))[i])
        vals.append(x)
    return pd.Series(vals, index=idx, dtype=float)


def test_sp500_green_when_above_average_and_near_high(tmp_path):
    assert D.sp500(view(tmp_path, {"SP500": sp_series([7000] * 14, [7050, 7060])}), C).colour == G


def test_sp500_red_only_on_a_finished_month_end_close_below_the_average(tmp_path):
    r = D.sp500(view(tmp_path / "a", {"SP500": sp_series([7000] * 13 + [6800], [6850])}), C)
    assert r.colour == R and r.extra["month_end_break"] is True
    # the same low close, but its month has no later data yet: the month is not finished, so amber, not red
    r = D.sp500(view(tmp_path / "b", {"SP500": sp_series([7000] * 14)[:-1].set_axis(sp_series([7000] * 14).index[:-1])
                                      .pipe(lambda s: pd.concat([s, pd.Series([6800.0], index=[pd.Timestamp("2026-10-30")])]))}), C)
    assert r.colour == A and r.extra["month_end_break"] is False


def test_sp500_amber_mid_month_below_average(tmp_path):
    assert D.sp500(view(tmp_path, {"SP500": sp_series([7000] * 14, [6900, 6890])}), C).colour == A


@pytest.mark.parametrize("drop,want", [(0.05, G), (0.10, A), (0.20, R)])
def test_sp500_fall_from_one_year_high(tmp_path, drop, want):
    closes = [5000] * 6 + [6000] * 7 + [7000]              # 10-month average stays far below the price
    r = D.sp500(view(tmp_path, {"SP500": sp_series(closes, [7000 * (1 - drop)])}), C)
    assert r.colour == want


@pytest.mark.parametrize("rate,want", [(-0.002, G), (0.01, A), (0.03, R)])
def test_funding_bands(tmp_path, rate, want):
    data = {k: flat(rate, 40) for k in ("FUND_BINANCE", "FUND_BYBIT", "FUND_OKX")}
    r = D.funding(view(tmp_path, data), C)
    assert r.colour == want and round(r.value, 2) == round(rate * 3 * 365, 2)


def test_funding_counts_negative_days(tmp_path):
    s = daily([0.01] * 33 + [-0.01] * 7)
    assert D.funding(view(tmp_path, {"FUND_BINANCE": s}), C).extra["days_negative"] == 7


@pytest.mark.parametrize("last,want", [(0.5, G), (1.5, A), (3.0, R)])
def test_alt_open_interest_percentile(tmp_path, last, want):
    alt = daily([1.0 + (i % 100) / 100 for i in range(399)] + [last])   # ratio ranges 1.0 to 1.99
    assert D.alt_oi(view(tmp_path, {"OI_ALT": alt, "OI_BTC": flat(1.0, 400)}), C).colour == want


def test_alt_open_interest_needs_a_year_of_history(tmp_path):
    assert D.alt_oi(view(tmp_path, {"OI_ALT": flat(1.5, 100), "OI_BTC": flat(1.0, 100)}), C).colour is None


@pytest.mark.parametrize("chg,want", [(0.01, G), (0.0, A), (-0.02, A), (-0.03, A), (-0.04, R)])
def test_stablecoin_supply_bands(tmp_path, chg, want):
    s = daily([280e9] * 40 + [280e9 * (1 + chg)])
    assert D.stable_30d(view(tmp_path, {"STABLE_USD": s}), C).colour == want


# ------------------------------------------------------------------ C. Credit-event risk
@pytest.mark.parametrize("dial,sid,moves", [
    (D.hy_spread, "BAMLH0A0HYM2", [(0.74, G), (0.75, A), (1.50, A), (1.51, R)]),
    (D.bbb_spread, "BAMLC0A4CBBB", [(0.24, G), (0.25, A), (0.50, A), (0.51, R)])])
def test_spread_change_bands(tmp_path, dial, sid, moves):
    for i, (move, want) in enumerate(moves):
        v = view(tmp_path / str(i), {sid: daily([3.0] * 70 + [3.0 + move], freq="B")})
        assert dial(v, C).colour == want


@pytest.mark.parametrize("move,want", [(1.49, G), (1.50, A), (3.0, A), (3.1, R)])
def test_ccc_minus_bb_gap_bands(tmp_path, move, want):
    v = view(tmp_path, {"BAMLH0A3HYC": daily([12.0] * 70 + [12.0 + move], freq="B"), "BAMLH0A1HYBB": flat(2.0, 71, freq="B")})
    assert D.ccc_bb(v, C).colour == want


def test_spread_dials_need_three_months_of_history(tmp_path):
    assert D.hy_spread(view(tmp_path, {"BAMLH0A0HYM2": flat(3.0, 30, freq="B")}), C).colour is None


@pytest.mark.parametrize("x,want", [(-0.48, G), (-0.25, G), (-0.1, A), (0.0, A), (0.1, R)])
def test_nfci_bands(tmp_path, x, want):
    assert D.nfci(view(tmp_path, {"NFCI": flat(x, 5)}), C).colour == want


@pytest.mark.parametrize("x,want", [(-0.87, G), (0.0, G), (0.5, A), (1.0, A), (1.1, R)])
def test_stlfsi_bands(tmp_path, x, want):
    assert D.stlfsi(view(tmp_path, {"STLFSI4": flat(x, 5)}), C).colour == want


@pytest.mark.parametrize("basket,want", [(0.95, G), (0.85, A), (0.70, R)])
def test_ai_basket_against_sp500(tmp_path, basket, want):
    data = {"SP500": flat(7000, 80, freq="B")}
    for m in C["ai_basket"]["members"]:
        data[m] = daily([100.0] * 79 + [100.0 * basket], freq="B")
    assert D.ai_basket(view(tmp_path, data), C).colour == want


def test_ai_basket_skips_a_member_without_enough_history(tmp_path):
    data = {"SP500": flat(7000, 80, freq="B"), "CRWV": flat(100, 10, freq="B")}
    for m in ["ORCL", "NBIS", "APLD", "IREN"]:
        data[m] = flat(50, 80, freq="B")
    r = D.ai_basket(view(tmp_path, data), C)
    assert r.colour == G and "CRWV" not in r.extra["members"]


@pytest.mark.parametrize("fall,want", [(0.05, G), (0.06, A), (0.11, A), (0.12, R)])
def test_bizd_fall_from_three_month_high(tmp_path, fall, want):
    v = view(tmp_path, {"BIZD": daily([14.0] * 70 + [14.0 * (1 - fall)], freq="B")})
    assert D.bizd(v, C).colour == want


def test_bizd_ignores_highs_older_than_three_months(tmp_path):
    v = view(tmp_path, {"BIZD": daily([20.0] * 100 + [14.0] * 70, freq="B")})
    assert D.bizd(v, C).colour == G


@pytest.mark.parametrize("fall,want", [(0.10, G), (0.15, A), (0.24, A), (0.25, R)])
def test_kre_fall_from_one_year_high(tmp_path, fall, want):
    v = view(tmp_path, {"KRE": daily([80.0] * 260 + [80.0 * (1 - fall)], freq="B")})
    assert D.kre(v, C).colour == want


@pytest.mark.parametrize("levels,want", [
    ([4000] * 5, G), ([9000] * 5, G), ([11000] * 5, A), ([3000] * 4 + [8500], A),
    ([26000] * 5, R), ([3000] * 4 + [13500], R)])
def test_discount_window_level_and_jump(tmp_path, levels, want):
    v = view(tmp_path, {"WLCFLPCL": daily(levels, freq="W-WED")})
    assert D.discount_window(v, C).colour == want


def test_standing_repo_uses_a_median_so_one_quarter_end_spike_is_ignored(tmp_path):
    assert D.srf(view(tmp_path / "a", {"RPONTSYD": daily([0, 0, 0, 0, 50.0])}), C).colour == G
    assert D.srf(view(tmp_path / "b", {"RPONTSYD": flat(5.0, 5)}), C).colour == A
    assert D.srf(view(tmp_path / "c", {"RPONTSYD": flat(12.0, 5)}), C).colour == R


# ------------------------------------------------------------------ D. Has the turn started?
@pytest.mark.parametrize("move,want", [(-0.25, G), (-0.24, A), (0.24, A), (0.25, R)])
def test_front_end_easing(tmp_path, move, want):
    assert D.front_end(view(tmp_path, {"DGS2": daily([4.6] * 25 + [4.6 + move], freq="B")}), C).colour == want


@pytest.mark.parametrize("dial,sid,unit", [(D.fed_bills, "WSHOBL", 20000), (D.fed_reserves, "WRESBAL", 150000)])
def test_fed_buying_units_are_millions(tmp_path, dial, sid, unit):
    for i, (mult, want) in enumerate([(1.0, G), (0.9, A), (-0.9, A), (-1.0, R)]):
        v = view(tmp_path / str(i), {sid: daily([500000.0] * 4 + [500000.0 + unit * mult], freq="W-WED")})
        assert dial(v, C).colour == want


def test_stablecoin_turn(tmp_path):
    def s(mid, last):
        return daily([280e9] * 35 + [mid] * 30 + [last])
    assert D.stable_turn(view(tmp_path / "a", {"STABLE_USD": s(270e9, 272e9)}), C).colour == G   # positive
    assert D.stable_turn(view(tmp_path / "b", {"STABLE_USD": s(270e9, 268e9)}), C).colour == A   # negative but improving
    assert D.stable_turn(view(tmp_path / "c", {"STABLE_USD": s(278e9, 262e9)}), C).colour == R   # negative and worsening


def test_weekly_reclaim_green_for_12_weeks_then_amber(tmp_path):
    base = [80000, 69000, 72000, 74000]
    assert D.weekly_reclaim(view(tmp_path / "a", {"BTCUSD": weekly_btc(base[:3])}), C).colour == R
    assert D.weekly_reclaim(view(tmp_path / "b", {"BTCUSD": weekly_btc(base)}), C).colour == G
    assert D.weekly_reclaim(view(tmp_path / "c", {"BTCUSD": weekly_btc(base + [75000] * 11)}), C).colour == G
    assert D.weekly_reclaim(view(tmp_path / "d", {"BTCUSD": weekly_btc(base + [75000] * 12)}), C).colour == A
    assert D.weekly_reclaim(view(tmp_path / "e", {"BTCUSD": weekly_btc([80000, 81000])}), C).colour == A


def buyback_series(prior_weekly, recent_weekly):
    idx = pd.date_range(end="2026-11-24", periods=16, freq="7D")
    return pd.Series([prior_weekly * 1e9] * 12 + [recent_weekly * 1e9] * 4, index=idx)


@pytest.mark.parametrize("recent,want", [(4.5, G), (4.4, A), (3.0, A), (2.0, R)])
def test_buybacks_step_up_uses_liquidity_support_only(tmp_path, recent, want):
    v = view(tmp_path, {"BUYBACK_LS": buyback_series(3.0, recent), "BUYBACK_CM": buyback_series(0.0, 40.0)})
    r = D.buybacks(v, C)
    assert r.colour == want                                 # huge cash-management buybacks change nothing
    assert round(r.extra["cash_management_usd"] / 1e9) == 160 and r.obs == pd.Timestamp("2026-11-25")


def test_every_dial_copes_with_no_data(tmp_path):
    v = view(tmp_path, {})
    for d in D.DIALS:
        r = d["fn"](v, C, None)
        assert r.colour is None and r.value is None, d["id"]


def test_dial_ids_are_unique_and_grouped():
    ids = [d["id"] for d in D.DIALS]
    assert len(ids) == len(set(ids)) == 40
    assert {d["group"] for d in D.DIALS} == {"A", "B", "C", "D"}


# ------------------------------------------------------------------ review fixes (point 8)
def test_margin_debt_with_a_missing_month_is_not_silently_stretched(tmp_path):
    full = margin_series([1255.0, 1250.0, 1230.0])
    gappy = full.drop(full.index[-3])                       # one month missing inside the 3-month window
    r = D.margin_debt(view(tmp_path, {"MARGIN_DEBT": gappy}), C)
    assert r.obs == full.index[-1] and r.colour == R        # computed from true month ends, 3 calendar months apart
    assert len(D.margin_growth(view(tmp_path / "b", {"MARGIN_DEBT": gappy}))) < len(D.margin_growth(view(tmp_path / "c", {"MARGIN_DEBT": full})))


def test_sp500_shows_an_unofficial_same_day_figure_without_changing_the_colour(tmp_path):
    sp = sp_series([7000] * 14, [7050, 7060])                # FRED's last close: 3 Nov
    spy = pd.Series([700.0, 706.0, 692.0], index=pd.to_datetime(["2026-11-02", "2026-11-03", "2026-11-04"]))   # one day ahead, sharply lower
    plain = D.sp500(view(tmp_path / "a", {"SP500": sp}, now="2026-11-05 09:00"), C)
    both = D.sp500(view(tmp_path / "b", {"SP500": sp, "SPY": spy}, now="2026-11-05 09:00"), C)
    assert both.colour == plain.colour == G and both.value == 7060
    assert round(both.extra["same_day_estimate"]) == round(7060 * 692 / 706)
    assert "unofficial, same day (04 Nov)" in both.text and plain.extra["same_day_estimate"] is None


def test_sp500_same_day_figure_is_hidden_when_it_is_not_newer(tmp_path):
    sp = sp_series([7000] * 14, [7050, 7060])
    spy = pd.Series([700.0, 706.0], index=pd.to_datetime(["2026-11-02", "2026-11-03"]))
    assert D.sp500(view(tmp_path, {"SP500": sp, "SPY": spy}, now="2026-11-05 09:00"), C).extra["same_day_estimate"] is None


def test_liquidity_date_is_the_older_of_the_two_weekly_balance_sheets(tmp_path):
    n = 420
    data = {"WALCL": ramp(6.0e6, 6.3e6, n), "ECBASSETSW": ramp(6.0e6, 6.3e6, n, end="2026-11-01"),
            "JPNASSETS": flat(6.0e6, n), "M2SL": flat(22000, n), "ECB_USD": flat(1.10, n), "ECB_JPY": flat(165.0, n)}
    assert D.liquidity(view(tmp_path, data), C).obs == pd.Timestamp("2026-11-01")


def test_liquidity_compares_each_part_with_its_own_year_earlier_figure(tmp_path):
    """Every part grows exactly 6% a year, but M2 and the Bank of Japan are published one to two months late.
    The reading must still be 6%, not shortened by the late parts."""
    def grow(n_days, end):
        idx = pd.date_range(end=end, periods=n_days, freq="D")
        return pd.Series([100.0 * 1.06 ** (i / 365) for i in range(n_days)], index=idx)
    data = {"WALCL": grow(800, "2026-11-24") * 6e4, "ECBASSETSW": grow(800, "2026-11-20") * 6e4,
            "JPNASSETS": grow(800, "2026-10-01") * 6e4, "M2SL": grow(800, "2026-09-01") * 220,
            "ECB_USD": flat(1.10, 900), "ECB_JPY": flat(165.0, 900)}
    r = D.liquidity(view(tmp_path, data), C)
    assert abs(r.value - 6.0) < 0.05 and r.colour == G


def test_buybacks_keep_judging_when_operations_stop(tmp_path):
    """A step-up, then no operations at all: the dial must fall back, not stay green as 'stale'."""
    idx = pd.date_range(end="2026-10-20", periods=16, freq="7D")
    s = pd.Series([3e9] * 12 + [6e9] * 4, index=idx)
    assert D.buybacks(view(tmp_path / "a", {"BUYBACK_LS": s}, now="2026-10-21 09:00"), C).colour == G
    later = D.buybacks(view(tmp_path / "b", {"BUYBACK_LS": s}, now="2026-11-25 09:00"), C)
    assert later.colour == R and later.obs == pd.Timestamp("2026-11-25") and "last operation 20 Oct 2026" in later.text
    long_after = D.buybacks(view(tmp_path / "c", {"BUYBACK_LS": s}, now="2027-06-01 09:00"), C)
    assert long_after.colour == A                                # nothing in either period: neutral, never a kept green


def test_buybacks_are_never_frozen_by_the_stale_rule(tmp_path):
    from hub.signals.engine import evaluate
    idx = pd.date_range(end="2026-10-20", periods=16, freq="7D")
    s = pd.Series([3e9] * 12 + [6e9] * 4, index=idx)
    state = None
    for i, now in enumerate(["2026-10-21 09:00", "2026-11-25 09:00", "2026-11-25 09:15", "2026-11-25 09:30"]):
        o = evaluate(view(tmp_path / str(i), {"BUYBACK_LS": s}, now=now), C, state)
        state = o["state"]
    b = o["readings"]["buybacks"]
    assert b["colour"] == R and b["too_old"] is False and b["fresh_green"] is False


def test_alt_open_interest_is_labelled_a_proxy_until_matched(tmp_path):
    data = {"OI_ALT": daily([1.0 + (i % 100) / 100 for i in range(400)]), "OI_BTC": flat(1.0, 400)}
    assert "proxy, not matched to Coutts" in D.alt_oi(view(tmp_path, data), cfg(alt_oi={"matched_to_coutts": False})).text
    assert "proxy" not in D.alt_oi(view(tmp_path / "b", data), cfg(alt_oi={"matched_to_coutts": True})).text


def test_percentiles_read_as_proper_ordinals():
    from hub.signals.core import ordinal
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 51, 62, 86, 98, 100)] == \
        ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "51st", "62nd", "86th", "98th", "100th"]
