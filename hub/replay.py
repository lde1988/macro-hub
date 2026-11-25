"""Replay the dials and rules over past dates, one step per day, seeing only
what was known on each day (see hub/store.py for how back-filled history is dated).

    python -m hub.replay --data DATA_DIR --start 2024-11-25 --end 2026-11-24 --out replay.csv
"""
import argparse
import copy

import pandas as pd

from hub.signals.core import View
from hub.signals.engine import evaluate
from hub.store import Store
from hub.util import load_config, load_registry


def replay(store, registry, cfg, start, end, warmup_days=5, each=None):
    """Returns a DataFrame with one row per day: every dial's colour, the regime and both readings.
    `each(day, out)` is called for every day if given."""
    cache, state, rows = {}, None, []
    days = pd.date_range(pd.Timestamp(start) - pd.Timedelta(days=warmup_days), end, freq="D")
    for day in days:
        now = day + pd.Timedelta(hours=23, minutes=59)   # end of day UTC: that day's own close is not yet known
        out = evaluate(View(store, registry, now, asof=True, cache=cache), cfg, state)
        state = out["state"]
        if day < pd.Timestamp(start):
            continue
        row = {"date": day, "regime": out["regime"]["name"], "reading": out["reading"]["label"],
               "level": out["reading"].get("level", ""), "headline": out["reading"]["headline"],
               "old_reading": out["reading_old_rule"]["label"], "turn_confirmed": out["reading"]["turn"]["confirmed"]}
        for i, r in out["readings"].items():
            row[i] = r["colour"]
            row[i + "__v"] = r["value"]
        rows.append(row)
        if each:
            each(day, out)
    return pd.DataFrame(rows).set_index("date")


def switch_ons(colours, colour="green"):
    """How many times a dial switched to `colour`, and the share of days it spent there."""
    is_c = (colours == colour)
    return int((is_c & ~is_c.shift(1, fill_value=False)).sum()), float(is_c.mean())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", default="replay.csv")
    a = ap.parse_args()
    df = replay(Store(a.data), load_registry(), copy.deepcopy(load_config()), a.start, a.end)
    df.to_csv(a.out)
    print(df[["regime", "reading", "level", "old_reading"]].value_counts().head(20))
