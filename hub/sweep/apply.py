"""The save step of the weekly sweep: add the week's records to the data branch, apply Coutts' level rule,
work out the panel, log the cost, and push notices.

    python -m hub.sweep.apply --data data --in sweepout [--no-push]

Writes ONLY inside data/sweep/. The hub reads data/sweep/watching.json (panel) and data/sweep/levels.json
(the four allowed levels); nothing else the sweep writes is read by the hub.
"""
import argparse
import csv
import datetime as dt
import json
from pathlib import Path

import yaml

from hub import notify
from hub.store import Store
from hub.sweep import analyse, levels
from hub.util import ROOT, load_config, utcnow

MONEY = "{:,.0f}"


def read_jsonl(p):
    p = Path(p)
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()] if p.exists() else []


def all_records(sweep_dir):
    recs = []
    for f in sorted((sweep_dir / "records").glob("*.jsonl")):
        recs += read_jsonl(f)
    return recs


def write_costs(sweep_dir, now, run):
    p = sweep_dir / "costs.csv"
    new = not p.exists()
    c, n = run["costs"], run["counts"]
    with open(p, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["month", "time_utc", "xai_usd", "groq_usd", "gemini_usd", "total_usd", "x_posts",
                        "audio_hours", "video_hours", "episodes", "videos", "newsletter_posts", "records"])
        w.writerow([now.strftime("%Y-%m"), now.strftime("%Y-%m-%dT%H:%MZ"), c.get("xai", 0), c.get("groq", 0),
                    c.get("gemini", 0), c["total"], n["x_posts"], round(n["audio_s"] / 3600, 2), round(n["video_s"] / 3600, 2),
                    n["episodes"], n["videos"], n["newsletter_posts"], run["records"]])


def build_panel(records, sweep_cfg, thresholds, store, lv, now, run, week_end):
    metrics = sweep_cfg["metrics"]
    a = sweep_cfg["analysis"]
    latest, changes = analyse.stances(records, week_end)
    names = {p["id"]: p["name"] for p in sweep_cfg["people"]}
    people = []
    for p in sweep_cfg["people"]:
        mine = [r for r in records if r["person_id"] == p["id"]]
        week = [r for r in mine if r["week_end"] == week_end]
        people.append({"id": p["id"], "name": p["name"], "balancing": bool(p.get("balancing")),
                       "latest": latest.get(p["id"], {}), "records_this_week": len(week),
                       "uncertain_this_week": sum(1 for r in week if not r.get("speaker_certain")),
                       "last_seen": max((r.get("date") or "" for r in mine), default=None),
                       "changed": [c["topic"] for c in changes if c["person_id"] == p["id"]]})
    for c in changes:
        c["person"] = names.get(c["person_id"], c["person_id"])
    week_recs = [r for r in records if r["week_end"] == week_end]
    return {
        "enabled": True, "version": 1, "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "week_end": week_end,
        "note": "Context only: what these people said this week. It never changes the buy / hold reading, a dial or a rule, "
                "except Coutts' stated levels under the owner's 15% rule.",
        "topics": analyse.TOPIC_LABEL,
        "people": people,
        "tally": analyse.tally(latest, week_end),
        "changes": changes,
        "cited": analyse.cited(records, week_end, metrics, a["cited_by_min_people"]),
        "calibration": analyse.calibration(records, metrics, store, thresholds, lv["values"]),
        "scorecard": analyse.scorecard(records, metrics, store, thresholds, lv["values"], now.date()),
        "proposals": analyse.proposals(records, week_end, metrics, a["proposal_min_people"], a["proposal_min_weeks"]),
        "levels": {"values": lv["values"], "log": lv["log"][-10:], "pending": lv["pending"]},
        "run": {"time_utc": now.strftime("%Y-%m-%dT%H:%MZ"), "cost_usd": run["costs"]["total"],
                "month_to_date_usd": round(run["month_before"] + run["costs"]["total"], 2),
                "budget_usd": sweep_cfg["budget"]["monthly_usd"], "counts": run["counts"],
                "records": len(week_recs), "gemini_on": run.get("gemini_on", False),
                "waiting_for_gemini": len(run.get("waiting_for_gemini") or []),
                "left_out_for_budget": len(run.get("budget_refused") or [])},
        "names": names,
    }


