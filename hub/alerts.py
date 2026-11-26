"""Decides what to push. Pure functions: they compare this run with the last one
and return a list of pushes; sending and retrying is done by hub/run.py.

Push only on change. Plain English: what changed, the number, one line on what it means.
"""
import pandas as pd

from hub.outputs import plain
from hub.outputs.feed import hkt

WORD = {"green": "Supports", "amber": "Neutral", "red": "Against", None: "No data"}


def summary(feed):
    """The few facts alerts compare from run to run."""
    pl = feed["plain"]
    return {"reading": feed["reading"]["headline"].split(" (CAUTION")[0], "label": feed["reading"]["label"],
            "regime": feed["regime"]["name"], "trend_exit": feed["trend_exit"]["state"],
            "light": pl["headline"]["word"], "backdrop": pl["backdrop"]["text"],
            "dials": {d["id"]: d["colour"] for d in feed["dials"]},
            "stale": sorted(d["id"] for d in feed["dials"] if d["stale"])}


def plan(prev, feed, cfg, down_before=None):
    """Pushes for the changes between the previous summary and this feed, in plain words.
    prev None = first run: record a silent baseline, push nothing."""
    a, cur, out, pl = cfg["alerts"], summary(feed), [], feed["plain"]
    if not prev:
        return out
    if cur["reading"] != prev.get("reading"):
        froth = "FROTH WARNING" in (cur["label"], prev.get("label"))
        was = prev.get("light")
        title = pl["headline"]["word"] + (f" (was {was})" if was and was != pl["headline"]["word"] else " (reason changed)")
        body = pl["headline"]["sentence"]
        if pl["weak_record"]:
            body += "\n" + pl["weak_record"]
        body += f'\nWhat would change it: {pl["what_would_change"]}\n{feed["disclaimer"]}.'
        out.append({"title": title, "message": body, "tags": ["vertical_traffic_light"],
                    "priority": cfg["froth_warning"]["push_priority"] if froth else a["reading_priority"]})
    if cur["regime"] != prev.get("regime"):
        bd = pl["backdrop"]
        out.append({"title": "Backdrop: " + bd["text"], "priority": a["regime_priority"], "tags": ["compass"],
                    "message": (f'Before: {prev["backdrop"]}.' if prev.get("backdrop") else "The backdrop has changed.")
                    + (f'\n{bd["early"]}' if bd["early"] else "") + "\nThe backdrop is context; it does not set the buy / hold reading."})
    if cur["trend_exit"] != prev.get("trend_exit") and "NO DATA" not in (cur["trend_exit"], prev.get("trend_exit")):
        tr, raw = pl["trend"], feed["trend_exit"]
        out.append({"title": "Bitcoin's weekly trend has turned " + ("down" if raw["state"] == "RISK-OFF" else "up"),
                    "priority": a["trend_exit_priority"], "tags": ["triangular_flag_on_post"],
                    "message": f'Bitcoin closed the week at ${raw["weekly_close"]:,.0f}. {tr["detail"]} This line is separate from the buy / hold reading.'})
    changes, top = [], 0
    for d in feed["dials"]:
        old, new = prev.get("dials", {}).get(d["id"]), d["colour"]
        if old is None or new is None or old == new or d.get("context_only"):
            continue                                    # context-only dials never push
        pr = (a["dial_red_priority"] if new == "red" else
              a["improvement_priority"] if (new == "green" or old == "red") else a["dial_change_priority"])
        top = max(top, pr)
        changes.append(plain.dial_change(d, old))
    if changes:
        title = changes[0].split(". ")[0] if len(changes) == 1 else f"{len(changes)} measures changed"
        body = changes[0].split(". ", 1)[1] if len(changes) == 1 else "\n\n".join(changes)
        out.append({"title": title, "message": body[:3000], "priority": top, "tags": ["control_knobs"]})
    newly_stale = [d for d in feed["dials"] if d["stale"] and d["id"] not in prev.get("stale", [])]
    if newly_stale:
        out.append({"title": f"Old data: {newly_stale[0]['title']}" if len(newly_stale) == 1 else f"Old data on {len(newly_stale)} measures",
                    "priority": a["stale_priority"], "tags": ["hourglass"],
                    "message": "\n".join(f"{d['title']}: {d['stale_reason']}." for d in newly_stale)
                    + "\nThese are greyed out and cannot change colour until fresh data arrives."})
    return out


