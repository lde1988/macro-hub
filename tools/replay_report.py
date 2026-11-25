"""History replay for the point 6 report. The yardsticks are fixed here, before any result is looked at:

- Levels: value zone = 1.10x realised price; reclaim line = short-term holder realised
  price; break line = 0.96x it (the owner's stand-ins for 58,600 / 73,000 / 70,000).
- A spell = BUY (or SELL) days joined when less than 15 days apart.
- A BUY spell is "right" if Bitcoin is higher 365 days after the spell's first day, "wrong" if lower.
  A FROTH WARNING spell is "right" if Bitcoin is lower 365 days after its first day. Too recent = not judged.
- Trend exit (fixed before running, not adjusted after): every RISK-OFF spell runs from the weekly close
  that broke the line to the weekly close that reclaimed it. It is judged the same way (right if
  Bitcoin is lower 365 days after it began) and also by the plain outcome: the price when it turned
  RISK-OFF against the price when it turned RISK-ON again (lower re-entry = the exit saved money).
- At an episode (a cycle low or high) a rule is "silent" if it gave no BUY (low) or SELL (high)
  within 60 days either side.
  For trend exit, a low is "protected" if the line was RISK-OFF on the day; a high is "missed" if it was still RISK-ON 60 days after.
Nothing in config/thresholds.yaml is changed to fit the result.

    python tools/replay_report.py DATA_DIR OUT_DIR
"""
import copy
import sys

import pandas as pd

sys.path.insert(0, ".")
from hub.replay import replay  # noqa: E402
from hub.signals.dials import DIALS  # noqa: E402
from hub.store import Store  # noqa: E402
from hub.util import load_config, load_registry  # noqa: E402

START, END = "2017-09-01", "2026-11-24"
AI_FROM = "2025-07-01"   # CoreWeave listed March 2025; before that the AI basket is not meaningful
EPISODES = [  # (name, kind, window in which the extreme daily close is looked up)
    ("2017 high", "high", "2017-11-01", "2018-01-31"),
    ("2018 low", "low", "2018-11-01", "2019-02-28"),
    ("2020 low", "low", "2020-03-01", "2020-04-15"),
    ("2021 first high", "high", "2021-03-01", "2021-05-31"),
    ("2021 second high", "high", "2021-10-01", "2021-12-15"),
    ("2022 June low", "low", "2022-06-01", "2022-07-31"),
    ("2022 November low", "low", "2022-11-01", "2023-01-15"),
    ("2025 high", "high", "2025-01-01", "2025-12-31"),
    ("2026 first-half low", "low", "2026-01-01", "2026-06-30"),
]


def spells(flags, gap=15):
    out, start, prev = [], None, None
    for d, x in flags.items():
        if x:
            if start is None:
                start = d
            elif (d - prev).days >= gap:
                out.append((start, prev))
                start = d
            prev = d
    if start is not None:
        out.append((start, prev))
    return out


def fwd(price, d, days):
    t = d + pd.Timedelta(days=days)
    return None if t > price.index[-1] else float(price.asof(t) / price.asof(d) - 1)


