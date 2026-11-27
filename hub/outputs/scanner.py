"""The "Coin scanner" tab (reports/18). Context only: never part of the buy / hold reading. Not advice.
All text is escaped; the small script only sorts, filters and folds rows (no outside scripts)."""
import html
import json
from pathlib import Path

import pandas as pd

STATE_COL = {"Strong Bull": "#13c43a", "Bull": "#0a8f22", "Neutral": "#8a8f96", "Bear": "#c43535", "Strong Bear": "#ff5a5a", None: "#5b6168"}
STATE_SHORT = {"Strong Bull": "S.Bull", "Bull": "Bull", "Neutral": "Neutral", "Bear": "Bear", "Strong Bear": "S.Bear", None: "–"}
ORDER = {"Strong Bull": 5, "Bull": 4, "Neutral": 3, "Bear": 2, "Strong Bear": 1, None: 0}
MARK = {"good": ("✓", "#13c43a"), "neutral": ("●", "#fbb315"), "bad": ("✗", "#ff5a5a"), None: ("–", "#6b6b6b")}


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def load(data):
    try:
        s = json.loads((Path(data) / "scanner" / "latest.json").read_text())
        return s if isinstance(s, dict) and s.get("coins") else None
    except (OSError, ValueError):
        return None


def price(v):
    if v is None:
        return "–"
    return f"${v:,.0f}" if v >= 1000 else f"${v:,.2f}" if v >= 1 else f"${v:.4g}"


def pct(v):
    return "–" if v is None else f"{v:+.1f}%"


def chip(state):
    return f'<span class="sst" style="color:{STATE_COL.get(state)}">{esc(STATE_SHORT.get(state))}</span>'


def marks(q):
    out = []
    for key, name in (("revenue_relative", "Revenue"), ("dilution", "Dilution"), ("accrual", "To holders")):
        sym, col = MARK[q.get(key)]
        out.append(f'<span title="{esc(name)}" style="color:{col}">{sym}</span>')
    verdict = "pass" if q.get("pass") else ("no data" if not q.get("parts_scored") else "fail")
    return "".join(out) + f' <span class="qv {esc(verdict.replace(" ", ""))}">{esc(verdict)}</span>'


def detail(x):
    q, o, v = x["quality"], x["own"], x["vs_btc"]

    def tests(r):
        if not r.get("tests"):
            return esc(r.get("why") or "no rating")
        t, d = r["tests"], r.get("detail") or {}
        word = {1: "+1", 0: "0", -1: "−1"}
        return (f'price vs 50-day average {d.get("vs_average_pct")}% ({word[t["position"]]}); average over 10 days '
                f'{d.get("average_change_pct")}% ({word[t["direction"]]}); momentum {d.get("momentum")} ({word[t["momentum"]]})')
    rev = "no data"
    if q.get("revenue_growth") is not None:
        rev = (f'{q["revenue_kind"]} last 90 days ${q["revenue_90d"]:,.0f}, {q["revenue_growth"] * 100:+.0f}% on the 90 before '
               f'(fixed mark: {q["revenue_fixed"]}); rank {q["revenue_rank"]} of {q["revenue_of"]} ({q["revenue_relative"]})')
    dil = "no data"
    if q.get("dilution"):
        bits = []
        if q.get("supply_growth") is not None:
            bits.append(f'supply {q["supply_growth"] * 100:+.1f}% over a year')
        if q.get("float_share") is not None:
            bits.append(f'{q["float_share"] * 100:.0f}% of fully diluted supply circulating')
        dil = f'{"; ".join(bits)} ({q["dilution"]})'
    acc = "no data" if q.get("accrual") is None else f'{q["holders_share"] * 100:.0f}% of revenue to holders ({q["accrual"]})'
    return (f'<tr class="sd" hidden><td colspan="8"><div class="sdi"><p><b>Own trend</b> {esc(o.get("state") or "–")} since {esc(o.get("since") or "–")}: '
            f'{tests(o)}</p><p><b>Against Bitcoin</b> {esc(v.get("state") or "–")} since {esc(v.get("since") or "–")}: {tests(v)}</p>'
            f'<p><b>Revenue</b> {esc(rev)}</p><p><b>Dilution</b> {esc(dil)}</p><p><b>To holders</b> {esc(acc)}</p>'
            f'<p class="disc">Unlock schedules: no free data. Revenue from DefiLlama; supply from CoinGecko.</p></div></td></tr>')