def source_pushes(status, registry, cfg, already_down):
    """'Source down' once a source has failed 4 runs in a row; 'source back' when it recovers.
    Returns (pushes, new list of sources reported down)."""
    out, down = [], set(already_down or [])
    n = cfg["general"]["source_down_runs"]
    for name, st in status.items():
        meta = registry["sources"].get(name, {})
        if meta.get("check_only"):
            continue
        part = sorted(k for k, c in (st.get("series_fails") or {}).items() if c >= n)
        key = name + ":" + ",".join(part)
        for old in [d for d in down if d.startswith(name + ":") and d != key]:
            down.discard(old)
        if part and st.get("fails", 0) < n and key not in down:
            down.add(key)
            out.append({"title": f"Source partly down: {meta.get('credit', name)}", "priority": cfg["alerts"]["source_down_priority"], "tags": ["warning"],
                        "message": f"{meta.get('credit', name)} has failed {n} runs in a row for: {', '.join(part)}. The dials that use them keep their last colour until the data returns."})
        if st.get("fails", 0) >= n and name not in down:
            down.add(name)
            out.append({"title": f"Source down: {meta.get('credit', name)}", "priority": cfg["alerts"]["source_down_priority"], "tags": ["warning"],
                        "message": f"{meta.get('credit', name)} has failed {st['fails']} runs in a row. Its dials keep their last colour, greyed out, until it answers again."})
        elif st.get("fails", 0) == 0 and name in down:
            down.discard(name)
            out.append({"title": f"Source back: {meta.get('credit', name)}", "priority": cfg["alerts"]["improvement_priority"], "tags": ["white_check_mark"],
                        "message": f"{meta.get('credit', name)} is answering again."})
    return out, sorted(down)


def digest_due(now, last_digest_date, cfg):
    """One digest a day, at the first run at or after 08:00 Hong Kong time."""
    t = hkt(now)
    return t.hour >= cfg["alerts"]["digest_hour_hkt"] and str(t.date()) != (last_digest_date or "")


def digest(feed, cfg):
    pl = feed["plain"]
    bad = [v["credit"] for v in feed["sources"].values() if v["fails_in_a_row"] and not v["check_only"]]
    b = feed["bitcoin"]
    lines = [pl["headline"]["word"] + ". " + pl["headline"]["sentence"].split(". ", 1)[-1],
             "Backdrop: " + pl["backdrop"]["text"] + ".",
             pl["trend"]["text"] + ".",
             pl["tally"]["text"] + ".",
             f'Bitcoin ${b["price"]:,.0f}.' if b.get("price") else "Bitcoin price unavailable.",
             "Sources failing: " + ", ".join(bad) + "." if bad else "All sources answering."]
    if pl["backdrop"]["early"]:
        lines.insert(2, pl["backdrop"]["early"])
    if feed.get("valuations"):
        lines.append(valuation_line(feed["valuations"]))
    stale = [d["title"] for d in feed["dials"] if d["stale"]]
    if stale:
        lines.append("Old data: " + ", ".join(stale) + ".")
    return {"title": "macro-hub daily digest", "message": "\n".join(lines) + f'\n{feed["disclaimer"]}.',
            "priority": cfg["alerts"]["digest_priority"], "tags": ["sunrise"]}


def valuation_line(vals):
    """The coin valuations in one digest line (context only): the 1-year reading for each coin."""
    ok = [f'{v["sym"]} {v["short"]["z"]:+.1f}' for v in vals if (v.get("short") or {}).get("status") == "ok"]
    none = [v["sym"] for v in vals if (v.get("short") or {}).get("status") != "ok"]
    line = "Coins against their last year (SD): " + ", ".join(ok)
    if none:
        line += "; too little history: " + ", ".join(none)
    return line + "."
