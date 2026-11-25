"""Source adapters. Each module has fetch(entries, ctx) and returns a Result.

entries: the registry entries that belong to this source.
ctx:     Ctx below (web session, time, whether this is a back-fill).
History rows are for finished periods only; anything still moving today goes in
Result.live and is never written to the history store.
"""
import dataclasses
import datetime as dt
import importlib
import os

import pandas as pd

from hub.util import Web

NAMES = ["coinbase", "bitview", "coinmetrics", "defillama", "ecb", "fred", "finra", "treasury",
         "nasdaq", "coingecko", "coinalyze", "coinalyze_oi", "dxycheck"]


@dataclasses.dataclass
class Ctx:
    now: dt.datetime
    backfill: bool = False
    web: Web = dataclasses.field(default_factory=Web)
    env: dict = dataclasses.field(default_factory=lambda: dict(os.environ))
    root: str = "."
    last: dict = dataclasses.field(default_factory=dict)  # sid -> last date already stored

    def since(self, entry, days):
        """First date to ask for: the registry start on a back-fill, otherwise a short look-back
        that is stretched to reach the last stored date, so a pause never leaves a hole in history."""
        if self.backfill:
            return pd.Timestamp(entry["start"])
        start = pd.Timestamp(self.now.date()) - pd.Timedelta(days=days)
        have = self.last.get(entry.get("id"))
        if have is not None and pd.Timestamp(have) - pd.Timedelta(days=3) < start:
            start = pd.Timestamp(have) - pd.Timedelta(days=3)   # after a long pause, reach back to what is already stored
        return max(start, pd.Timestamp(entry["start"])) if "start" in entry else start

    @property
    def today(self):
        return pd.Timestamp(self.now.date())


@dataclasses.dataclass
class Result:
    history: dict = dataclasses.field(default_factory=dict)   # sid -> Series(date -> value)
    live: dict = dataclasses.field(default_factory=dict)      # sid -> (value, ISO time)
    once: set = dataclasses.field(default_factory=set)        # sids recorded once per day, never revised
    errors: dict = dataclasses.field(default_factory=dict)    # sid -> message (partial failures)


def adapter(name):
    return importlib.import_module(f"hub.sources.{name}")
