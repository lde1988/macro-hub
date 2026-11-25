"""No-flapping rule, families, turn confirmation, regime and the buy/hold/sell rules. Made-up data."""
import pandas as pd
import pytest

from hub.signals.core import A, G, R
from hub.signals.dials import DIALS
from hub.signals.engine import evaluate, families, reading, regime, step, trading_days_between, turn_status
from tests.helpers import cfg, flat, view

C = cfg()
T0 = pd.Timestamp("2026-11-25 09:00")


# ------------------------------------------------------------------ no flapping
def test_first_colour_is_a_silent_baseline():
    st, changed = step({}, G, T0, 2)
    assert st["colour"] == G and changed is None and st["baseline"] is True


def test_colour_changes_only_after_two_runs_in_a_row():
    st, _ = step({}, G, T0, 2)
    st, changed = step(st, R, T0, 2)
    assert st["colour"] == G and changed is None               # first run beyond the edge: no change yet
    st, changed = step(st, R, T0 + pd.Timedelta(minutes=15), 2)
    assert st["colour"] == R and changed == G                  # second run in a row: changes


def test_a_single_blip_is_ignored():
    st, _ = step({}, G, T0, 2)
    st, _ = step(st, R, T0, 2)
    st, _ = step(st, G, T0, 2)                                 # back inside: the count resets
    st, changed = step(st, R, T0, 2)
    assert st["colour"] == G and changed is None


def test_two_different_colours_do_not_add_up():
    st, _ = step({}, G, T0, 2)
    st, _ = step(st, R, T0, 2)
    st, changed = step(st, A, T0, 2)
    assert st["colour"] == G and st["pending"] == A and st["count"] == 1


def test_no_data_keeps_the_last_colour():
    st, _ = step({}, R, T0, 2)
    st, changed = step(st, None, T0, 2)
    assert st["colour"] == R and changed is None


def test_self_confirming_dials_change_at_once():
    st, _ = step({}, G, T0, 2, mode="none")
    st, changed = step(st, R, T0, 2, mode="none")
    assert st["colour"] == R and changed == G


def test_trading_days_skip_weekends():
    assert trading_days_between("2026-11-20", "2026-11-23") == 1   # Friday to Monday
    assert trading_days_between("2026-11-18", "2026-11-25") == 5


# ------------------------------------------------------------------ made-up dial readings
def R_(**colours):
    """Readings for every dial: amber unless stated. extra facts can be passed as id__key=value."""
    out = {}
    for d in DIALS:
        out[d["id"]] = {"id": d["id"], "group": d["group"], "title": d["title"], "colour": A, "fresh_red": False,
                        "extra": {"ratio_to_realised": 1.5} if d["id"] == "btc_price" else {}}
    for k, v in colours.items():
        if "__" in k:
            i, key = k.split("__")
            out[i]["extra"][key] = v
        elif v == "fresh":
            out[k].update(colour=R, fresh_red=True)
        elif v == "old green":                      # green for longer than 13 weeks
            out[k].update(colour=G, fresh_green=False)
        else:
            out[k]["colour"] = v
    for r in out.values():
        r.setdefault("fresh_green", r["colour"] == G)
    return out


CHEAP = dict(btc_price=G, btc_price__ratio_to_realised=1.08)


# ------------------------------------------------------------------ families
def test_every_stress_dial_belongs_to_exactly_one_family():
    bc = {d["id"] for d in DIALS if d["group"] in "BC"}
    listed = [i for ids in C["families"].values() for i in ids]
    assert sorted(listed) == sorted(bc)
    assert set(C["buy_blocking_families"]) == {"money_market", "credit", "banks"}


def test_a_family_counts_once_however_many_of_its_dials_are_red():
    f = families(R_(hy_spread=R, ccc_bb=R, bbb_spread=R), C)
    assert [k for k, v in f.items() if v["red"]] == ["credit"]


# ------------------------------------------------------------------ turn confirmation
def test_turn_confirmed_by_the_dollar_alone():
    assert turn_status(R_(dollar_reversal=G), C)["confirmed"] is True


