"""FINRA margin statistics (monthly spreadsheet). If FINRA fails, the hand-filled
file manual/margin_debt.csv (columns: month,debit_usd_millions; month as YYYY-MM) is used."""
import io
from pathlib import Path

import pandas as pd

from hub.sources import Result

URL = "https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx"


def month_end(x):
    return (pd.Timestamp(x) + pd.offsets.MonthEnd(0)).normalize()


def parse_xlsx(content):
    df = pd.read_excel(io.BytesIO(content))
    df = df.iloc[:, :2].dropna()
    df.columns = ["month", "debit"]
    df["month"] = pd.to_datetime(df["month"], format="mixed", errors="coerce")
    df["debit"] = pd.to_numeric(df["debit"].astype(str).str.replace(",", ""), errors="coerce")
    df = df.dropna()
    return pd.Series(df["debit"].values, index=[month_end(m) for m in df["month"]], dtype=float).sort_index()


def parse_manual(path):
    p = Path(path)
    if not p.exists():
        return pd.Series(dtype=float)
    df = pd.read_csv(p, comment="#").dropna()
    if df.empty:
        return pd.Series(dtype=float)
    return pd.Series(df["debit_usd_millions"].astype(float).values,
                     index=[month_end(str(m) + "-01") for m in df["month"]], dtype=float).sort_index()


def fetch(entries, ctx):
    res = Result()
    manual = parse_manual(Path(ctx.root) / "manual" / "margin_debt.csv")
    try:
        s = parse_xlsx(ctx.web.get(URL, timeout=90).content)
        if len(s) < 12:
            raise ValueError("FINRA file has too few rows")
        s = s.combine_first(manual)  # FINRA wins where both have a month
    except Exception as ex:
        if manual.empty:
            raise
        s = manual
        res.errors["MARGIN_DEBT"] = f"FINRA failed ({ex}); using manual/margin_debt.csv"
    for e in entries:
        res.history[e["id"]] = s[s.index >= ctx.since(e, 800)]
    return res
