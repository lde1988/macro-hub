"""Backstop for the daily scanner's timer (GitHub's own timer is unreliable). From 02:30 UTC, if yesterday's
snapshot is missing, the hub run starts the scanner. Free.

    python -m hub.scanner.due --data data      prints "yes" or "no"
"""
import argparse
import datetime as dt
from pathlib import Path

from hub.util import utcnow


def overdue(data, now):
    if (now.hour, now.minute) < (2, 30):
        return False
    day = (now.date() - dt.timedelta(days=1)).isoformat()
    return not (Path(data) / "scanner" / "snapshots" / f"{day}.csv").exists()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    print("yes" if overdue(ap.parse_args().data, utcnow()) else "no")