@pytest.mark.parametrize("greens,want", [
    (["front_end", "stable_turn"], True),       # rates + crypto liquidity
    (["hikes_out", "buybacks"], True),          # rates + Fed and Treasury
    (["fed_bills", "stable_turn"], True),
    (["front_end", "hikes_out"], False),        # two dials, one family
    (["fed_bills", "buybacks"], False),
    (["fed_reserves", "stable_turn"], False),   # bank reserves alone never confirm
    (["fed_reserves", "front_end"], False),
    (["weekly_reclaim", "front_end"], False),   # the price reclaim is not a turn family
    ([], False)])
def test_turn_needs_two_families(greens, want):
    assert turn_status(R_(**{g: G for g in greens}), C)["confirmed"] is want


def test_a_green_older_than_13_weeks_is_a_state_not_a_turn():
    assert turn_status(R_(dollar_reversal="old green"), C)["confirmed"] is False
    assert turn_status(R_(front_end=G, stable_turn="old green"), C)["confirmed"] is False
    assert turn_status(R_(front_end=G, stable_turn=G), C)["confirmed"] is True
    assert regime(R_(dollar_reversal="old green", stable_turn="old green"), C)["name"] == "CALM"
    assert reading(R_(btc_price__ratio_to_realised=1.2, dollar_reversal="old green"), C)["label"] == "HOLD"


def test_the_original_rule_still_counts_any_green_turn_dial():
    assert reading(R_(**CHEAP, dollar_reversal="old green"), C, "old")["label"] == "BUY"


# ------------------------------------------------------------------ regime, first match wins
def test_regime_order():
    assert regime(R_(), C)["name"] == "CALM"
    assert regime(R_(margin_debt__fired_latched=True), C)["name"] == "FRAGILE"
    assert regime(R_(margin_debt__fired_latched=True, hy_spread=R), C)["name"] == "STRESS BUILDING"
    assert regime(R_(hy_spread=R, btc_weekly__break_in_force=True), C)["name"] == "BREAK"
    assert regime(R_(sp500__month_end_break=True), C)["name"] == "BREAK"
    t = regime(R_(hy_spread=R, btc_weekly__break_in_force=True, dollar_reversal=G), C)
    assert t["name"] == "TURN" and "confirmed" in t["detail"] and t["early_line"] == ""
    assert regime(R_(front_end=G, stable_turn=G), C)["name"] == "TURN"            # two families


def test_unconfirmed_turn_signals_show_under_the_underlying_regime():
    t = regime(R_(hy_spread=R, btc_weekly__break_in_force=True, front_end=G, hikes_out=G), C)
    assert t["name"] == "BREAK"                                                    # one family only: not confirmed
    assert t["early_line"] == "2 early turn signals: Front-end easing (2-year yield), Rate hikes being priced out"
    one = regime(R_(fed_reserves=G), C)
    assert one["name"] == "CALM" and one["early_line"].startswith("1 early turn signal: ")
    assert regime(R_(), C)["early_line"] == ""


def test_group_a_red_does_not_count_as_stress():
    assert regime(R_(lth_sopr=R), C)["name"] == "CALM"


# ------------------------------------------------------------------ buy / hold / sell, new rule
def test_buy_staged_needs_cheap_price_and_a_capitulation_sign_but_no_turn():
    r = reading(R_(**CHEAP, lth_sopr=G), C)
    assert (r["label"], r["level"]) == ("BUY", "STAGED")
    r = reading(R_(**CHEAP, net_loss=G), C)
    assert (r["label"], r["level"]) == ("BUY", "STAGED")
    r = reading(R_(**CHEAP), C)
    assert r["label"] == "HOLD" and "no capitulation sign" in r["headline"]


def test_buy_confirmed_needs_price_within_1_3x_and_a_confirmed_turn():
    r = reading(R_(btc_price__ratio_to_realised=1.25, dollar_reversal=G), C)
    assert (r["label"], r["level"]) == ("BUY", "CONFIRMED")
    assert reading(R_(btc_price__ratio_to_realised=1.31, dollar_reversal=G), C)["label"] == "HOLD"
    r = reading(R_(btc_price__ratio_to_realised=1.25, front_end=G), C)      # one family only
    assert r["label"] == "HOLD" and "turn is not confirmed" in r["headline"]


