"""Backstop for the weekly sweep's timer. GitHub's own timer proved unreliable (26 Nov: the 15-minute hub
timer fired twice in 20 hours), so every hub run asks: is a weekly sweep overdue? If so the hub workflow
starts one. A sweep is overdue from Sunday 13:30 UTC (21:30 Hong Kong, 83 minutes after its slot) until the end
of Monday, when the last saved sweep is more than 6 days old and the sweep is switched on.

    python -m hub.sweep.due --data data      prints "yes" or "no"
"""
import argparse
import datetime as dt
import json
from pathlib import Path

import yaml

from hub.util import ROOT, utcnow


def overdue(last_end, now, enabled=True):
    if not enabled:
        return False
    in_window = (now.weekday() == 6 and (now.hour, now.minute) >= (13, 30)) or now.weekday() == 0
    if not in_window:
        return False
    return last_end is None or now - last_end > dt.timedelta(days=6)


def last_end(data):
    p = Path(data) / "sweep" / "last_run.json"
    try:
        return dt.datetime.fromisoformat(json.loads(p.read_text())["window"][1])
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    a = ap.parse_args()
    cfg = yaml.safe_load(open(ROOT / "config" / "sweep.yaml"))
    print("yes" if overdue(last_end(a.data), utcnow(), bool(cfg.get("enabled"))) else "no")
