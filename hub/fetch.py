"""Fetch step: ask each source that is due, write new values to the history store,
and keep a record of each source's health.

    python -m hub.fetch --data DATA_DIR [--backfill] [--only source,source]
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from hub.sources import NAMES, Ctx, adapter
from hub.store import Store
from hub.util import ROOT, load_registry, scrub, utcnow


def load_json(path, default):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else default


def save_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")


def is_due(status, every_minutes, now):
    """A source is asked again once `every_minutes` have passed since it was last tried.
    A failing source is retried every run."""
    last = status.get("last_try")
    if not last or status.get("fails", 0) > 0:
        return True
    return (now - pd.Timestamp(last)).total_seconds() >= every_minutes * 60 - 120


def run_fetch(data_dir, backfill=False, only=None, now=None, registry=None, root=ROOT, fetchers=None, state_dir=None):
    """Returns (store, live, status). `fetchers` lets tests replace the web calls.
    state_dir holds the fast-changing bookkeeping (when each source was last asked, live values).
    The scheduled run keeps it outside the data branch so that branch is not committed every run."""
    now = now or utcnow()
    reg = registry or load_registry()
    store = Store(data_dir)
    state_dir = Path(state_dir) if state_dir else Path(data_dir) / "state"
    status = load_json(state_dir / "sources.json", None)
    if status is None:   # bookkeeping lost: start from the health record kept in the data branch
        status = {k: {"fails": v.get("fails", 0), "last_ok": v.get("last_ok", "")}
                  for k, v in load_json(Path(data_dir) / "state" / "source_health.json", {}).items()}
    live = load_json(state_dir / "live.json", {})
    now_ts = pd.Timestamp(now)
    for name in NAMES:
        if only and name not in only:
            continue
        entries = [e for e in reg["series"] if e["source"] == name]
        if not entries:
            continue
        st = status.setdefault(name, {"fails": 0})
        if not backfill and not is_due(st, reg["sources"][name].get("every", 60), now_ts):
            continue
        st["last_try"] = now.isoformat()
        ctx = Ctx(now=now, backfill=backfill, root=str(root))
        for e in entries:
            s = store.series(e["id"])
            if len(s):
                ctx.last[e["id"]] = s.index[-1]
        try:
            res = (fetchers or {}).get(name, None)
            res = res(entries, ctx) if res else adapter(name).fetch(entries, ctx)
            added = 0
            for sid, s in res.history.items():
                added += store.append(sid, s, now, backfill=backfill, once=sid in res.once)
            for sid, (v, t) in res.live.items():
                live[sid] = {"value": v, "time": t}
            got = [e["id"] for e in entries if e["id"] in res.history and len(res.history[e["id"]])]
            st["series_errors"] = {k: scrub(v)[:200] for k, v in res.errors.items()}
            if got or not res.errors:
                st.update(fails=0, last_ok=now.isoformat(), last_error="")
            else:
                st.update(fails=st.get("fails", 0) + 1, last_error=scrub("; ".join(res.errors.values()))[:200])
            print(f"{name}: {len(got)}/{len(entries)} series, {added} new rows"
                  + (f", problems: {st['series_errors']}" if res.errors else ""), flush=True)
        except Exception as ex:
            st.update(fails=st.get("fails", 0) + 1, last_error=scrub(f"{type(ex).__name__}: {ex}")[:200])
            print(f"{name}: FAILED ({st['last_error']})", flush=True)
    # a live value is only "now" while fresh: drop any older than twice its source's interval plus 15 minutes
    src_of = {e["id"]: e["source"] for e in reg["series"]}
    for sid in list(live):
        limit = 2 * reg["sources"].get(src_of.get(sid), {}).get("every", 60) + 15
        age = (now_ts - pd.Timestamp(live[sid]["time"])).total_seconds() / 60
        if age > limit or age < -5:
            del live[sid]
    store.save()
    save_json(state_dir / "sources.json", status)
    save_json(state_dir / "live.json", live)
    return store, live, status


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    run_fetch(a.data, backfill=a.backfill, only=[x for x in a.only.split(",") if x] or None)
