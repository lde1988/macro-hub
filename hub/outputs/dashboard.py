"""The dashboard: one static page, built from the feed. No external scripts or fonts.

Order: regime banner and updated time; the reading; one line per family with its
dials folded underneath; what they're watching; sources footer.
Colour is never the only cue: every dial and family line carries a word and a symbol.
"""
import html
import math

COL = {"green": "#0aac23", "amber": "#fbb315", "red": "#dc3c3d", None: "#6b6b6b"}
SYM = {"green": "▲", "amber": "●", "red": "▼", None: "○"}
GROUPS = {"A": "Is it cheap?", "B": "Is stress still building?", "C": "Credit-event risk", "D": "Has the turn started?"}
esc = lambda x: html.escape(str(x if x is not None else ""))


def _pt(cx, cy, r, frac):
    a = math.pi * (1 - frac)   # 0 = left end, 1 = right end of the half circle
    return cx + r * math.cos(a), cy - r * math.sin(a)


def _arc(cx, cy, r, f0, f1):
    x0, y0 = _pt(cx, cy, r, f0)
    x1, y1 = _pt(cx, cy, r, f1)
    return f"M{x0:.1f},{y0:.1f} A{r},{r} 0 0 1 {x1:.1f},{y1:.1f}"


def gauge_svg(d):
    """Semi-circular gauge: three colour bands and a needle."""
    g = d.get("gauge") or {"min": 0, "max": 1, "bands": [[0, 1, None]]}
    lo, hi = g["min"], g["max"]
    span = (hi - lo) or 1
    frac = lambda v: min(max((v - lo) / span, 0.0), 1.0)
    cx, cy, r = 100, 96, 78
    parts = [f'<svg viewBox="0 0 200 108" role="img" aria-label="{esc(d["title"])}: {esc(d["word"])}, {esc(d["text"])}">']
    for a, b, colour in g["bands"]:
        f0, f1 = frac(a), frac(b)
        if f1 - f0 < 0.004:
            continue
        pad = 0.006
        parts.append(f'<path d="{_arc(cx, cy, r, f0 + (pad if f0 > 0 else 0), f1 - (pad if f1 < 1 else 0))}" '
                     f'fill="none" stroke="{COL[colour]}" stroke-width="13" opacity="{0.95 if colour == d["colour"] else 0.38}"/>')
    v = d.get("value")
    if v is not None and d.get("colour"):
        x, y = _pt(cx, cy, r - 14, frac(v))
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#f2f2f2" stroke-width="3" stroke-linecap="round"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="#f2f2f2"/></svg>')
    return "".join(parts)


def dial_card(d):
    main, _, rest = (d["text"] or "").partition(" · ")
    age = ""
    if d.get("data_date"):
        n = d.get("data_age_days")
        age = f'data {esc(d["data_date"])}' + (f" ({n}d old)" if n else " (today)")
    cls = "dial stale" if d["stale"] else "dial"
    stale = f'<p class="warn">Greyed out: {esc(d["stale_reason"])}.</p>' if d["stale"] else ""
    fresh = ' <span class="tag">fresh signal</span>' if d.get("fresh_turn_signal") else ""
    notes = "".join(f'<p class="warn">{esc(n)}</p>' for n in (d.get("extra") or {}).get("notes", []))
    return (f'<article class="{cls}" id="dial-{esc(d["id"])}"><h4>{esc(d["title"])}</h4>{gauge_svg(d)}'
            f'<p class="val">{esc(main)}</p>'
            f'<p class="word" style="color:{COL[d["colour"]]}"><span aria-hidden="true">{SYM[d["colour"]]}</span> {esc(d["word"])}{fresh}</p>'
            f'{f"<p class=more>{esc(rest)}</p>" if rest else ""}<p class="moves">{esc(d["moves"])}</p>{notes}{stale}'
            f'<p class="age">{age}</p></article>')


def section_block(s, dials):
    c = s["colour"]
    cards = "".join(dial_card(dials[i]) for i in s["dials"])
    return (f'<details class="fam"><summary>'
            f'<span class="dot" style="background:{COL[c]}"></span>'
            f'<span class="famname">{esc(s["name"])}</span>'
            f'<span class="famword" style="color:{COL[c]}"><span aria-hidden="true">{SYM[c]}</span> {esc(s["word"])}</span>'
            f'<span class="famline">{esc(s["sentence"])}</span></summary><div class="grid">{cards}</div></details>')