def test_confirmed_beats_staged_when_both_apply():
    assert reading(R_(**CHEAP, lth_sopr=G, dollar_reversal=G), C)["level"] == "CONFIRMED"


@pytest.mark.parametrize("dial,blocks", [
    ("sofr_iorb", True), ("discount_window", True), ("srf", True),      # money-market funding
    ("hy_spread", True), ("ccc_bb", True), ("nfci", True),              # credit spreads
    ("kre", True),                                                       # banks
    ("ai_basket", False), ("bizd", False), ("funding", False), ("stable_30d", False),
    ("sp500", False), ("dollar", False), ("y2_chg", False)])
def test_only_fresh_red_in_funding_credit_or_banks_blocks_a_buy(dial, blocks):
    staged = reading(R_(**CHEAP, lth_sopr=G, **{dial: "fresh"}), C)
    confirmed = reading(R_(btc_price__ratio_to_realised=1.2, dollar_reversal=G, **{dial: "fresh"}), C)
    assert (staged["label"] == "HOLD") is blocks and (confirmed["label"] == "HOLD") is blocks
    if blocks:
        assert "fresh stress" in staged["headline"]


def test_a_red_that_is_no_longer_fresh_does_not_block():
    assert reading(R_(**CHEAP, lth_sopr=G, hy_spread=R), C)["label"] == "BUY"


@pytest.mark.parametrize("froth", ["funding", "alt_oi", "btc_price"])
@pytest.mark.parametrize("liq", [dict(margin_debt__fired_latched=True), dict(dollar=R), dict(hy_spread=R, kre=R)])
def test_sell_needs_froth_and_deteriorating_liquidity(froth, liq):
    assert reading(R_(**{froth: R}, **liq), C)["label"] == "SELL"


def test_sell_counts_families_not_dials():
    r = reading(R_(funding=R, hy_spread=R, ccc_bb=R, bbb_spread=R), C)     # three dials, but only two families with funding
    assert r["label"] == "SELL"                                             # crypto leverage + credit = two families
    r = reading(R_(btc_price=R, hy_spread=R, ccc_bb=R, bbb_spread=R), C)   # price froth; credit is one family
    assert r["label"] == "HOLD" and "frothy" in r["headline"]


def test_froth_alone_or_bad_liquidity_alone_is_hold():
    assert reading(R_(funding=R), C)["label"] == "HOLD"
    assert reading(R_(dollar=R, margin_debt__fired_latched=True), C)["label"] == "HOLD"


def test_hold_always_says_which_kind():
    for r in (reading(R_(), C), reading(R_(**CHEAP), C), reading(R_(funding=R), C),
              reading(R_(btc_price__ratio_to_realised=1.2), C)):
        assert r["headline"].startswith("Hold: ") and len(r["headline"]) > 12 and 1 <= len(r["reasons"]) <= 4 and r["change"]


def test_caution_flag_when_weekly_close_is_broken_and_price_not_in_value_zone():
    r = reading(R_(btc_weekly__break_in_force=True), C)
    assert r["caution"] is True and "CAUTION" in r["headline"]
    assert reading(R_(**CHEAP, btc_weekly__break_in_force=True), C)["caution"] is False


def test_altcoins_have_a_stricter_rule():
    buy = dict(**CHEAP, lth_sopr=G)
    assert reading(R_(**buy, alt_oi=G), C)["alts"]["label"] == "BUY"
    assert reading(R_(**buy), C)["alts"]["label"] == "HOLD"                # open interest not below its 50th percentile
    assert reading(R_(alt_oi=G), C)["alts"]["label"] == "HOLD"             # Bitcoin reading is not Buy
    assert reading(R_(funding=R, dollar=R), C)["alts"]["label"] == "SELL"


# ------------------------------------------------------------------ old rule, kept for the side-by-side replay
def test_old_buy_rule_needs_any_turn_signal_and_no_newly_red_stress_dial():
    assert reading(R_(**CHEAP, fed_reserves=G), C, "old")["label"] == "BUY"
    assert reading(R_(**CHEAP), C, "old")["label"] == "HOLD"
    assert reading(R_(**CHEAP, fed_reserves=G, ai_basket="fresh"), C, "old")["label"] == "HOLD"   # any B or C dial blocks
    assert reading(R_(**CHEAP, lth_sopr=G), C, "old")["label"] == "HOLD"                           # no turn signal


