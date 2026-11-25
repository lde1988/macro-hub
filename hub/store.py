"""History store.

One tidy table per series, split into one CSV per calendar year so that a daily
update only touches a small file:

    history/<series_id>/<year>.csv   columns: date,value,first_seen,backfill

Rules:
- A row is never changed or deleted. If a source later revises a figure, the
  revision is appended as a new row with its own first_seen time.
- first_seen is when this hub first saw that value (UTC).
- backfill=1 marks rows loaded as past history in one go. The hub did not see
  them at the time, so for point-in-time questions they count as known from
  (date + the series' usual publication lag), which is an estimate.
"""
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

COLS = ["date", "value", "first_seen", "backfill"]


def _ts(x):
    t = pd.Timestamp(x)
    return t.tz_convert("UTC").tz_localize(None) if t.tzinfo else t


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self._cache = {}
        self._dirty = {}  # sid -> set of years with new rows

    # ------------------------------------------------------------ reading
    def raw(self, sid):
        """Every row ever recorded for a series, oldest first."""
        if sid not in self._cache:
            d = self.root / "history" / sid
            files = sorted(d.glob("*.csv")) if d.exists() else []
            if files:
                df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
                df["date"] = pd.to_datetime(df["date"])
                df["first_seen"] = pd.to_datetime(df["first_seen"], utc=True).dt.tz_localize(None)
                df["backfill"] = df["backfill"].astype(int)
            else:
                df = pd.DataFrame({"date": pd.Series(dtype="datetime64[ns]"), "value": pd.Series(dtype=float),
                                   "first_seen": pd.Series(dtype="datetime64[ns]"), "backfill": pd.Series(dtype=int)})
            self._cache[sid] = df
        return self._cache[sid]

    def series(self, sid, asof=None, lag_days=0):
        """Latest known value for each date, as it was known at `asof` (default: now)."""
        df = self.raw(sid)
        if df.empty:
            return pd.Series(dtype=float, name=sid, index=pd.DatetimeIndex([]))
        if asof is not None:
            t = _ts(asof)
            known = np.where(df["backfill"] == 1, df["date"] + pd.Timedelta(days=lag_days), df["first_seen"])
            df = df[pd.to_datetime(known) <= t]
        df = df.sort_values(["date", "first_seen"], kind="stable")
        s = df.groupby("date")["value"].last()
        s.name = sid
        return s

    def known_at(self, sid, lag_days=0):
        """For fast replays: (latest series, date each value became known, has_revisions)."""
        df = self.raw(sid)
        if df.empty:
            e = pd.DatetimeIndex([])
            return pd.Series(dtype=float, index=e), pd.Series(dtype="datetime64[ns]", index=e), False
        known = pd.to_datetime(np.where(df["backfill"] == 1, df["date"] + pd.Timedelta(days=lag_days), df["first_seen"]))
        revised = bool(df["date"].duplicated().any())
        d = df.assign(known=known).sort_values(["date", "first_seen"], kind="stable")
        g = d.groupby("date")
        return g["value"].last(), g["known"].last(), revised

    # ------------------------------------------------------------ writing
    def append(self, sid, obs, now, backfill=False, once=False):
        """Record observations. Returns the number of rows added.

        obs: pandas Series indexed by date. A row is added when the date is new
        or the value differs from the latest one recorded for that date.
        once=True never revises a date that already has a value (daily snapshots).
        """
        if obs is None or len(obs) == 0:
            return 0
        obs = pd.Series(obs).dropna().astype(float)
        obs.index = pd.to_datetime(obs.index).normalize()
        obs = obs[~obs.index.duplicated(keep="last")].sort_index()
        cur = self.series(sid)
        common = obs.index.intersection(cur.index)
        new_dates = obs.index.difference(cur.index)
        changed = [] if once else [d for d in common if not np.isclose(obs[d], cur[d], rtol=1e-9, atol=1e-12)]
        take = obs.loc[new_dates.union(pd.DatetimeIndex(changed))]
        if take.empty:
            return 0
        add = pd.DataFrame({"date": take.index, "value": take.values,
                            "first_seen": _ts(now).floor("s"), "backfill": int(backfill)})
        old = self.raw(sid)
        self._cache[sid] = add if old.empty else pd.concat([old, add], ignore_index=True)
        self._dirty.setdefault(sid, set()).update(add["date"].dt.year.unique().tolist())
        return len(add)

    def save(self):
        """Write the year files that gained rows. Returns the list of files written."""
        written = []
        for sid, years in self._dirty.items():
            df = self._cache[sid]
            d = self.root / "history" / sid
            d.mkdir(parents=True, exist_ok=True)
            for y in sorted(years):
                part = df[df["date"].dt.year == y].sort_values(["date", "first_seen"], kind="stable")
                out = part.assign(date=part["date"].dt.strftime("%Y-%m-%d"),
                                  first_seen=part["first_seen"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                  value=part["value"].map(lambda v: repr(float(v))))
                out[COLS].to_csv(d / f"{y}.csv", index=False)
                written.append(str(d / f"{y}.csv"))
        self._dirty = {}
        return written

    def ids(self):
        d = self.root / "history"
        return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.exists() else []