def render(feed):
    dials = {d["id"]: d for d in feed["dials"]}
    rd, rg, tr, alt = feed["reading"], feed["regime"], feed["trend_exit"], feed["altcoins"]
    rcol = {"BUY": "green", "HOLD": "amber", "FROTH WARNING": "red"}.get(rd["label"])
    tcol = {"RISK-ON": "green", "RISK-OFF": "red"}.get(tr["state"])
    acol = {"BUY": "green", "HOLD": "amber", "FROTH WARNING": "red"}.get(alt["label"])
    regcol = {"TURN": "green", "CALM": "green", "FRAGILE": "amber", "STRESS BUILDING": "red", "BREAK": "red"}.get(rg["name"])

    def inforce(x):
        if not x.get("since"):
            return ""
        n = x.get("days_in_force")
        return f'in force since {esc(str(x["since"])[:10])}' + (f' ({n} day{"s" if n != 1 else ""})' if n is not None else "")

    reasons = "".join(f"<li>{esc(r)}</li>" for r in rd["reasons"])
    record = f'<p class="record">Record of this warning: {esc(rd["record"])}.</p>' if rd.get("record") else ""
    kinds = {"valuation": "Valuation", "stress": "Stress and credit, by family", "turn": "Turn signals"}
    blocks, last = [], None
    for s in feed["sections"]:
        if s["kind"] != last:
            blocks.append(f'<h3>{kinds[s["kind"]]}</h3>')
            last = s["kind"]
        blocks.append(section_block(s, dials))
    srcs = "".join(
        f'<tr><td>{esc(v["credit"])}</td><td>{esc((v["last_ok"] or "never")[:16].replace("T", " "))} UTC</td>'
        f'<td>{"check only" if v["check_only"] else ""}{" · failing: " + str(v["fails_in_a_row"]) + " runs" if v["fails_in_a_row"] else ""}'
        f'{" · " + esc(v["problem"][:120]) if v["problem"] else ""}</td></tr>' for v in feed["sources"].values())
    w = feed["watching"]
    b = feed["bitcoin"]
    price_line = ""
    if b.get("price"):
        price_line = (f'Bitcoin ${b["price"]:,.0f} · realised price ${b["realised_price"]:,.0f} ({b["ratio_to_realised"]:.2f}x) · '
                      f'long-term holder cost ${b["lth_cost"]:,.0f} · short-term holder cost ${b["sth_cost"]:,.0f}')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>macro-hub</title>
