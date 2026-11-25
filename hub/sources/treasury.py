"""US Treasury buyback operations (Fiscal Data). Summed per operation day, by type."""
import pandas as pd

from hub.sources import Result

URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/buybacks_operations"


def parse(rows):
    """Returns {operation type: Series(date -> par accepted in dollars)}. Rows without a
    type or without an accepted amount (announced, not yet held) are left out."""
    df = pd.DataFrame(rows)
    if df.empty:
        return {}
    df["amt"] = pd.to_numeric(df["total_par_amt_accepted"], errors="coerce")
    df["d"] = pd.to_datetime(df["operation_date"], errors="coerce")
    df = df.dropna(subset=["amt", "d"])
    df = df[df["operation_type"].isin(["Liquidity Support", "Cash Management"])]
    return {t: g.groupby("d")["amt"].sum().sort_index() for t, g in df.groupby("operation_type")}


def fetch(entries, ctx):
    res = Result()
    j = ctx.web.get(URL, params={"page[size]": 1000, "sort": "-operation_date"}, timeout=90).json()
    by_type = parse(j.get("data", []))
    for e in entries:
        s = by_type.get(e["code"], pd.Series(dtype=float))
        res.history[e["id"]] = s[s.index >= ctx.since(e, 120)]
    return res