def pane(scan):
    if not scan:
        return '<section class="card"><p class="disc">The coin scanner has not run yet.</p></section>'
    reg, coins = scan["regime"], scan["coins"]
    by = {c["id"]: c for c in coins}
    line = f' Regime line (short-term holder cost): ${reg["line"]:,.0f}.' if reg.get("line") else ""
    if reg["on"]:
        cands = [by[i] for i in scan["candidates"] if i in by]
        body = ("".join(f'<li><b>{esc(c["symbol"])}</b> {esc(c["sector"])}: own {chip(c["own"]["state"])}, vs BTC '
                        f'{chip(c["vs_btc"]["state"])}, quality {marks(c["quality"])}</li>' for c in cands)
                or "<li>No coin is Dual Bull with quality today.</li>")
        banner = (f'<section class="card sban on"><h4>Bitcoin regime ON: buy candidates</h4><p class="disc">Dual Bull '
                  f'(own trend and vs BTC both Bull or better) and passing quality.{esc(line)}</p><ul class="wl">{body}</ul></section>')
    else:
        since = f' since {esc((reg.get("since") or "")[:10])}' if reg.get("since") else ""
        body = "".join(f'<li data-meme="{int(w["meme"])}" data-exch="{int(w["exchange"])}"><b>{esc(w["symbol"])}</b> '
                       f'{pct(w["vs_btc_since_off_pct"])} · {chip(w["vs_btc_state"])}</li>'
                       for w in scan["watchlist"]) or "<li>No data yet.</li>"
        try:
            span = (pd.Timestamp(scan["day"]) - pd.Timestamp((reg.get("since") or "")[:10])).days
        except (ValueError, TypeError):
            span = None
        short = (f' Only {span} days so far, so this list is still noisy.' if span is not None and span < 30 else "")
        banner = (f'<section class="card sban off"><h4>No buy candidates: Bitcoin regime OFF{since}</h4>'
                  f'<p class="disc">The hub\'s weekly trend line is {esc(reg["state"])}.{esc(line)} Meanwhile, the coins '
                  f'holding up best against Bitcoin since the regime turned OFF (change against Bitcoin · trend against '
                  f'Bitcoin).{esc(short)}</p><ol class="wl swl">{body}</ol></section>')
    rows = []
    for c in coins:
        q = c["quality"]
        rows.append(
            f'<tr class="sr" data-own="{esc(c["own"]["state"] or "")}" data-vs="{esc(c["vs_btc"]["state"] or "")}" '
            f'data-dual="{int(c["dual_bull"])}" data-meme="{int(c["meme"])}" data-exch="{int(c["exchange"])}" data-mine="{int(c["owner"])}">'
            f'<td data-v="{esc(c["symbol"])}"><b>{esc(c["symbol"])}</b>{" ★" if c["owner"] else ""}<br><span class="sm">{esc(c["sector"])}'
            f'{" · meme" if c["meme"] else ""}{" · exchange token" if c["exchange"] else ""}</span></td>'
            f'<td data-v="{c["price"] or 0}">{price(c["price"])}</td>'
            f'<td data-v="{c["pct_since_signal"] if c["pct_since_signal"] is not None else -9e9}">{pct(c["pct_since_signal"])}</td>'
            f'<td data-v="{c["change_7d"] if c["change_7d"] is not None else -9e9}">{pct(c["change_7d"])}</td>'
            f'<td data-v="{ORDER[c["own"]["state"]]}">{chip(c["own"]["state"])}</td>'
            f'<td data-v="{ORDER[c["vs_btc"]["state"]]}">{chip(c["vs_btc"]["state"])}{" ◆" if c["dual_bull"] else ""}</td>'
            f'<td data-v="{c["days_since"] if c["days_since"] is not None else 9e9}">{c["days_since"] if c["days_since"] is not None else "–"}</td>'
            f'<td data-v="{(2 if q["pass"] else 0) + (q["parts_scored"] or 0) / 10}">{marks(q)}</td></tr>' + detail(c))
    chips = "".join(f'<button class="sf{" on" if k == "all" else ""}" data-f="{k}">{esc(t)}</button>' for k, t in
                    (("all", "All"), ("dual", "Dual Bull"), ("Strong Bull", "Strong Bull"), ("Bull", "Bull"), ("Neutral", "Neutral"),
                     ("Bear", "Bear"), ("Strong Bear", "Strong Bear"), ("mine", "Yours ★")))
    excl = "".join(f'<li>{esc(e["symbol"])} ({esc(e["name"])}): {esc("; ".join(e["reasons"]))}</li>' for e in scan["excluded"][:150])
    med = scan.get("revenue_median_growth")
    return f"""{banner}
<section class="card">
<p class="disc">Context only: never part of the buy / hold reading. Not advice. Ratings on daily closes to {esc(scan["day"])}.
Own trend in dollars; vs BTC = the coin divided by Bitcoin. ◆ = Dual Bull (both Bull or better). Quality marks: revenue
(rank against all scanned coins{f", median {med * 100:+.0f}%" if med is not None else ""}), dilution, share to holders. Tap a row for detail.</p>
<div class="sfil">{chips}</div>
<label class="stog"><input type="checkbox" id="hidememe"> Hide memecoins</label> <label class="stog"><input type="checkbox" id="hideexch"> Hide exchange tokens</label>
<div class="swrap"><table class="stab" id="stab"><thead><tr><th data-k="0">Asset</th><th data-k="1">Price</th><th data-k="2">Since signal</th>
<th data-k="3">7 days</th><th data-k="4">Own trend</th><th data-k="5">vs BTC</th><th data-k="6">Days since</th><th data-k="7">Quality</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<details class="more"><summary>How the ratings work</summary><p class="disc">Each day three tests, each +1, 0 or −1: is the price
more than 3% above or below its 50-day average; has that average risen or fallen more than 1% over 10 days; is the 20-day move large
for this coin (beyond 0.75 of its usual size). The sum, from +3 to −3, gives Strong Bull, Bull, Neutral (−1 to +1), Bear, Strong Bear.
A new state counts only after 5 daily closes in a row. An open approximation, not Alex Cole's Trend Chameleon.
Quality: revenue over the last 90 days against the 90 before (ranked: top third good, bottom third bad; the fixed ±20% mark is in each
row's detail); circulating supply growth over a year and the share of fully diluted supply circulating; the share of revenue going to
token holders. "No data" is never counted as bad. Passes = no ✗ and at least one part scored.</p></details>
<details class="more"><summary>Left out ({len(scan["excluded"])}) and why</summary><ul class="wl">{excl}</ul></details>
<p class="disc">History and honesty: a snapshot of every coin is saved each day so the scanner can be judged later. The backtest from 2020
(reports/19) covers only coins that exist today (survivorship bias), leaves out trading costs, and its settings were chosen on the same
history. Prices: Coin Metrics community data (CC BY-NC 4.0) and CoinGecko; revenue: DefiLlama.</p>
</section>"""