<meta name="description" content="Macro and crypto dials with a framework reading. Not financial advice.">
<meta name="theme-color" content="#111315"><meta name="color-scheme" content="dark">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icons/icon-192.png" sizes="192x192" type="image/png">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><meta name="apple-mobile-web-app-title" content="macro-hub">
<style>
:root{{--bg:#111315;--card:#1a1d20;--line:#2c3136;--ink:#f2f2f2;--mute:#a4abb3;--amber:#fbb315}}
*{{box-sizing:border-box}}html{{-webkit-text-size-adjust:100%}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
padding:env(safe-area-inset-top) 16px calc(24px + env(safe-area-inset-bottom))}}
main{{max-width:1180px;margin:0 auto}}
h1{{font-size:15px;font-weight:600;letter-spacing:.04em;color:var(--mute);margin:14px 0 8px;text-transform:uppercase}}
h3{{font-size:13px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--mute);margin:26px 0 8px}}
h4{{font-size:15px;font-weight:600;margin:0 0 4px}}
p{{margin:0}}
.banner{{background:var(--card);border:1px solid var(--line);border-left:6px solid {COL[regcol]};border-radius:12px;padding:14px 16px}}
.banner .name{{font-size:26px;font-weight:700;line-height:1.15}}
.banner .detail{{color:var(--mute);margin-top:4px}}
.banner .early{{font-size:14px;margin-top:6px}}
.upd{{font-size:14px;color:var(--mute);margin-top:8px}} .upd.late{{color:var(--amber);font-weight:600}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-top:12px}}
.reading{{border-left:6px solid {COL[rcol]}}}
.reading .head{{font-size:22px;font-weight:700;line-height:1.2}}
.disc{{font-size:13px;color:var(--mute);margin-top:2px}}
.reading ul{{margin:10px 0 8px;padding-left:20px}} .reading li{{margin:3px 0}}
.lbl{{font-size:13px;color:var(--mute);text-transform:uppercase;letter-spacing:.04em}}
.sub{{display:grid;grid-template-columns:1fr;gap:10px;margin-top:12px}}
.line{{border-top:1px solid var(--line);padding-top:10px}}
.line b{{font-size:17px}}
.note{{font-size:14px;color:var(--mute);margin-top:10px;font-style:italic}}
.record{{font-size:14px;margin-top:6px}}
details.fam{{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-top:8px}}
summary{{list-style:none;cursor:pointer;padding:12px 14px;display:grid;grid-template-columns:14px 1fr auto;gap:4px 10px;align-items:center}}
summary::-webkit-details-marker{{display:none}}
.dot{{width:12px;height:12px;border-radius:50%}}
.famname{{font-weight:600}} .famword{{font-weight:600;font-size:14px;white-space:nowrap}}
.famline{{grid-column:2 / -1;font-size:14px;color:var(--mute)}}
.grid{{display:grid;grid-template-columns:1fr;gap:10px;padding:4px 12px 14px}}
.dial{{background:#15181b;border:1px solid var(--line);border-radius:10px;padding:12px}}
.dial svg{{display:block;width:100%;max-width:230px;margin:2px auto 0}}
.dial .val{{font-size:19px;font-weight:700;text-align:center;font-variant-numeric:tabular-nums}}
.dial .word{{text-align:center;font-weight:600;margin-bottom:6px}}
.dial .more,.dial .moves,.dial .age,.dial .warn{{font-size:13px;color:var(--mute);margin-top:4px}}
.dial .moves{{color:#c9ced4}} .dial .warn{{color:var(--amber)}}
.dial.stale svg,.dial.stale .val,.dial.stale .word{{filter:grayscale(1);opacity:.5}}
.tag{{font-size:11px;border:1px solid currentColor;border-radius:8px;padding:0 6px;margin-left:4px;vertical-align:middle}}
table{{width:100%;border-collapse:collapse;font-size:13px;color:var(--mute)}} td{{padding:4px 6px 4px 0;border-top:1px solid var(--line);vertical-align:top}}
footer{{margin-top:26px;font-size:13px;color:var(--mute)}} footer p{{margin-top:8px}} a{{color:#9ecbff}}
@media(min-width:700px){{.grid{{grid-template-columns:repeat(2,1fr)}}.sub{{grid-template-columns:1fr 1fr}}.line{{border-top:0;border-left:1px solid var(--line);padding:0 0 0 14px}}.sub .line:first-child{{border-left:0;padding-left:0}}}}
@media(min-width:1040px){{.grid{{grid-template-columns:repeat(3,1fr)}}}}
</style></head><body><main>
<h1>macro-hub</h1>
<section class="banner" aria-label="Regime">
<p class="lbl">Regime</p><p class="name">{esc(rg["name"])}</p>
<p class="detail">{esc(rg["detail"])}{" · " + inforce(rg) if inforce(rg) else ""}</p>
{f'<p class="early">{esc(rg["early_line"])}</p>' if rg.get("early_line") else ""}
<p class="upd" id="upd" data-t="{esc(feed["generated_at"])}">updated {esc(feed["generated_at_hkt"])}</p>
</section>

<section class="card reading" aria-label="Reading">
<p class="lbl">Bitcoin reading</p>
<p class="head"><span aria-hidden="true" style="color:{COL[rcol]}">{SYM[rcol]}</span> {esc(rd["headline"])}</p>
<p class="disc">{esc(feed["disclaimer"])}{" · " + inforce(rd) if inforce(rd) else ""}</p>
<p class="note">{esc(feed["exit_note"])}</p>{record}
<ul>{reasons}</ul>
<p><span class="lbl">What would change it</span><br>{esc(rd["change"])}</p>
{f'<p class="disc" style="margin-top:8px">{esc(price_line)}</p>' if price_line else ""}
<div class="sub">
<div class="line"><p class="lbl">Altcoins</p><p><b><span aria-hidden="true" style="color:{COL[acol]}">{SYM[acol]}</span> {esc(alt["headline"])}</b></p><p class="disc">{esc(alt["why"])}</p></div>
<div class="line"><p class="lbl">Trend exit (weekly-close filter)</p><p><b><span aria-hidden="true" style="color:{COL[tcol]}">{SYM[tcol]}</span> {esc(tr["state"])}</b></p><p class="disc">{esc(tr["text"])}{" · " + inforce(tr) if inforce(tr) else ""}</p></div>
</div>
</section>

{"".join(blocks)}

<h3>What they're watching</h3>
<section class="card"><p class="disc">{esc(w.get("note", ""))}</p></section>

<footer>
<h3>Sources: last successful fetch</h3>
<table>{srcs}</table>
<p>On-chain data: Bitview (bitview.space), CC BY 4.0. The dollar index is computed from ECB reference rates and is not the official ICE index. The liquidity figure is a proxy.</p>
<p>Green = supports buying crypto, amber = neutral, red = argues against. A dial changes colour only after two runs in a row beyond a band edge.</p>
<p>Feed for bots: <a href="feed/latest.json">feed/latest.json</a> (version {esc(feed["version"])}) · <a href="feed/FEED.md">layout</a> · <a href="feed/verdicts.csv">verdict log</a></p>
<p>{esc(feed["disclaimer"])}. Public market data only.</p>
</footer>
</main>
<script>
(function(){{var e=document.getElementById('upd');if(!e)return;function f(){{var m=Math.round((Date.now()-new Date(e.dataset.t).getTime())/60000);
var t=e.textContent.split(' · ')[0];e.textContent=t+' · '+(m<1?'just now':m<120?m+' min ago':Math.round(m/60)+' h ago');
e.className='upd'+(m>{int(feed.get("stale_minutes", 60))}?' late':'');}}f();setInterval(f,60000);
if(window.matchMedia('(min-width:1040px)').matches){{document.querySelectorAll('details.fam').forEach(function(d){{d.open=true}})}}
}})();
</script>
</body></html>
"""


MANIFEST = {
    "name": "macro-hub", "short_name": "macro-hub", "description": "Macro and crypto dials with a framework reading.",
    "start_url": "./", "scope": "./", "display": "standalone", "background_color": "#111315", "theme_color": "#111315",
    "icons": [{"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
              {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
              {"src": "icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
}
