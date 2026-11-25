"""Plain-English wording: built from live readings, sensible for every combination of colours,
and free of the old jargon. Presentation only: no rule or threshold is involved."""
import itertools
import re

import pytest

from hub.outputs import dashboard, plain
from hub.signals.dials import DIALS
from hub.util import load_config
from tests.test_outputs import small_feed

C = load_config()
GROUPS = {"valuation": [d["id"] for d in DIALS if d["group"] == "A"], "turn": [d["id"] for d in DIALS if d["group"] == "D"], **C["families"]}
JARGON = ["regime", "Regime", "BREAK", "FRAGILE", "STRESS BUILDING", "TURN", "CALM", "RISK-OFF", "RISK-ON", "realised", "SOPR", "percentile"]


def group_colour(colours):
    live = [c for c in colours if c]
    return None if not live else "red" if "red" in live else "amber" if "amber" in live else "green"


def test_every_dial_has_a_phrase_for_every_colour():
    for d in DIALS:
        assert set(plain.PHRASE[d["id"]]) == {"green", "amber", "red"}, d["id"]
        for text in plain.PHRASE[d["id"]].values():
            assert text and text[0].islower() or text.startswith(("Bitcoin", "US ", "Treasury")), text
            assert not text.endswith(".") and not any(j in text for j in JARGON), text
    assert set(plain.MEANING) == set(GROUPS)


@pytest.mark.parametrize("gid", sorted(GROUPS))
def test_every_combination_of_colours_gives_a_sensible_group_sentence(gid):
    ids = GROUPS[gid]
    seen = set()
    for combo in itertools.product(["green", "amber", "red", None], repeat=len(ids)):
        colour = group_colour(combo)
        dials = {i: {"id": i, "colour": c, "stale": False, "title": i} for i, c in zip(ids, combo)}
        text = plain.group_sentence({"id": gid, "colour": colour, "dials": ids}, dials)
        seen.add(text)
        assert text and text[0].isupper() and text.endswith("."), (combo, text)
        assert "None" not in text and "{" not in text and "  " not in text and ", ." not in text and " ," not in text and ".." not in text, (combo, text)
        assert not any(j in text for j in JARGON), (combo, text)
        assert 11 < len(text) < 420, (combo, text)
        if colour is None:
            assert text == "No data yet."
            continue
        sentences = [x for x in re.split(r"(?<=[.])\s+", text) if x]
        assert len(sentences) == 2, (combo, text)                              # what it is doing now; what that means
        assert sentences[1] == plain.MEANING[gid][colour]
        named = [plain.PHRASE[i][c] for i, c in zip(ids, combo) if c == colour]
        assert any(n.lower() in text.lower() for n in named), (combo, text)    # says something true about a dial of that colour
        other = {"red": "green", "green": "red"}.get(colour)
        if colour == "green":                                                   # an all-green group never mentions a red or amber state
            wrong = [plain.PHRASE[i][o] for i in ids for o in ("red", "amber") if plain.PHRASE[i][o] != plain.PHRASE[i]["green"]]
            assert not any(w in text for w in wrong), (combo, text)
    assert len(seen) > 3


def test_group_sentences_come_from_the_live_readings(tmp_path):
    fd, _ = small_feed(tmp_path)
    before = fd["plain"]["groups"]["rates_dollar"]
    for d in fd["dials"]:
        if d["id"] == "dollar":
            d["colour"] = "red"
    for s in fd["sections"]:
        if s["id"] == "rates_dollar":
            s["colour"] = "red"
    after = plain.build(fd)["groups"]["rates_dollar"]
    assert after != before and after.startswith("The dollar is strong and still rising") and "works against buying" in after


def test_a_stale_dial_is_not_described_as_if_it_were_current():
    dials = {"kre": {"id": "kre", "colour": "red", "stale": True, "title": "kre"}}
    text = plain.group_sentence({"id": "banks", "colour": "red", "dials": ["kre"]}, dials)
    assert "falling hard" not in text and text.endswith("works against buying.")


