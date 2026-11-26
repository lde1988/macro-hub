"""Turning stored records into the "What they're watching" panel. Pure calculation: no network.

Context only. Nothing here changes a dial, band, rule or the reading; the calibration table and the scorecard
READ the hub's history, never write it. (The one exception, Coutts' levels, is in hub/sweep/levels.py.)
"""
import datetime as dt
import math
import re
from collections import Counter, defaultdict

import pandas as pd

TOPICS = ("liquidity", "crypto", "ai_spending", "credit_risk")
TOPIC_LABEL = {"liquidity": "Liquidity", "crypto": "Crypto", "ai_spending": "AI spending", "credit_risk": "Credit risk"}
CALIBRATE = ("coutts", "pal")          # owner: calibration table for Jamie Coutts and Raoul Pal
STALE_WEEKS = 8                        # a stance older than this is left out of the tally


# ------------------------------------------------------------------ numbers as people write them
def parse_level(text, units):
    """'$53,100' / '53.1k' / '$287bn' / '330bp' / '3.63%' / '1.66x' -> a number in the hub's units, or None."""
    if text is None:
        return None
    t = str(text).lower().replace(",", "").replace("−", "-").strip()
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*(k|thousand|m|mn|million|b|bn|billion|t|tn|trillion|bp|bps|basis points?|%|x)?", t)
    if not m:
        return None
    v, suf = float(m.group(1)), (m.group(2) or "")
    mult = {"k": 1e3, "thousand": 1e3, "m": 1e6, "mn": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9, "billion": 1e9,
            "t": 1e12, "tn": 1e12, "trillion": 1e12}
    if units == "usd":
        return v * mult.get(suf, 1)
    if units == "bp_as_pct":
        if suf.startswith("b"):
            return v / 100
        if suf == "%":
            return v
        return v / 100 if v >= 20 else v          # "330" is basis points; "3.3" is a percentage
    if units in ("pct", "yoy_pct"):
        if suf.startswith("b"):
            return v / 100
        return v
    if units == "x":
        return v if suf in ("x", "") else None
    if units == "index":
        return v if suf in ("", "x") else None
    return None


# ------------------------------------------------------------------ the hub's own reading of a measure
def hub_value(spec, store, thresholds, overrides, on_date):
    """(value, date of that value) as the hub knew it on `on_date`, or (None, None)."""
    day = pd.Timestamp(on_date)

    def at(sid):
        s = store.series(sid)
        s = s[s.index <= day]
        return (float(s.iloc[-1]), s.index[-1]) if len(s) else (None, None)
    if not spec:
        return None, None
    if "series" in spec:
        v, d = at(spec["series"])
        return (v * spec.get("scale", 1.0), d) if v is not None else (None, None)
    if "ratio" in spec:
        a, da = at(spec["ratio"][0])
        b, db = at(spec["ratio"][1])
        return (a / b, min(da, db)) if a is not None and b else (None, None)
    if "yoy" in spec:
        s = store.series(spec["yoy"])
        s = s[s.index <= day]
        if len(s) < 13:
            return None, None
        last, d = float(s.iloc[-1]), s.index[-1]
        prev = s[s.index <= d - pd.DateOffset(years=1)]
        return ((last / float(prev.iloc[-1]) - 1) * 100, d) if len(prev) else (None, None)
    if "level" in spec:
        k = spec["level"]
        return float(overrides.get(k, thresholds["levels"][k])), day
    if "valuation" in spec:
        from hub.signals import valuation
        c = next(c for c in thresholds["valuations"]["coins"] if c["sym"] == spec["valuation"])
        s = store.series(c["history"])
        s = s[s.index <= day]
        r = valuation.reading(s, thresholds, today=day)
        return (r.get("z"), s.index[-1]) if r.get("status") == "ok" else (None, None)
    return None, None


# ------------------------------------------------------------------ stances
def _week_stance(recs, topic):
    """One person's stance on a topic for one week: the majority; positive against negative is 'mixed'."""
    c = Counter(r["stances"][topic]["stance"] for r in recs if r["stances"].get(topic))
    if not c:
        return None
    if c["positive"] and c["negative"] and c["positive"] == c["negative"]:
        return "mixed"
    return c.most_common(1)[0][0]


def stances(records, week_end):
    """Latest stance per person and topic, plus changes of mind this week.
    Only records whose speaker is certain count; uncertain ones are shown but never flip a stance."""
    by = defaultdict(lambda: defaultdict(list))          # person -> week -> records
    for r in records:
        if r.get("speaker_certain"):
            by[r["person_id"]][r["week_end"]].append(r)
    latest, changes = {}, []
    for pid, weeks in by.items():
        order = sorted(weeks)
        for t in TOPICS:
            hist = [(w, _week_stance(weeks[w], t)) for w in order]
            hist = [(w, s) for w, s in hist if s]
            if not hist:
                continue
            w, s = hist[-1]
            ev = max((r for r in weeks[w] if r["stances"].get(t)), key=lambda r: r.get("date") or "")
            latest.setdefault(pid, {})[t] = {"stance": s, "week_end": w, "date": ev.get("date"),
                                             "quote": ev["stances"][t]["quote"], "url": ev.get("url"), "at": ev.get("at")}
            if w == week_end and len(hist) >= 2:
                pw, ps = hist[-2]
                if ps != s and "mixed" not in (ps, s):
                    old = max((r for r in weeks[pw] if r["stances"].get(t)), key=lambda r: r.get("date") or "")
                    changes.append({"person_id": pid, "topic": t, "from": ps, "to": s, "from_date": old.get("date"),
                                    "to_date": ev.get("date"), "from_quote": old["stances"][t]["quote"],
                                    "to_quote": ev["stances"][t]["quote"], "url": ev.get("url"), "old_url": old.get("url")})
    return latest, changes


