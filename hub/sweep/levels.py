"""The one exception to "context only" (owner's rule, 26 Nov 2026):

When Jamie Coutts states a new value for a level the hub already tracks (realised price, long-term or
short-term holder cost, his regime-filter level), update it, log old and new value with date and link, and
push a notice. If it differs from the old value by more than 15%, or the post is ambiguous, ask instead.

Overrides live on the data branch in sweep/levels.json. The hub applies ONLY the keys listed in
ALLOWED; anything else in that file is ignored, so the sweep can never change any other setting.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path

from hub.sweep.analyse import parse_level

ALLOWED = ("realised_price", "lth_cost", "sth_cost", "btc_break", "btc_reclaim")


def load(data):
    p = Path(data) / "sweep" / "levels.json"
    d = json.loads(p.read_text()) if p.exists() else {}
    return {"values": {k: float(v) for k, v in (d.get("values") or {}).items() if k in ALLOWED},
            "log": d.get("log") or [], "pending": d.get("pending") or []}


def save(data, d):
    p = Path(data) / "sweep" / "levels.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=1))


def with_overrides(cfg, data):
    """The thresholds config with Coutts' level overrides applied (only the allowed keys). Used by the hub run."""
    vals = load(data)["values"]
    if not vals:
        return cfg
    out = dict(cfg)
    out["levels"] = {**cfg["levels"], **{k: v for k, v in vals.items() if k in ALLOWED}}
    return out


def target_key(r, rules):
    """Which config level a record may update, or (None, reason)."""
    m = rules["keys"].get(r.get("metric_key"))
    if m is None:
        return None, "not a level the hub tracks"
    if isinstance(m, dict):
        role = r.get("level_role")
        if role not in m:
            return None, "the post does not say whether this is the break or the reclaim line"
        return m[role], None
    return m, None


def decide(records, sweep_cfg, thresholds, current, now):
    """Return (applied, questions) for this run's Coutts records. Does not write anything."""
    rules = sweep_cfg["level_updates"]
    limit = sweep_cfg["analysis"]["levels_max_change"]
    found = {}
    asks = []
    for r in records:
        if r.get("person_id") != rules["person"] or r.get("metric_key") not in rules["keys"]:
            continue
        key, why = target_key(r, rules)
        new = parse_level(r.get("level"), "usd")
        problems = []
        if key is None:
            problems.append(why)
        if new is None:
            problems.append("no clear dollar value")
        if not r.get("speaker_certain"):
            problems.append("not certain Coutts said it")
        if not r.get("level_in_quote"):
            problems.append("the number was read off a chart, not stated in words")
        if problems:
            asks.append(_question(r, key, None, new, "; ".join(problems), now))
            continue
        found.setdefault(key, []).append((new, r))
    applied = []
    vals = dict(current)
    for key, items in found.items():
        values = {round(v, -1) for v, _ in items}
        new, r = items[-1]
        old = float(vals.get(key, thresholds["levels"][key]))
        if len(values) > 1:
            asks.append(_question(r, key, old, new, "he gave more than one value this week", now))
            continue
        if abs(new - old) / old <= 0.005:
            continue                                         # the same level again: nothing to do
        change = (new - old) / old
        brk = new if key == "btc_break" else float(vals.get("btc_break", thresholds["levels"]["btc_break"]))
        rec = new if key == "btc_reclaim" else float(vals.get("btc_reclaim", thresholds["levels"]["btc_reclaim"]))
        if abs(change) > limit:
            asks.append(_question(r, key, old, new, f"a change of {change:+.0%}, more than {limit:.0%}", now))
        elif brk >= rec:
            asks.append(_question(r, key, old, new, "the break line would be at or above the reclaim line", now))
        else:
            vals[key] = new
            applied.append({"time_utc": now.strftime("%Y-%m-%dT%H:%MZ"), "key": key, "old": old, "new": new,
                            "change_pct": round(change * 100, 1), "post_date": r.get("date"), "url": r.get("url"),
                            "quote": r["quote"][:300], "how": "applied automatically (within 15%)"})
    return applied, asks


def _question(r, key, old, new, reason, now):
    qid = hashlib.sha1(f'{r.get("url")}|{key}|{new}'.encode()).hexdigest()[:8]
    return {"id": qid, "asked_utc": now.strftime("%Y-%m-%dT%H:%MZ"), "key": key, "old": old, "new": new,
            "reason": reason, "post_date": r.get("date"), "url": r.get("url"), "quote": r["quote"][:300],
            "level_text": r.get("level")}


def answer(data, thresholds, qid, accept, now, value=None, key=None):
    """The owner's answer to a pending question. Returns a short plain-English result."""
    d = load(data)
    q = next((x for x in d["pending"] if x["id"] == qid), None)
    if q is None:
        return False, f"No open question with id {qid}."
    d["pending"] = [x for x in d["pending"] if x["id"] != qid]
    if not accept:
        d["log"].append({**{k: q.get(k) for k in ("key", "old", "new", "post_date", "url", "quote")},
                         "time_utc": now.strftime("%Y-%m-%dT%H:%MZ"), "how": "declined by the owner"})
        save(data, d)
        return True, f"Declined: {q.get('key') or 'level'} stays as it was."
    key = key or q.get("key")
    new = float(value) if value not in (None, "") else q.get("new")
    if key not in ALLOWED or new is None:
        d["pending"].append(q)
        save(data, d)
        return False, "This question cannot be accepted as it stands (unclear line or value). Answer with a value and the line, or decline it."
    old = float(d["values"].get(key, thresholds["levels"][key]))
    d["values"][key] = new
    d["log"].append({"time_utc": now.strftime("%Y-%m-%dT%H:%MZ"), "key": key, "old": old, "new": new,
                     "change_pct": round((new - old) / old * 100, 1), "post_date": q.get("post_date"), "url": q.get("url"),
                     "quote": q.get("quote"), "how": "approved by the owner"})
    save(data, d)
    return True, f"Applied: {key} {old:,.0f} -> {new:,.0f}."