CSS = """
.sban h4{font-size:16px;margin:0 0 4px} .sban.off{border-color:#5a2a2a} .sban.on{border-color:#1d5a2a}
.sfil{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 6px} .sf{background:#15181b;color:var(--mute);border:1px solid var(--line);border-radius:14px;padding:5px 10px;font-size:13px}
.sf.on{color:var(--ink);border-color:#9ecbff} .stog{font-size:13px;color:var(--mute);margin-right:10px}
.swrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin-top:8px}
.stab{min-width:640px;font-size:13px;color:var(--ink)} .stab th{position:sticky;top:0;background:var(--card);text-align:left;font-size:11px;
text-transform:uppercase;letter-spacing:.04em;color:var(--mute);padding:6px 6px 6px 0;cursor:pointer;white-space:nowrap}
.stab td{padding:7px 6px 7px 0;white-space:nowrap} .stab td:first-child,.stab th:first-child{position:sticky;left:0;background:var(--card);z-index:1}
.stab tr.sr{cursor:pointer} .stab .sm{font-size:11px;color:var(--mute)} .sst{font-weight:600}
.stab tr.sd td{white-space:normal;color:#c9ced4;background:#15181b;padding:8px} .stab tr.sd p{margin:3px 0}
.sdi{position:sticky;left:8px;max-width:calc(100vw - 72px)} @media(min-width:700px){.sdi{max-width:none;position:static}}
.swl{columns:2;column-gap:18px} .swl li{break-inside:avoid} @media(min-width:700px){.swl{columns:3}}
.qv{font-size:11px;border:1px solid currentColor;border-radius:8px;padding:0 5px;margin-left:3px} .qv.pass{color:#13c43a} .qv.fail{color:#ff5a5a} .qv.nodata{color:#8a8f96}
"""