def tally(latest, week_end):
    """Across the group: how many are positive / neutral / negative / mixed on each topic (recent stances only)."""
    cut = (pd.Timestamp(week_end) - pd.Timedelta(weeks=STALE_WEEKS)).strftime("%Y-%m-%d")
    out = {}
    for t in TOPICS:
        c = Counter(v[t]["stance"] for v in latest.values() if t in v and v[t]["week_end"] >= cut)
        out[t] = {k: c.get(k, 0) for k in ("positive", "neutral", "negative", "mixed")}
    return out


def cited(records, week_end, metrics, min_people):
    """Measures cited by at least `min_people` different people this week."""
    who = defaultdict(set)
    ex = {}
    for r in records:
        if r["week_end"] == week_end and r.get("metric_key") not in (None, "other"):
            who[r["metric_key"]].add(r["person_id"])
            ex.setdefault(r["metric_key"], r)
    out = [{"key": k, "label": metrics.get(k, {}).get("label", k), "people": sorted(p), "count": len(p),
            "tracked_by_hub": "hub" in metrics.get(k, {}), "example": {"quote": ex[k]["quote"], "url": ex[k].get("url"),
                                                                        "person_id": ex[k]["person_id"]}}
           for k, p in who.items() if len(p) >= min_people]
    return sorted(out, key=lambda x: (-x["count"], x["label"]))


def proposals(records, week_end, metrics, min_people, min_weeks):
    """Dial proposals: a measure the hub does not track, cited by >= min_people in >= min_weeks of the last 4."""
    end = pd.Timestamp(week_end)
    weeks = defaultdict(lambda: defaultdict(set))
    for r in records:
        k = r.get("metric_key")
        if k in (None, "other") or "hub" in metrics.get(k, {"hub": 1}):
            continue
        if end - pd.Timestamp(r["week_end"]) < pd.Timedelta(weeks=4):
            weeks[k][r["week_end"]].add(r["person_id"])
    out = []
    for k, ws in weeks.items():
        busy = [w for w, p in ws.items() if len(p) >= min_people]
        if len(busy) >= min_weeks:
            out.append({"key": k, "label": metrics[k]["label"], "weeks": sorted(busy),
                        "people": sorted(set().union(*ws.values())), "status": "proposal only: nothing is built"})
    return out


def calibration(records, metrics, store, thresholds, overrides, limit=40):
    """Coutts' and Pal's stated numbers against the hub's own reading of the same measure, on the same day."""
    rows = []
    for r in records:
        if r["person_id"] not in CALIBRATE or not r.get("level"):
            continue
        m = metrics.get(r.get("metric_key"), {})
        spec, units = m.get("hub"), m.get("units")
        if not spec or not units:
            continue
        theirs = parse_level(r["level"], units)
        hub, hub_date = hub_value(spec, store, thresholds, overrides, r.get("date") or r["week_end"])
        gap = None
        if theirs is not None and hub not in (None, 0):
            gap = (theirs - hub) / abs(hub) * 100
        rows.append({"person_id": r["person_id"], "date": r.get("date"), "metric": m["label"], "their_text": r["level"],
                     "theirs": theirs, "hub": hub, "hub_date": hub_date.strftime("%Y-%m-%d") if hub_date is not None else None,
                     "gap_pct": round(gap, 1) if gap is not None and math.isfinite(gap) else None,
                     "note": None if theirs is not None else "units not comparable", "url": r.get("url"),
                     "from_chart_only": not r.get("level_in_quote", True)})
    rows.sort(key=lambda x: x["date"] or "", reverse=True)
    return rows[:limit]


def scorecard(records, metrics, store, thresholds, overrides, today):
    """Every dated, checkable call. Marked right or wrong only when the deadline has passed, the measure is one the
    hub reads, and the threshold is plainly a level of that measure; otherwise it waits or needs the owner's judgement."""
    out, seen = [], set()
    today = pd.Timestamp(today).normalize()
    for r in records:
        c = r.get("call")
        if not c or (r["person_id"], c["text"]) in seen:
            continue
        seen.add((r["person_id"], c["text"]))
        row = {"person_id": r["person_id"], "made": c.get("made"), "by": c["by"], "text": c["text"], "url": r.get("url"),
               "status": "open", "outcome": None, "speaker_certain": r.get("speaker_certain")}
        due = pd.Timestamp(c["by"]) < today
        spec = metrics.get(c.get("measure_key") or "", {}).get("hub")
        if due:
            if not spec or c.get("direction") is None or c.get("threshold") is None:
                row["status"] = "needs your judgement"
            else:
                then, _ = hub_value(spec, store, thresholds, overrides, c.get("made"))
                v, d = hub_value(spec, store, thresholds, overrides, c["by"])
                t = c["threshold"]
                if v is None or then in (None, 0) or not (0.2 <= t / abs(then) <= 5):
                    row["status"] = "needs your judgement"   # e.g. "up 15%" is a change, not a level of the index
                else:
                    hit = v > t if c["direction"] == "above" else v < t
                    row.update(status="right" if hit else "wrong",
                               outcome=f"{v:,.2f} on {d.strftime('%Y-%m-%d')} against {c['direction']} {t:,.2f}")
        out.append(row)
    return sorted(out, key=lambda x: (x["status"] == "open", x["by"]))
