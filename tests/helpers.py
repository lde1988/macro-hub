"""Shared test helpers. All data here is made up."""
import pandas as pd

from hub.signals.core import View
from hub.store import Store
from hub.util import load_config, load_registry

REG = load_registry()
NOW = pd.Timestamp("2026-11-25 09:00")
END = "2026-11-24"


def cfg(**over):
    c = load_config()
    for k, v in over.items():
        c[k].update(v)
    return c


def daily(values, end=END, freq="D"):
    """Series of made-up values ending on `end`."""
    return pd.Series(list(values), index=pd.date_range(end=end, periods=len(values), freq=freq), dtype=float)


def flat(value, n, end=END, freq="D"):
    return daily([value] * n, end, freq)


def ramp(a, b, n, end=END, freq="D"):
    return daily([a + (b - a) * i / (n - 1) for i in range(n)], end, freq)


def view(tmp_path, data, now=NOW, live=None):
    st = Store(tmp_path)
    for sid, s in data.items():
        st.append(sid, s, pd.Timestamp("2026-01-01"), backfill=True)
    return View(st, REG, now, live={k: {"value": v, "time": str(now)} for k, v in (live or {}).items()})


def weekly_btc(week_values, last_sunday="2026-11-22"):
    """Daily Bitcoin closes where every day of a week has that week's value; the last value is the latest Sunday's week."""
    out = {}
    end = pd.Timestamp(last_sunday)
    for i, val in enumerate(reversed(week_values)):
        sunday = end - pd.Timedelta(weeks=i)
        for d in range(7):
            out[sunday - pd.Timedelta(days=d)] = float(val)
    return pd.Series(out).sort_index()


# ECB rates on a made-up day; with the other rates fixed, the dollar index is proportional to 1 / USD.
ECB0 = {"USD": 1.0963, "JPY": 174.39, "GBP": 0.8370, "CAD": 1.5700, "SEK": 11.2000, "CHF": 0.9200}


def ecb_for_dxy(targets, end=END):
    """Six ECB series that produce the given dollar-index values, one per business day."""
    from hub.signals.core import dxy_from_ecb
    base = dxy_from_ecb(*[ECB0[k] for k in ("USD", "JPY", "GBP", "CAD", "SEK", "CHF")])
    idx = pd.date_range(end=end, periods=len(targets), freq="B")
    data = {f"ECB_{k}": pd.Series([v] * len(targets), index=idx) for k, v in ECB0.items() if k != "USD"}
    data["ECB_USD"] = pd.Series([ECB0["USD"] * base / t for t in targets], index=idx)
    return data
