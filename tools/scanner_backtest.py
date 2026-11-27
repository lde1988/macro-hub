"""Backtest of the coin scanner's rule from 2020 (reports/19). Run after the scanner has loaded price history:

    python tools/scanner_backtest.py --data data --out out

SURVIVORSHIP BIAS: only coins that exist (and are in the top 100) today are tested; coins that died are missing,
so this flatters the rule. No trading costs. The trend settings were chosen on this same history. Quality is not
tested (free supply history is one year only). Regime: the hub's weekly trend exit replayed with its moving
stand-ins (reports/06b): RISK-OFF after a weekly close below 0.96 x short-term holder cost, RISK-ON after a weekly
close above it.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from hub.scanner import data as D, trend as T  # noqa: E402
from hub.store import Store  # noqa: E402

START = pd.Timestamp("2020-01-01")


def regime_series(btc, sth):
    """Daily ON/OFF from weekly closes (Sunday) against the moving stand-ins."""
    wk = pd.concat([btc.resample("W-SUN").last(), sth.resample("W-SUN").last()], axis=1, keys=["p", "s"]).dropna()
    on, out = True, {}
    for d, r in wk.iterrows():
        if on and r.p < 0.96 * r.s:
            on = False
        elif not on and r.p > r.s:
            on = True
        out[d] = on
    s = pd.Series(out).reindex(pd.date_range(wk.index.min(), btc.index.max()), method="ffill")
    return s.shift(1).fillna(False).astype(bool)          # a weekly close is known the next day


def stats(r, name):
    r = r.dropna()
    eq = (1 + r).cumprod()
    years = len(r) / 365
    dd = float((eq / eq.cummax() - 1).min())
    return {"rule": name, "growth": f"{eq.iloc[-1]:.2f}x", "per year": f"{eq.iloc[-1] ** (1 / years) - 1:+.0%}",
            "worst fall": f"{dd:.0%}", "days invested": f"{(r != 0).mean():.0%}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = yaml.safe_load(open(ROOT / "config" / "scanner.yaml"))
    tc = cfg["trend"]
    folder = Path(a.data) / "scanner"
    prices = {p.stem: D.read_csv(p, "close") for p in (folder / "prices").glob("*.csv")}
    latest = D.load_json(folder / "latest.json", {})
    meta = {c["id"]: c for c in latest.get("coins", [])}
    st = Store(a.data)
    btc = prices.get("bitcoin")
    sth = st.series("BV_STH_REALIZED_PRICE")
    reg = regime_series(btc, sth)
    days = pd.date_range(START, btc.index.max())
    rets = pd.DataFrame({k: v.reindex(days).pct_change(fill_method=None) for k, v in prices.items()})
    dual = {}
    tested = []
    for cid, p in prices.items():
        if cid == "bitcoin" or p.index.min() > btc.index.max() - pd.Timedelta(days=tc["min_history_days"] + 30):
            continue
        own = T.rating(p, tc)
        vs = T.rating((p / btc).dropna(), tc)
        if own.get("series") is None or vs.get("series") is None:
            continue
        d = pd.concat([own["series"], vs["series"]], axis=1).reindex(days)
        dual[cid] = (d.iloc[:, 0].isin(T.BULLISH) & d.iloc[:, 1].isin(T.BULLISH)).astype(bool)
        tested.append(cid)
    dual = pd.DataFrame(dual).fillna(False).astype(bool)
    on = reg.reindex(days).fillna(False)
    # weekly rebalance: holdings chosen on Sunday's close, held Monday to Sunday
    pick = dual[days.dayofweek == 6].reindex(days).ffill().shift(1).fillna(False).astype(bool)
    hold = pick.where(on, False)
    w = hold.div(hold.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    strat = (w * rets[w.columns].fillna(0)).sum(axis=1)
    btc_r = rets["bitcoin"].fillna(0)
    rows = [stats(strat, "Dual Bull coins, equal weight, only while the regime is ON (cash otherwise)"),
            stats(btc_r, "Hold Bitcoin"), stats(btc_r.where(on, 0), "Bitcoin only while the regime is ON")]
    # each new Dual Bull entry while the regime is ON: 30 and 90-day result against Bitcoin
    sig = []
    for cid in dual.columns:
        new = dual[cid] & ~dual[cid].shift(1, fill_value=False) & on
        for d0 in new[new].index:
            for h in (30, 90):
                d1 = d0 + pd.Timedelta(days=h)
                if d1 > btc.index.max():
                    continue
                p, b = prices[cid], btc
                try:
                    rc = float(p.asof(d1) / p.asof(d0) - 1)
                    rb = float(b.asof(d1) / b.asof(d0) - 1)
                except (TypeError, ZeroDivisionError):
                    continue
                sig.append({"coin": cid, "date": d0, "days": h, "coin_ret": rc, "btc_ret": rb, "beat": rc > rb})
    sig = pd.DataFrame(sig)
    out = [f"# Coin scanner backtest, {START:%d %b %Y} to {btc.index.max():%d %b %Y}", "",
           "**Read this first: survivorship bias.** Only coins that are in today's scanner and have free price history are "
           f"tested ({len(tested)} coins; {sum(1 for c in tested if prices[c].index.min() <= START)} of them from the start of 2020). "
           "Coins that died or dropped out (LUNA, FTT and many others) are missing, so these results flatter the rule. "
           "No trading costs or slippage. The trend settings were chosen on this same history. Quality is not tested.", "",
           "| Rule | Growth | Per year | Worst fall | Days invested |", "|---|---|---|---|---|"]
    out += [f"| {r['rule']} | {r['growth']} | {r['per year']} | {r['worst fall']} | {r['days invested']} |" for r in rows]
    if len(sig):
        out += ["", "## Each new Dual Bull while the regime was ON", "", "| After | Signals | Beat Bitcoin | Median coin | Median Bitcoin |",
                "|---|---|---|---|---|"]
        for h in (30, 90):
            s = sig[sig.days == h]
            if len(s):
                out.append(f"| {h} days | {len(s)} | {s.beat.mean():.0%} | {s.coin_ret.median():+.1%} | {s.btc_ret.median():+.1%} |")
        memes = {c for c, m in meta.items() if m.get("meme")}
        s = sig[(sig.days == 90) & ~sig.coin.isin(memes)]
        if len(s):
            out.append(f"| 90 days, memecoins left out | {len(s)} | {s.beat.mean():.0%} | {s.coin_ret.median():+.1%} | {s.btc_ret.median():+.1%} |")
    out += ["", f"Regime ON on {on.mean():.0%} of days since {START:%Y}. Coins tested: {', '.join(sorted(meta.get(c, {}).get('symbol', c) for c in tested))}."]
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "scanner_backtest.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
