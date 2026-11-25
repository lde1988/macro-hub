"""Decides what to push. Pure functions: they compare this run with the last one
and return a list of pushes; sending and retrying is done by hub/run.py.

Push only on change. Plain English: what changed, the number, one line on what it means.
"""
import pandas as pd

from hub.outputs.feed import hkt

WORD = {"green": "Supports", "amber": "Neutral", "red": "Against", None: "No data"}


def summary(feed):
    """The few facts alerts compare from run to run."""
    return {"reading": feed["reading"]["headline"].split(" (CAUTION")[0], "label": feed["reading"]["label"],
            "regime": feed["regime"]["name"], "trend_exit": feed["trend_exit"]["state"],
            "dials": {d["id"]: d["colour"] for d in feed["dials"]}}


def plan(prev, feed, cfg, down_before=None):
    """Pushes for the changes between the previous summary and this feed.
    prev None = first run: record a silent baseline, push nothing."""
    a, cur, out = cfg["alerts"], summary(feed), []
    if not prev:
        return out
    rd = feed["reading"]
    if cur["reading"] != prev.get("reading"):
        froth = "FROTH WARNING" in (cur["label"], prev.get("label"))
        body = f'{prev.get("reading")} → {cur["reading"]}.\n' + "\n".join("• " + r for r in rd["reasons"][:3])
        if rd.get("record"):
            body += f'\nRecord of this warning: {rd["record"]}.'
        body += f'\nWhat would change it: {rd["change"]}\n{feed["disclaimer"]}.'
        out.append({"title": f'Reading: {cur["reading"]}', "message": body, "tags": ["chart_with_upwards_trend"],
                    "priority": cfg["froth_warning"]["push_priority"] if froth else a["reading_priority"]})
    if cur["regime"] != prev.get("regime"):
        rg = feed["regime"]
        out.append({"title": f'Regime: {prev.get("regime")} → {rg["name"]}', "priority": a["regime_priority"], "tags": ["compass"],
                    "message": rg["detail"] + (f'\n{rg["early_line"]}' if rg.get("early_line") else "")})
    if cur["trend_exit"] != prev.get("trend_exit") and "NO DATA" not in (cur["trend_exit"], prev.get("trend_exit")):
        tr = feed["trend_exit"]
        out.append({"title": f'Trend exit: {tr["state"]}', "priority": a["trend_exit_priority"], "tags": ["triangular_flag_on_post"],
                    "message": f'Bitcoin weekly close ${tr["weekly_close"]:,.0f}: {tr["text"]}. This line is separate from the buy / hold reading.'})
    changes, top = [], 0
    for d in feed["dials"]:
        old, new = prev.get("dials", {}).get(d["id"]), d["colour"]
        if old is None or new is None or old == new:
            continue
        pr = (a["dial_red_priority"] if new == "red" else
              a["improvement_priority"] if (new == "green" or old == "red") else a["dial_change_priority"])
        top = max(top, pr)
        changes.append(f'{d["title"]}: {WORD[old]} → {WORD[new]}. {d["text"]}. {d["moves"]}')
    if changes:
        title = changes[0].split(". ")[0] if len(changes) == 1 else f"{len(changes)} dials changed"
        out.append({"title": title, "message": "\n\n".join(changes)[:3000], "priority": top, "tags": ["control_knobs"]})
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
    red = [s["name"] for s in feed["sections"] if s["colour"] == "red"]
    bad = [v["credit"] for v in feed["sources"].values() if v["fails_in_a_row"] and not v["check_only"]]
    b = feed["bitcoin"]
    lines = [feed["reading"]["headline"],
             f'Regime: {feed["regime"]["name"]}' + (f' ({feed["regime"]["early_line"]})' if feed["regime"].get("early_line") else ""),
             f'Trend exit: {feed["trend_exit"]["state"]}',
             f'Bitcoin ${b["price"]:,.0f}, {b["ratio_to_realised"]:.2f}x realised price' if b.get("price") else "Bitcoin price unavailable",
             "Against: " + (", ".join(red) if red else "no family"),
             "Sources failing: " + ", ".join(bad) if bad else "All sources answering"]
    return {"title": "macro-hub daily digest", "message": "\n".join(lines) + f'\n{feed["disclaimer"]}.',
            "priority": cfg["alerts"]["digest_priority"], "tags": ["sunrise"]}