def pushes_for(run, sweep_cfg, applied, asks, changes, panel, state, now):
    out = []
    month = now.strftime("%Y-%m")
    b = sweep_cfg["budget"]
    mtd = run["month_before"] + run["costs"]["total"]
    if mtd >= b["monthly_usd"] * b["warn_at_share"] and state.get("warned_month") != month:
        out.append({"title": "macro-hub: sweep budget nearly used", "priority": 3, "tags": ["moneybag"],
                    "message": f"The weekly sweep has spent ${mtd:.2f} of its ${b['monthly_usd']:.0f} budget for {month}. "
                               f"At {b['stop_at_share']:.0%} it stops adding paid work until next month. "
                               "The budget is in config/sweep.yaml."})
        state["warned_month"] = month
    for x in applied:
        out.append({"title": f"macro-hub: Coutts level updated ({x['key']})", "priority": 3, "tags": ["pushpin"],
                    "message": f"{x['key']}: {MONEY.format(x['old'])} -> {MONEY.format(x['new'])} ({x['change_pct']:+.1f}%), "
                               f"from his post of {x['post_date']}: {x['url']}\n\"{x['quote'][:200]}\"\n"
                               "Within the 15% rule, so applied. Logged in the sweep panel."})
    for q in asks:
        old = MONEY.format(q["old"]) if q.get("old") else "?"
        new = MONEY.format(q["new"]) if q.get("new") else (q.get("level_text") or "?")
        out.append({"title": "macro-hub: Coutts level needs your answer", "priority": 4, "tags": ["question"],
                    "message": f"{q.get('key') or 'A level'}: {old} -> {new}. Not applied because {q['reason']}. "
                               f"Post of {q['post_date']}: {q['url']}\n\"{q['quote'][:200]}\"\n"
                               f"To answer: Actions -> 'Sweep: answer a level question' -> Run workflow, question id {q['id']}."})
    c = run["counts"]
    flips = "; ".join(f"{x['person']} on {analyse.TOPIC_LABEL[x['topic']].lower()}: {x['from']} -> {x['to']}" for x in changes[:4])
    out.append({"title": "macro-hub: weekly sweep done", "priority": 2, "tags": ["newspaper"],
                "message": f"{panel['run']['records']} records from {c['x_posts']} X posts, {c['episodes']} podcast episodes "
                           f"({c['audio_s'] / 3600:.1f} h), {c['videos']} videos and {c['newsletter_posts']} newsletter posts. "
                           f"Cost ${run['costs']['total']:.2f} (month ${mtd:.2f} of ${b['monthly_usd']:.0f})."
                           + (f" Changed their mind: {flips}." if flips else " Nobody changed their mind.")
                           + (f" {len(run.get('waiting_for_gemini') or [])} YouTube-only videos wait for the Gemini key."
                              if not run.get("gemini_on") else "")})
    return out


def main(argv=None, now=None, sender=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--in", dest="inp")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--rebuild", action="store_true",
                    help="rebuild the panel from the records already stored (free: nothing fetched, no pushes)")
    a = ap.parse_args(argv)
    now = now or utcnow()
    data = Path(a.data)
    sweep_dir = data / "sweep"
    if a.rebuild:
        return rebuild(data, now)
    inp = Path(a.inp)
    (sweep_dir / "records").mkdir(parents=True, exist_ok=True)
    sweep_cfg = yaml.safe_load(open(ROOT / "config" / "sweep.yaml"))
    thresholds = load_config()
    run = json.loads((inp / "run.json").read_text())
    new = read_jsonl(inp / "records.jsonl")
    week_end = run["window"][1][:10]
    old_ids = {r["id"] for r in all_records(sweep_dir)}
    fresh = [r for r in new if r["id"] not in old_ids]
    with open(sweep_dir / "records" / f"{week_end}.jsonl", "a") as f:
        for r in fresh:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    seen_p = sweep_dir / "seen.json"
    seen = set(json.loads(seen_p.read_text())) if seen_p.exists() else set()
    seen_p.write_text(json.dumps(sorted(seen | set(run.get("new_seen") or []))))
    write_costs(sweep_dir, now, run)

    lv = levels.load(data)
    applied, asks = levels.decide(fresh, sweep_cfg, thresholds, lv["values"], now)
    for x in applied:
        lv["values"][x["key"]] = x["new"]
        lv["log"].append(x)
    open_ids = {q["id"] for q in lv["pending"]}
    asks = [q for q in asks if q["id"] not in open_ids]
    lv["pending"] += asks
    levels.save(data, lv)

    records = all_records(sweep_dir)
    panel = build_panel(records, sweep_cfg, thresholds, Store(data), lv, now, run, week_end)
    (sweep_dir / "watching.json").write_text(json.dumps(panel, indent=1, default=str))
    (sweep_dir / "last_run.json").write_text(json.dumps({k: v for k, v in run.items() if k != "new_seen"}, indent=1, default=str))

    state_p = sweep_dir / "state.json"
    state = json.loads(state_p.read_text()) if state_p.exists() else {}
    pushes = pushes_for(run, sweep_cfg, applied, asks, panel["changes"], panel, state, now)
    state_p.write_text(json.dumps(state))
    for p in pushes:
        ok, why = (sender or notify.send)(p["title"], p["message"], p["priority"], p.get("tags")) if not a.no_push \
            else (False, "pushes off")
        print(f'push "{p["title"]}" priority {p["priority"]}: {why}')
    print(f"sweep save: {len(fresh)} new records; {len(applied)} level updates; {len(asks)} questions; "
          f"cost ${run['costs']['total']:.3f}")
    return panel


def rebuild(data, now):
    """The panel worked out again from stored records, after a fix to the analysis. Changes nothing else."""
    sweep_dir = Path(data) / "sweep"
    run = json.loads((sweep_dir / "last_run.json").read_text())
    sweep_cfg = yaml.safe_load(open(ROOT / "config" / "sweep.yaml"))
    records = all_records(sweep_dir)
    lv = levels.load(data)
    week_end = run["window"][1][:10]
    old = json.loads((sweep_dir / "watching.json").read_text()) if (sweep_dir / "watching.json").exists() else {}
    panel = build_panel(records, sweep_cfg, load_config(), Store(data), lv, now, run, week_end)
    panel["run"]["time_utc"] = (old.get("run") or {}).get("time_utc", panel["run"]["time_utc"])
    panel["rebuilt_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    (sweep_dir / "watching.json").write_text(json.dumps(panel, indent=1, default=str))
    print(f"sweep panel rebuilt from {len(records)} stored records; nothing fetched, nothing pushed")
    return panel


if __name__ == "__main__":
    main()
