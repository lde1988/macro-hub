"""The monthly budget and per-run caps. Month-to-date spend is read from the data branch's sweep/costs.csv;
every paid step asks first, and nothing paid starts once the month would pass the stop share of the budget."""
import csv
from pathlib import Path


def month_to_date(costs_csv, month):
    p = Path(costs_csv)
    if not p.exists():
        return 0.0
    with open(p) as f:
        return sum(float(r.get("total_usd") or 0) for r in csv.DictReader(f) if r.get("month") == month)


class Budget:
    def __init__(self, monthly_usd, stop_share, spent_before):
        self.limit = monthly_usd * stop_share
        self.monthly = monthly_usd
        self.before = spent_before
        self.by = {"xai": 0.0, "groq": 0.0, "gemini": 0.0}
        self.refused = []

    @property
    def run_total(self):
        return sum(self.by.values())

    @property
    def month_total(self):
        return self.before + self.run_total

    def allow(self, estimate, what):
        ok = self.month_total + estimate <= self.limit
        if not ok:
            self.refused.append(what)
        return ok

    def add(self, provider, usd):
        self.by[provider] += float(usd or 0)