def main(data, out):
    store, reg = Store(data), load_registry()
    cfg = copy.deepcopy(load_config())
    cfg["dynamic_levels"]["use_for_colours"] = True
    cfg["general"]["enforce_max_age"] = False   # back-filled history is dated by estimate, so the live staleness rule is not applied
    blackout = {m: AI_FROM for m in cfg["ai_basket"]["members"]}
    df = replay(store, reg, cfg, START, END, blackout=blackout)
    price = store.series("BTCUSD")
    df["price"] = price.reindex(df.index).ffill()
    df.to_csv(f"{out}/replay_daily.csv")
    ids = [d["id"] for d in DIALS]
    L = [f"Replay {START} to {END}: {len(df)} days.", ""]

    L += ["## Days in each reading", "", "| | new rule | original rule |", "|---|---|---|"]
    new = df["reading"] + df["level"].map(lambda x: f" ({x})" if x else "")
    for k in sorted(set(new) | set(df["old_reading"])):
        L.append(f"| {k} | {(new == k).sum()} | {(df['old_reading'] == k).sum()} |")
    L += ["", "Regime days: " + ", ".join(f"{k} {v}" for k, v in df["regime"].value_counts().items()), ""]

    def spell_table(title, flags, kind):
        rows = [f"### {title}", "", "| spell | days flagged | price at start | 6 months later | 12 months later | worst fall within 12 months | verdict |", "|---|---|---|---|---|---|---|"]
        res = []
        for a, b in spells(flags):
            p0 = float(price.asof(a))
            r6, r12 = fwd(price, a, 182), fwd(price, a, 365)
            path = price[a:a + pd.Timedelta(days=365)]
            dd = float(path.min() / p0 - 1)
            ok = None if r12 is None else (r12 > 0 if kind == "buy" else r12 < 0)
            res.append(ok)
            n = int(flags[a:b].sum())
            rows.append(f"| {a:%d %b %Y} to {b:%d %b %Y} | {n} | ${p0:,.0f} | {'n/a' if r6 is None else f'{r6:+.0%}'} | "
                        f"{'n/a' if r12 is None else f'{r12:+.0%}'} | {dd:+.0%} | {'too recent' if ok is None else 'right' if ok else 'wrong'} |")
        if len(rows) == 4:
            rows.append("| none | | | | | | |")
        rows += ["", f"Spells: {len(res)}; right {sum(1 for x in res if x)}, wrong {sum(1 for x in res if x is False)}, too recent {sum(1 for x in res if x is None)}.", ""]
        return rows

    L += ["## Every spell, judged 12 months on", ""]
    L += spell_table("New rule: BUY (STAGED)", (df["reading"] == "BUY") & (df["level"] == "STAGED"), "buy")
    L += spell_table("New rule: BUY (CONFIRMED)", (df["reading"] == "BUY") & (df["level"] == "CONFIRMED"), "buy")
    L += spell_table("New rule: any BUY", df["reading"] == "BUY", "buy")
    L += spell_table("Original rule: BUY", df["old_reading"] == "BUY", "buy")
    L += spell_table("FROTH WARNING (same rule in both)", df["reading"] == "FROTH WARNING", "sell")
    off = df["trend"] == "RISK-OFF"
    L += spell_table("Trend exit: RISK-OFF spells", off, "sell")
    L += ["### Trend exit: what each RISK-OFF spell did", "", "| risk-off from | price then | risk-on again | price then | days out | re-entry vs exit | lowest price while out |", "|---|---|---|---|---|---|---|"]
    saved = []
    for a, b in spells(off, gap=2):
        p0 = float(price.asof(a))
        nxt = b + pd.Timedelta(days=1)
        ended = nxt in df.index
        p1 = float(price.asof(nxt)) if ended else float(price.iloc[-1])
        low = float(price[a:b].min())
        saved.append(p1 / p0 - 1)
        L.append(f"| {a:%d %b %Y} | ${p0:,.0f} | {nxt.strftime('%d %b %Y') if ended else 'still risk-off'} | ${p1:,.0f} | {(b - a).days + 1} | {p1 / p0 - 1:+.0%} | ${low:,.0f} ({low / p0 - 1:+.0%}) |")
    L += ["", f"RISK-OFF spells: {len(saved)}; re-entry below the exit price in {sum(1 for x in saved if x < 0)}, above it in {sum(1 for x in saved if x >= 0)}. "
          f"Days risk-off: {int(off.sum())} of {len(df)} ({off.mean():.0%}).", ""]

    L += ["## Episode by episode", ""]
    for name, kind, a, b in EPISODES:
        w = price[a:b]
        d = w.idxmin() if kind == "low" else w.idxmax()
        lo, hi = d - pd.Timedelta(days=60), d + pd.Timedelta(days=60)
        win = df[lo:hi]
        want = "BUY" if kind == "low" else "FROTH WARNING"
        row = df.loc[d] if d in df.index else None
        L += [f"### {name}: {d:%d %b %Y}, ${price[d]:,.0f}", ""]
        for label, col, hl in (("New rule", "reading", "headline"), ("Original rule", "old_reading", "old_headline")):
            hit = win[win[col] == want]
            if len(hit):
                first = hit.index[0]
                lev = ""
                if col == "reading" and want == "BUY":
                    lev = " as " + ", ".join(sorted(set(hit["level"])))
                L.append(f"- **{label}: {want}**{lev} on {len(hit)} of {len(win)} days in the window; first {first:%d %b %Y} at ${price.asof(first):,.0f} "
                         f"({(first - d).days:+d} days from the {kind}, {price.asof(first) / price[d] - 1:+.0%} from it).")
            else:
                L.append(f"- **{label}: silent** (no {want} within 60 days either side).")
            if row is not None:
                L.append(f"  - On the day: {row[hl]}")
        if row is not None:
            after = df["trend"].asof(d + pd.Timedelta(days=60)) if d + pd.Timedelta(days=60) <= df.index[-1] else "n/a"
            L.append(f"- **Trend exit** on the day: {row['trend']}; 60 days later: {after}")
            L.append(f"- Regime on the day: {row['regime']}" + (f" ({row['early']})" if row["early"] else ""))
            nodata = [i for i in ids if pd.isna(row[i])]
            cols = {c: [i for i in ids if row[i] == c] for c in ("green", "red")}
            L.append(f"- Dials with no data ({len(nodata)} of {len(ids)}): {', '.join(nodata) or 'none'}")
            L.append(f"- Green: {', '.join(cols['green']) or 'none'}")
            L.append(f"- Red: {', '.join(cols['red']) or 'none'}")
        L.append("")
    L += ["## When each dial first has data", "", "| dial | first day with a reading |", "|---|---|"]
    for i in ids:
        ok = df[i].dropna()
        L.append(f"| {i} | {ok.index[0]:%d %b %Y} |" if len(ok) else f"| {i} | never in this replay |")
    open(f"{out}/replay_summary.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