# ------------------------------------------------------------------ whole run on a small made-up store
def test_evaluate_end_to_end_and_fresh_red_window(tmp_path):
    data = {"BTCUSD": flat(80000, 30), "BV_REALIZED_PRICE": flat(53000, 30), "T5YIE": flat(2.1, 5)}
    v1 = view(tmp_path, data, now="2026-11-25 09:00")
    out1 = evaluate(v1, C)
    assert out1["readings"]["breakeven"]["colour"] == G and out1["readings"]["hy_spread"]["colour"] is None
    assert out1["reading"]["label"] == "HOLD" and out1["regime"]["name"] == "CALM"
    # breakeven jumps: needs two runs, then counts as newly red for 5 trading days
    data["T5YIE"] = flat(3.0, 5)
    out2 = evaluate(view(tmp_path / "b", data, now="2026-11-25 09:15"), C, out1["state"])
    assert out2["readings"]["breakeven"]["colour"] == G
    out3 = evaluate(view(tmp_path / "c", data, now="2026-11-25 09:30"), C, out2["state"])
    b = out3["readings"]["breakeven"]
    assert b["colour"] == R and b["changed_from"] == G and b["fresh_red"] is True
    assert out3["regime"]["name"] == "STRESS BUILDING"
    out4 = evaluate(view(tmp_path / "d", data, now="2026-12-03 09:30"), C, out3["state"])
    assert out4["readings"]["breakeven"]["colour"] == R and out4["readings"]["breakeven"]["fresh_red"] is False


def test_green_is_fresh_for_13_weeks_after_switching_on(tmp_path):
    def run(level, now, state=None):
        return evaluate(view(tmp_path / now.replace(" ", "_").replace(":", ""), {"WSHOBL": weeks(level)}, now=now), C, state)

    def weeks(last):
        return pd.Series([500000.0] * 4 + [last], index=pd.date_range(end="2026-06-03", periods=5, freq="W-WED"))
    o = run(500000.0, "2026-06-04 09:00")                       # baseline: amber
    o = run(530000.0, "2026-06-04 09:15", o["state"])
    o = run(530000.0, "2026-06-04 09:30", o["state"])           # second run: turns green
    assert o["readings"]["fed_bills"]["colour"] == G and o["readings"]["fed_bills"]["fresh_green"] is True
    assert o["regime"]["name"] == "CALM" and o["regime"]["early_line"].startswith("1 early turn signal")
    later = run(530000.0, "2026-09-02 09:30", o["state"])       # 90 days on: still fresh
    assert later["readings"]["fed_bills"]["fresh_green"] is True
    stale = run(530000.0, "2026-09-04 09:30", o["state"])       # 92 days on: still green, no longer a turn
    assert stale["readings"]["fed_bills"]["colour"] == G and stale["readings"]["fed_bills"]["fresh_green"] is False
    assert stale["regime"]["name"] == "CALM" and stale["regime"]["early_line"] == ""


def test_a_baseline_green_is_not_treated_as_fresh(tmp_path):
    s = pd.Series([500000.0] * 4 + [530000.0], index=pd.date_range(end="2026-06-03", periods=5, freq="W-WED"))
    o = evaluate(view(tmp_path, {"WSHOBL": s}, now="2026-06-04 09:00"), C)
    assert o["readings"]["fed_bills"]["colour"] == G and o["readings"]["fed_bills"]["fresh_green"] is False


def test_a_baseline_red_is_not_treated_as_newly_red(tmp_path):
    out = evaluate(view(tmp_path, {"T5YIE": flat(3.0, 5)}), C)
    assert out["readings"]["breakeven"]["colour"] == R and out["readings"]["breakeven"]["fresh_red"] is False


def test_one_broken_dial_does_not_stop_the_others(tmp_path, monkeypatch):
    d = next(x for x in DIALS if x["id"] == "breakeven")
    monkeypatch.setitem(d, "fn", lambda v, c, p: 1 / 0)
    out = evaluate(view(tmp_path, {"NFCI": flat(-0.5, 5)}), C)
    assert "calculation error" in out["readings"]["breakeven"]["text"] and out["readings"]["nfci"]["colour"] == G