JS = """
(function(){var t=document.getElementById('stab');if(!t)return;var tb=t.tBodies[0],f='all',dir={};
function pairs(){var r=[],rs=tb.rows;for(var i=0;i<rs.length;i+=2)r.push([rs[i],rs[i+1]]);return r;}
function apply(){var hm=document.getElementById('hidememe').checked,he=document.getElementById('hideexch').checked;
pairs().forEach(function(p){var d=p[0].dataset,show=(f==='all'||(f==='dual'&&d.dual==='1')||(f==='mine'&&d.mine==='1')||d.own===f)
&&!(hm&&d.meme==='1')&&!(he&&d.exch==='1');p[0].hidden=!show;if(!show)p[1].hidden=true;});
document.querySelectorAll('.sban li[data-meme]').forEach(function(li){li.hidden=(hm&&li.dataset.meme==='1')||(he&&li.dataset.exch==='1');});
try{localStorage.setItem('scan',JSON.stringify({hm:hm,he:he}))}catch(e){}}
try{var s=JSON.parse(localStorage.getItem('scan')||'{}');document.getElementById('hidememe').checked=!!s.hm;document.getElementById('hideexch').checked=!!s.he;}catch(e){}
document.querySelectorAll('.sf').forEach(function(b){b.addEventListener('click',function(){f=b.dataset.f;
document.querySelectorAll('.sf').forEach(function(x){x.classList.toggle('on',x===b)});apply();});});
['hidememe','hideexch'].forEach(function(id){document.getElementById(id).addEventListener('change',apply);});
t.tHead.querySelectorAll('th').forEach(function(th){th.addEventListener('click',function(){var k=+th.dataset.k;dir[k]=!dir[k];
var ps=pairs();ps.sort(function(a,b){var x=a[0].cells[k].dataset.v,y=b[0].cells[k].dataset.v,nx=parseFloat(x),ny=parseFloat(y);
var c=(isNaN(nx)||isNaN(ny))?String(x).localeCompare(String(y)):nx-ny;return dir[k]?-c:c;});
ps.forEach(function(p){tb.appendChild(p[0]);tb.appendChild(p[1]);});});});
tb.addEventListener('click',function(e){var tr=e.target.closest('tr.sr');if(tr){var d=tr.nextElementSibling;d.hidden=!d.hidden;}});
apply();})();
"""
