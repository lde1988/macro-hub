"""The machine-readable feed. Layout is documented in FEED.md and versioned:
fields are only ever added within a major version, never renamed or removed."""
import pandas as pd

from hub.signals.core import A, G, R, WORD
from hub.signals.engine import FAMILY_NAMES

FEED_VERSION = "1.0"
HKT = "Asia/Hong_Kong"
DISCLAIMER = "Framework reading, not financial advice"
EXIT_NOTE = "Built to spot buy zones. Its exit signals have a weak record."


def hkt(ts):
    t = pd.Timestamp(ts)
    t = t.tz_localize("UTC") if t.tzinfo is None else t
    return t.tz_convert(HKT)


def days_since(since, now):
    if not since:
        return None
    return max(0, (pd.Timestamp(now).tz_localize(None) - pd.Timestamp(since).tz_localize(None)).days)


def section(sid, name, kind, dials):
    """One line per family: a colour and a plain sentence."""
    live = [d for d in dials if d["colour"]]
    red = [d["title"] for d in live if d["colour"] == R]
    amber = [d for d in live if d["colour"] == A]
    green = [d for d in live if d["colour"] == G]
    stale = [d["title"] for d in dials if d["stale"]]
    if not live:
        colour, sentence = None, "No data yet."
    elif red:
        colour, sentence = R, f"{len(red)} of {len(live)} against: " + ", ".join(red) + "."
    elif amber:
        colour = A
        sentence = f"None against; {len(green)} of {len(live)} supportive." if green else "All neutral."
    else:
        colour, sentence = G, (f"All {len(live)} supportive." if len(live) > 1 else "Supportive.")
    missing = len(dials) - len(live)
    if missing:
        sentence += f" {missing} with no data yet."
    if stale:
        sentence += " Stale: " + ", ".join(stale) + "."
    return {"id": sid, "name": name, "kind": kind, "colour": colour, "word": WORD[colour], "sentence": sentence,
            "dials": [d["id"] for d in dials]}


def build(out, cfg, registry, now, status, since, record=None):
    """out: engine.evaluate() result. since: {"reading":, "regime":, "trend_exit":} ISO dates."""
    now = pd.Timestamp(now)
    today = now.tz_localize(None).normalize() if now.tzinfo is None else now.tz_convert("UTC").tz_localize(None).normalize()
    fam_of = {i: f for f, ids in cfg["families"].items() for i in ids}
    dials = []
    for r in out["readings"].values():
        obs = r["obs_date"]
        age = (today - pd.Timestamp(obs)).days if obs else None
        too_old = bool(r.get("too_old"))
        stale = bool(r["colour"]) and (r["no_data"] or too_old)
        dials.append({
            "id": r["id"], "title": r["title"], "group": r["group"],
            "family": fam_of.get(r["id"], "valuation" if r["group"] == "A" else "turn"),
            "value": r["value"], "text": r["text"], "colour": r["colour"], "word": WORD[r["colour"]],
            "since": r["since"], "data_date": obs, "data_age_days": age, "stale": stale,
            "stale_reason": (f"newest data is {age} days old" + ("; last colour kept" if r["colour"] else "; no colour given") if too_old else
                             "source not answering; last colour kept" if r["no_data"] and r["colour"] else ""),
            "fresh_turn_signal": bool(r.get("fresh_green")) if r["group"] == "D" else None,
            "moves": r["moves"], "gauge": r["gauge"], "extra": r["extra"]})
    by = lambda pred: [d for d in dials if pred(d)]
    sections = [section("valuation", "Is it cheap?", "valuation", by(lambda d: d["group"] == "A"))]
    for f in cfg["families"]:
        sections.append(section(f, FAMILY_NAMES[f][0].upper() + FAMILY_NAMES[f][1:], "stress", by(lambda d, f=f: d["family"] == f)))
    turn = out["turn"]
    ts = section("turn", "Has the turn started?", "turn", by(lambda d: d["group"] == "D"))
    n = len(turn["fresh_signals"])
    ts["sentence"] = ("Turn confirmed: " + ", ".join(turn["fresh_signals"]) + "." if turn["confirmed"]
                      else f"Not confirmed. {n} early signal{'s' if n != 1 else ''}" + (": " + ", ".join(turn["fresh_signals"]) if n else "") + ".")
    ts["colour"] = G if turn["confirmed"] else (A if n else ts["colour"] if ts["colour"] == R else A)
    ts["word"] = WORD[ts["colour"]]
    sections.append(ts)

    rd = dict(out["reading"])
    rd.pop("turn", None)
    alts = rd.pop("alts")
    price = out["readings"].get("btc_price", {})
    credits = {k: v.get("credit", k) for k, v in registry["sources"].items()}
    return {
        "version": FEED_VERSION,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_at_hkt": hkt(now).strftime("%Y-%m-%d %H:%M HKT"),
        "disclaimer": DISCLAIMER, "exit_note": EXIT_NOTE,
        "reading": {**rd, "since": since.get("reading"), "days_in_force": days_since(since.get("reading"), now)},
        "altcoins": alts,
        "trend_exit": {**out["trend_exit"], "since": since.get("trend_exit"), "days_in_force": days_since(since.get("trend_exit"), now)},
        "regime": {**out["regime"], "since": since.get("regime"), "days_in_force": days_since(since.get("regime"), now)},
        "turn": {k: turn[k] for k in ("confirmed", "dollar_reversal", "families", "fresh_signals")},
        "bitcoin": {"price": price.get("value"), **{k: price.get("extra", {}).get(k) for k in
                    ("realised_price", "ratio_to_realised", "value_zone", "dynamic_value_zone", "lth_cost", "sth_cost")}},
        "sections": sections,
        "dials": dials,
        "sources": {k: {"credit": credits.get(k, k), "last_ok": v.get("last_ok", ""), "fails_in_a_row": v.get("fails", 0),
                        "check_only": bool(registry["sources"].get(k, {}).get("check_only")),
                        "problem": v.get("last_error", "") or "; ".join(f"{a}: {b}" for a, b in (v.get("series_errors") or {}).items())}
                    for k, v in sorted(status.items())},
        "watching": {"enabled": False, "note": "Weekly sweep (Phase 2) is switched off."},
    }
