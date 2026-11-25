"""One scheduled run: fetch, evaluate, write the dashboard and feed, log, push.

    python -m hub.run --data data --site site --runtime runtime [--no-push]

data     the checked-out "data" branch (history, dial state, logs)
site     folder published to GitHub Pages
runtime  fast-changing bookkeeping kept in the Actions cache, not in git
"""
import argparse
import copy
import csv
import json
import shutil
from pathlib import Path

import pandas as pd

from hub import alerts, notify
from hub.fetch import load_json, run_fetch, save_json
from hub.outputs import dashboard, feed as feedmod, icons
from hub.replay import replay
from hub.signals.core import View
from hub.signals.engine import evaluate
from hub.util import ROOT, load_config, load_registry, utcnow

WARM_DAYS = 150


def warm_start(store, registry, cfg, now):
    """First run only: replay the last few months day by day so the hub knows how long each
    colour, the reading, the regime and the trend line have been in force. Nothing is pushed."""
    end = (pd.Timestamp(now).tz_localize(None) - pd.Timedelta(days=1)).normalize()
    last = {}

    def keep(day, out):
        last["out"] = out
    df = replay(store, registry, copy.deepcopy(cfg), end - pd.Timedelta(days=WARM_DAYS), end, each=keep)

    def since(col):
        s = df[col]
        changed = s[s != s.shift(1)]
        return str(changed.index[-1].date()) if len(changed) > 1 else None   # None = longer than the warm-up window
    return last["out"]["state"], {"reading": since("headline"), "regime": since("regime"), "trend_exit": since("trend")}


def update_since(since, prev, cur, now):
    stamp = pd.Timestamp(now).strftime("%Y-%m-%dT%H:%MZ")
    for k in ("reading", "regime", "trend_exit"):
        if prev and prev.get(k) != cur[k]:
            since[k] = stamp
    return since


def append_csv(path, header, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerow(row)


def write_site(site, data, fd, store, registry):
    site = Path(site)
    (site / "feed" / "history").mkdir(parents=True, exist_ok=True)
    (site / "index.html").write_text(dashboard.render(fd))
    (site / "manifest.webmanifest").write_text(json.dumps(dashboard.MANIFEST, indent=1))
    (site / ".nojekyll").write_text("")
    icons.write_all(site / "icons")
    (site / "feed" / "latest.json").write_text(json.dumps(fd, indent=1, default=str))
    shutil.copy(ROOT / "FEED.md", site / "feed" / "FEED.md")
    (site / "feed" / "series.json").write_text(json.dumps(registry["series"], indent=1))
    for sid in store.ids():
        raw = store.raw(sid).sort_values(["date", "first_seen"], kind="stable")
        raw.assign(date=raw["date"].dt.strftime("%Y-%m-%d"), first_seen=raw["first_seen"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                   ).to_csv(site / "feed" / "history" / f"{sid}.csv", index=False)
    for name in ("verdicts.csv", "dial_changes.csv"):
        src = Path(data) / "log" / name
        if src.exists():
            shutil.copy(src, site / "feed" / name)


def main(data, site, runtime, push=True, now=None, fetchers=None, sender=None):
    now = now or utcnow()
    data, runtime = Path(data), Path(runtime)
    cfg, registry = load_config(), load_registry()
    store, live, status = run_fetch(data, now=now, registry=registry, fetchers=fetchers, state_dir=runtime)
    for old in ("sources.json", "live.json"):          # bookkeeping from the first back-fill; now kept in `runtime`
        (data / "state" / old).unlink(missing_ok=True)

    st = load_json(data / "state" / "hub.json", None)
    first = st is None
    if first:
        dial_state, since = warm_start(store, registry, cfg, now)
        st = {"dials": dial_state["dials"], "since": since, "summary": None, "outbox": [], "down": [], "last_digest": ""}
    out = evaluate(View(store, registry, now, live=live), cfg, {"dials": st["dials"]})
    fd = feedmod.build(out, cfg, registry, now, status, st["since"])
    cur = alerts.summary(fd)
    st["since"] = update_since(st["since"], st["summary"], cur, now)
    fd = feedmod.build(out, cfg, registry, now, status, st["since"])
    fd["stale_minutes"] = cfg["general"]["stale_minutes"]

    pushes = alerts.plan(st["summary"], fd, cfg)
    more, st["down"] = alerts.source_pushes(status, registry, cfg, st["down"])
    pushes += more
    stamp = pd.Timestamp(now).strftime("%Y-%m-%dT%H:%M:%SZ")
    rd = fd["reading"]
    changed = first or (st["summary"] and any(st["summary"].get(k) != cur[k] for k in ("reading", "regime", "trend_exit")))
    do_digest = alerts.digest_due(now, st["last_digest"], cfg)
    if changed or do_digest:
        append_csv(data / "log" / "verdicts.csv",
                   ["time_utc", "why_logged", "reading", "level", "headline", "altcoins", "trend_exit", "regime", "turn_confirmed",
                    "btc_price", "price_to_realised", "reasons", "what_would_change_it"],
                   [stamp, "first run" if first else "change" if changed else "daily", rd["label"], rd.get("level", ""), rd["headline"],
                    fd["altcoins"]["label"], fd["trend_exit"]["state"], fd["regime"]["name"], fd["turn"]["confirmed"],
                    fd["bitcoin"].get("price"), fd["bitcoin"].get("ratio_to_realised"), " | ".join(rd["reasons"]), rd["change"]])
    for d in fd["dials"]:
        ch = out["readings"][d["id"]]["changed_from"]
        if ch:
            append_csv(data / "log" / "dial_changes.csv", ["time_utc", "dial", "from", "to", "reading"], [stamp, d["id"], ch, d["colour"], d["text"]])
    if do_digest:
        if not first:
            pushes.append(alerts.digest(fd, cfg))
        st["last_digest"] = str(feedmod.hkt(now).date())

    queue = st["outbox"] + ([] if first else pushes)     # first run: silent baseline
    left = []
    for p in queue:
        ok, why = (sender or notify.send)(p["title"], p["message"], p["priority"], p.get("tags")) if push else (False, "pushes off")
        print(f'push "{p["title"]}" priority {p["priority"]}: {why}')
        if not ok and push:
            left.append(p)                                # retry next run
    st.update(dials=out["state"]["dials"], summary=cur, outbox=left[-cfg["alerts"]["max_outbox"]:])
    save_json(data / "state" / "hub.json", st)
    save_json(data / "state" / "source_health.json",
              {k: {"fails": v.get("fails", 0), "last_ok": (v.get("last_ok") or "")[:10], "last_error": v.get("last_error", "")}
               for k, v in sorted(status.items())})
    write_site(site, data, fd, store, registry)
    print(f'{fd["generated_at_hkt"]}: {fd["regime"]["name"]} | {rd["headline"]} | trend exit {fd["trend_exit"]["state"]} | '
          f'{sum(1 for d in fd["dials"] if d["colour"])}/{len(fd["dials"])} dials with a colour, {sum(1 for d in fd["dials"] if d["stale"])} stale')
    return fd


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--site", required=True)
    ap.add_argument("--runtime", required=True)
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    main(a.data, a.site, a.runtime, push=not a.no_push)