KINDS = ["buy_staged", "buy_confirmed", "froth", "hold_froth", "hold_cheap_waiting", "hold_cheap_stress", "hold_near_no_turn",
         "hold_near_stress", "hold_neutral"]


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("dollar", ["green", "amber", "red", None])
@pytest.mark.parametrize("caution", [True, False])
def test_headline_is_one_word_one_colour_and_a_plain_sentence(tmp_path, kind, dollar, caution):
    fd, _ = small_feed(tmp_path)
    label = "BUY" if kind.startswith("buy") else "FROTH WARNING" if kind == "froth" else "HOLD"
    fd["reading"].update(label=label, kind=kind, caution=caution, blocked_by=["credit spreads"] if "stress" in kind else [], record="right on 3 of 8 past occasions")
    for d in fd["dials"]:
        if d["id"] == "dollar":
            d["colour"] = dollar
    h = plain.headline(fd)
    assert (h["word"], h["colour"]) == {"BUY": ("BUY", "green"), "HOLD": ("HOLD", "amber"), "FROTH WARNING": ("SELL", "red")}[label]
    assert h["symbol"] in "▲●▼" and h["sentence"].endswith(".") and not any(j in h["sentence"] for j in JARGON)
    assert h["sentence"].startswith({"BUY": "Buy", "HOLD": "Hold. ", "FROTH WARNING": "Sell signal"}[label])
    if kind == "buy_staged":
        assert "in stages" in h["sentence"]                                     # says which kind of buy
    if kind == "hold_near_no_turn" and dollar == "red":
        assert h["sentence"].startswith("Hold. Bitcoin is fairly cheap, but the dollar is still rising, so the turn has not started.")
    assert plain.what_would_change(fd) and not any(j in plain.what_would_change(fd) for j in JARGON)


@pytest.mark.parametrize("name,want", [
    ("CALM", "Calm"), ("FRAGILE", "Leverage warning: borrowing to buy shares has rolled over"), ("TURN", "Liquidity is turning up")])
def test_backdrop_names_in_plain_words(tmp_path, name, want):
    fd, _ = small_feed(tmp_path)
    fd["regime"]["name"] = name
    assert plain.backdrop(fd)["text"] == want


def test_backdrop_says_where_stress_is_and_which_trend_broke(tmp_path):
    fd, _ = small_feed(tmp_path)
    assert plain.backdrop(fd)["text"] == "Downtrend: Bitcoin is below its weekly trend line"
    next(d for d in fd["dials"] if d["id"] == "sp500")["extra"] = {"month_end_break": True}
    assert plain.backdrop(fd)["text"] == "Downtrend: Bitcoin is below its weekly trend line and the S&P 500 closed last month below its 10-month average"
    fd["regime"]["name"] = "STRESS BUILDING"
    for s in fd["sections"]:
        s["colour"] = "red" if s["id"] in ("credit", "ai_private") else "green"
    assert plain.backdrop(fd)["text"] == "Stress is building in credit spreads and AI and private credit"


def test_trend_line_wording(tmp_path):
    fd, _ = small_feed(tmp_path)
    fd["trend_exit"]["since"] = "2026-11-16"
    assert plain.trend(fd)["text"] == "Trend: down since 16 Nov"
    fd["trend_exit"].update(state="RISK-ON", since="2026-08-24T00:20Z")
    assert plain.trend(fd)["text"] == "Trend: up since 24 Aug"
    fd["trend_exit"]["since"] = None
    assert plain.trend(fd)["text"] == "Trend: up for more than five months"


def test_tally_counts_every_group_with_a_colour(tmp_path):
    fd, _ = small_feed(tmp_path)
    t = plain.tally(fd)
    assert t["green"] + t["amber"] + t["red"] == t["groups"] == sum(1 for s in fd["sections"] if s["colour"])
    assert t["text"] == f"Of the {t['groups']} groups: {t['green']} support buying, {t['amber']} neutral, {t['red']} against"


def test_the_page_has_no_regime_wording_but_the_feed_keeps_it(tmp_path):
    fd, _ = small_feed(tmp_path)
    page = dashboard.render(fd)
    visible = re.sub(r"<(script|style)[\s\S]*?</\1>", "", page)
    for word in ("regime", "Regime", "BREAK", "FRAGILE", "STRESS BUILDING", "CALM", "RISK-OFF", "RISK-ON"):
        assert word not in visible, word
    assert not re.search(r"\bTURN\b", visible)
    assert fd["regime"]["name"] == "BREAK" and fd["trend_exit"]["state"] == "RISK-OFF" and fd["reading"]["label"] == "HOLD"   # unchanged for bots
    assert ">HOLD<" in page and "Backdrop" in page and "Of the " in page


def test_group_heading_shows_plain_sentence_then_count_then_dials(tmp_path):
    fd, _ = small_feed(tmp_path)
    page = dashboard.render(fd)
    block = page[page.index("Is it cheap?"):page.index("Rates and dollar")]
    import html
    assert block.index(html.escape(fd["plain"]["groups"]["valuation"])[:30]) < block.index('class="count"') < block.index('class="grid"')
    assert "1 of " in block and "against" in block
