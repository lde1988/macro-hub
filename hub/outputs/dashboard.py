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
    stale = (f'<p class="warn">Greyed out: {esc(d["stale_reason"])}.</p>' if d["stale"]
             else f'<p class="warn">{esc(d["stale_reason"])}.</p>' if d.get("stale_reason") else "")
    fresh = ' <span class="tag">fresh signal</span>' if d.get("fresh_turn_signal") else ""
    notes = "".join(f'<p class="warn">{esc(n)}</p>' for n in (d.get("extra") or {}).get("notes", []))
    return (f'<article class="{cls}" id="dial-{esc(d["id"])}"><h4>{esc(d["title"])}</h4>{gauge_svg(d)}'
            f'<p class="val">{esc(main)}</p>'
            f'<p class="word" style="color:{COL[d["colour"]]}"><span aria-hidden="true">{SYM[d["colour"]]}</span> {esc(d["word"])}{fresh}</p>'
            f'{f"<p class=more>{esc(rest)}</p>" if rest else ""}<p class="moves">{esc(d["moves"])}</p>{notes}{stale}'
            f'<p class="age">{age}</p></article>')


def fmt_price(x):
    if x is None:
        return "n/a"
    if x >= 1e9:
        return f"${x / 1e9:,.1f}bn"
    if x >= 1_000_000:
        return f"${x / 1e6:,.2f}m"
    if x >= 100:
        return f"${x:,.0f}"
    if x >= 1:
        return f"${x:,.2f}"
    if x >= 0.01:
        return f"${x:,.4f}"
    return f"${x:.6f}"


VZ = [(-4, -3, "green", "−3 SD"), (-3, -2, "green", "−2 SD"), (-2, -1, "green", "−1 SD"), (-1, 0, "amber", "below fair"),
      (0, 1, "amber", "above fair"), (1, 2, "red", "+1 SD"), (2, 3, "red", "+2 SD"), (3, 4, "red", "+3 SD")]
ZONE_INDEX = {"-3 SD oversold": 0, "-2 SD oversold": 1, "-1 SD oversold": 2, "below fair value": 3, "above fair value": 4,
              "+1 SD overbought": 5, "+2 SD overbought": 6, "+3 SD overbought": 7}


def minus(text):
    """Typographic minus sign, so "-1.71" does not read as a dash."""
    return text.replace("-", "−")


def valuation_svg(z, zone_name, colour, grey=False, title=""):
    """Eight-zone gauge from -4 to +4 SD, a needle at the reading, and the SD number large under the pivot."""
    cx, cy, r = 150, 128, 100
    frac = lambda x: (min(max(x, -4), 4) + 4) / 8
    on_i = ZONE_INDEX.get(zone_name, -1)
    num_col = "#9aa1a8" if grey else COL[colour]
    parts = [f'<svg viewBox="0 0 300 178" role="img" aria-label="{esc(title)}: {z:+.2f} standard deviations, {esc(zone_name)}">']
    for i, (lo, hi, col, lab) in enumerate(VZ):
        f0, f1 = frac(lo) + 0.004, frac(hi) - 0.004
        on = i == on_i
        parts.append(f'<path d="{_arc(cx, cy, r, f0, f1)}" fill="none" stroke="{COL[col]}" stroke-width="16" opacity="{0.95 if on else 0.32}"/>')
        x, y = _pt(cx, cy, r + 20, (frac(lo) + frac(hi)) / 2)
        weight = ' font-weight="700"' if on else ""
        if "fair" in lab:      # two short lines, so "below fair" and "above fair" do not run into each other
            word = lab.split()[0]
            parts.append(f'<text x="{x:.1f}" y="{y - 4:.1f}" text-anchor="middle" font-size="10" fill="#c9ced4"{weight}>'
                         f'<tspan x="{x:.1f}">{word}</tspan><tspan x="{x:.1f}" dy="11">fair</tspan></text>')
        else:
            parts.append(f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" font-size="11" fill="#c9ced4"{weight}>{lab}</text>')
    x, y = _pt(cx, cy, r - 18, frac(z))
    parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#f2f2f2" stroke-width="3.5" stroke-linecap="round"/>'
                 f'<circle cx="{cx}" cy="{cy}" r="6" fill="#f2f2f2"/>'
                 f'<text x="{cx}" y="{cy + 42}" text-anchor="middle" font-size="36" font-weight="800" fill="{num_col}">{minus(f"{z:+.2f}")}</text></svg>')
    return "".join(parts)


def reading_block(title, r, label, grey=False, warnings=(), body="", lead=False, sym=""):
    """One reading on a coin card: heading, zone in words with a symbol, label, the dial (SD number large), detail."""
    c = r["colour"]
    shade = "#9aa1a8" if grey else COL[c]
    warn = "".join(f'<p class="cvwarn">{esc(w[:1].upper() + w[1:])}.</p>' for w in warnings)
    zone_text = minus(r["zone"][:1].upper() + r["zone"][1:])
    return (f'<section class="cvblock{" lead" if lead else ""}{" grey" if grey else ""}"><p class="cvh">{esc(title)}</p>'
            f'<p class="cvzone" style="color:{shade}"><span aria-hidden="true">{SYM[c]}</span> {esc(zone_text)}</p>'
            f'<p class="cvlabel">{esc(label)}</p>{warn}'
            f'<div class="cvdial">{valuation_svg(r["z"], r["zone"], c, grey, f"{sym} {title}")}</div>{body}</section>')


def empty_block(title, big, small, label=""):
    return (f'<section class="cvblock grey"><p class="cvh">{esc(title)}</p><p class="cvmid muted">{esc(big)}</p>'
            f'<p class="cvsub">{esc(small)}</p>{f"<p class=cvlabel>{esc(label)}</p>" if label else ""}</section>')


def long_term_block(v, lead):
    title = "Long-term trend (log regression)"
    if v["status"] in ("none", "too_little"):
        msg = "too little history" + (f' ({v["months"]} months)' if v.get("months") is not None else "") if v["status"] == "too_little" else "no data yet"
        return empty_block(title, msg, "No dial is drawn for under a year of history.", v.get("label", "")).replace(
            "</section>", f'<p class="cvnote">{esc(v.get("drift_note", ""))}</p></section>')
    bands = "".join(f'<tr><td>{lab}</td><td>{fmt_price(v["bands"][f"{k:+d}"]) if k else fmt_price(v["fair_value"])}</td></tr>'
                    for k, lab in ((3, "+3 SD"), (2, "+2 SD"), (1, "+1 SD"), (0, "Fair value"), (-1, "−1 SD"), (-2, "−2 SD"), (-3, "−3 SD")))
    when = "live" if v.get("price_is_live") else f'close {v["last_close_date"]}'
    hist = f'{v["years"]:.1f} years' if v["years"] >= 1 else f'{v["months"]} months'
    body = (f'<p class="cvsub">Fair value {fmt_price(v["fair_value"])} · assumes {minus(f"{v[chr(103) + chr(114) + "owth_per_year"] * 100:+.0f}")}% a year</p>'
            f'<p class="cvprice">Price now <b>{fmt_price(v["price"])}</b> <span class="cvsub">({esc(when)})</span></p>'
            f'<table class="cvbands">{bands}</table>'
            f'<p class="cvsub">History used: {hist}, from {esc(v["history_from"])} · line fit R² {v["r2"]:.2f}</p>'
            f'<p class="cvnote">{esc(v.get("drift_note", ""))}</p>')
    return reading_block(title, v, v.get("label", ""), v["status"] == "greyed", v.get("warnings", []), body, lead, v["sym"])


def recent_block(st, lead):
    title = "Recent trend (stretch from its 200-day average)"
    if not st:
        return ""
    if st.get("status") != "ok":
        return empty_block(title, "too little history", f'Needs 365 days of the measure; {st.get("days") or 0} available.', st.get("label", ""))
    body = (f'<p class="cvsub">Price is {st["ratio"]:.2f} times its 200-day average ({fmt_price(st["ma"])}); usually {st["typical_ratio"]:.2f} times. '
            f'Scored against {st["days"]:,} days.</p>')
    return reading_block(title, st, st.get("label", ""), False, (), body, lead)


def revenue_block(rv):
    title = "Price against revenue"
    if not rv:
        return ""
    unlock = f'Still to unlock: {rv["unlock"]:.0%} of supply.' if rv.get("unlock") is not None else ""
    if rv["status"] == "waiting":
        n = rv["available_in"]
        return empty_block(title, f'available in {n} day{"s" if n != 1 else ""}',
                           f'Needs a year of fees plus a year of history of the multiple. {unlock}'.strip(), rv.get("label", ""))
    if rv["status"] != "ok":
        return empty_block(title, "no data yet", unlock, rv.get("label", ""))
    caveat = rv.get("caveat") or (plain_approx if rv.get("approximate") else "")
    warn = [caveat] if caveat else []
    body = (f'<p class="cvsub">Fully diluted value {fmt_price(rv["fdv"])} is {rv["multiple"]:,.0f} times the last year\'s fees '
            f'({fmt_price(rv["fees_365"])}); usually {rv["typical_multiple"]:,.0f} times. Scored against {rv["days"]:,} days.</p>'
            f'<p class="cvsub">{esc(unlock)}</p>'
            + (f'<p class="cvnote">{esc(rv["note"])}</p>' if rv.get("note") else "")
            + '<p class="cvnote">Fees mean different things for different coins (trading fees, gas, oracle payments). Compare each coin only with its own history.</p>')
    return reading_block(title, rv, rv.get("label", ""), bool(caveat), warn, body, False)


plain_approx = "approximate: past supply estimated"


def valuation_card(v):
    head = f'<h4>{esc(v["sym"])} <span class="cvname">{esc(v["name"])}</span></h4><p class="cvmethods">{esc(v.get("methods", ""))}</p>'
    st = v.get("stretch") or {}
    lead_recent = v["status"] in ("greyed", "too_little") and st.get("status") == "ok"
    first, second = (recent_block(st, True), long_term_block(v, False)) if lead_recent else (long_term_block(v, True), recent_block(st, False))
    return f'<article class="cvcard" id="cv-{esc(v["sym"].lower())}">{head}{first}{second}{revenue_block(v.get("revenue"))}</article>'


def valuations_pane(vals):
    if not vals:
        return '<section class="card"><p class="disc">No coin data yet.</p></section>'
    strip = "".join(f'<a href="#cv-{esc(v["sym"].lower())}" data-i="{i}"><span class="dot" style="background:'
                    f'{COL[v.get("colour")] if v.get("status") == "ok" else "#6b6b6b"}"></span>{esc(v["sym"])}</a>' for i, v in enumerate(vals))
    cards = "".join(valuation_card(v) for v in vals)
    return (f'<p class="disc cvintro">Up to three readings per coin, each in standard deviations from that coin\'s own norm: the long-term trend '
            f'(a straight line through the log of its whole price history), the recent trend (price against its 200-day average) and, where '
            f'fee data allows, price against revenue. Context only: these do not enter the reading or any alert.</p>'
            f'<nav class="cvstrip" aria-label="Coins">{strip}</nav><div class="cvtrack" id="cvtrack">{cards}</div>')


def section_block(s, dials, sentence):
    c = s["colour"]
    cards = "".join(dial_card(dials[i]) for i in s["dials"])
    return (f'<details class="fam"><summary>'
            f'<span class="dot" style="background:{COL[c]}"></span>'
            f'<span class="famname">{esc(s["name"])}</span>'
            f'<span class="famword" style="color:{COL[c]}"><span aria-hidden="true">{SYM[c]}</span> {esc(s["word"])}</span>'
            f'<span class="famline">{esc(sentence)}</span></summary>'
            f'<p class="count">{esc(s["sentence"])}</p><div class="grid">{cards}</div></details>')


def render(feed):
    dials = {d["id"]: d for d in feed["dials"]}
    pl, rd, alt = feed["plain"], feed["reading"], feed["altcoins"]
    hl, bd, tr, ty = pl["headline"], pl["backdrop"], pl["trend"], pl["tally"]
    acol = {"BUY": "green", "HOLD": "amber", "FROTH WARNING": "red"}.get(alt["label"])
    aword = {"BUY": "Buy", "HOLD": "Hold", "FROTH WARNING": "Sell signal"}.get(alt["label"], "Hold")

    since = ""
    if rd.get("since"):
        n = rd.get("days_in_force")
        since = f' · in force since {esc(str(rd["since"])[:10])}' + (f' ({n} day{"s" if n != 1 else ""})' if n is not None else "")
    small = pl["weak_record"] or feed["exit_note"]
    total = max(ty["groups"], 1)
    bar = "".join(f'<span style="width:{ty[c] / total * 100:.1f}%;background:{COL[c]}" title="{ty[c]} {w}"></span>'
                  for c, w in (("green", "support buying"), ("amber", "neutral"), ("red", "against")) if ty[c])
    reasons = "".join(f"<li>{esc(r)}</li>" for r in rd["reasons"])
    kinds = {"valuation": "Price and trend", "stress": "Stress and credit, by group", "turn": "Signs of a turn"}
    blocks, last = [], None
    for s in feed["sections"]:
        if s["kind"] != last:
            blocks.append(f'<h3>{kinds[s["kind"]]}</h3>')
            last = s["kind"]
        blocks.append(section_block(s, dials, pl["groups"].get(s["id"], "")))
    srcs = "".join(
        f'<tr><td>{esc(v["credit"])}</td><td>{esc((v["last_ok"] or "never")[:16].replace("T", " "))} UTC</td>'
        f'<td>{"check only" if v["check_only"] else ""}{" · failing: " + str(v["fails_in_a_row"]) + " runs" if v["fails_in_a_row"] else ""}'
        f'{" · " + esc(v["problem"][:120]) if v["problem"] else ""}</td></tr>' for v in feed["sources"].values())
    w = feed["watching"]
    b = feed["bitcoin"]
    price_line = ""
    if b.get("price"):
        price_line = (f'Bitcoin ${b["price"]:,.0f} · average price holders paid ${b["realised_price"]:,.0f} ({b["ratio_to_realised"]:.2f}x) · '
                      f'long-term holders paid ${b["lth_cost"]:,.0f} · recent buyers paid ${b["sth_cost"]:,.0f}')
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
h1{{font-size:15px;font-weight:600;letter-spacing:.04em;color:var(--mute);margin:14px 0 8px;text-transform:uppercase;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}}
h3{{font-size:13px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--mute);margin:26px 0 8px}}
h4{{font-size:15px;font-weight:600;margin:0 0 4px}}
p{{margin:0}}
.upd{{font-size:13px;color:var(--mute);font-weight:400;letter-spacing:0;text-transform:none}} .upd.late{{color:var(--amber);font-weight:600}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-top:12px}}
.top{{display:grid;grid-template-columns:1fr;gap:14px;align-items:center}}
.lamp{{width:132px;height:132px;border-radius:50%;margin:0 auto;display:flex;flex-direction:column;align-items:center;justify-content:center;
background:{COL[hl["colour"]]};color:#0b0b0b;box-shadow:0 0 0 6px #0b0d0e,0 0 0 8px {COL[hl["colour"]]}}}
.lamp .sym{{font-size:22px;line-height:1}} .lamp .w{{font-size:30px;font-weight:800;letter-spacing:.03em;line-height:1.1}}
.why .sentence{{font-size:20px;font-weight:600;line-height:1.3}}
.disc{{font-size:13px;color:var(--mute);margin-top:6px}}
.note{{font-size:13px;color:var(--mute);margin-top:4px;font-style:italic}}
.tally{{margin-top:14px}} .tally p{{font-size:15px}}
.bar{{display:flex;height:10px;border-radius:5px;overflow:hidden;gap:2px;margin-top:6px;background:#0b0d0e}} .bar span{{display:block}}
.lines{{display:grid;grid-template-columns:1fr;gap:0;margin-top:12px}}
.line{{border-top:1px solid var(--line);padding:10px 0}}
.line b{{font-size:16px}} .line .disc{{margin-top:2px}}
.lbl{{font-size:12px;color:var(--mute);text-transform:uppercase;letter-spacing:.05em}}
details.more{{border-top:1px solid var(--line);padding-top:10px}} details.more summary{{display:block;padding:0;cursor:pointer;color:#9ecbff;font-size:14px}}
details.more ul{{margin:10px 0 8px;padding-left:20px;font-size:15px}} details.more li{{margin:3px 0}}
details.fam{{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-top:8px}}
details.fam summary{{list-style:none;cursor:pointer;padding:12px 14px;display:grid;grid-template-columns:14px 1fr auto;gap:4px 10px;align-items:center}}
summary::-webkit-details-marker{{display:none}}
.dot{{width:12px;height:12px;border-radius:50%}}
.famname{{font-weight:600}} .famword{{font-weight:600;font-size:14px;white-space:nowrap}}
.famline{{grid-column:2 / -1;font-size:14px;color:#c9ced4}}
.count{{padding:0 14px 8px 38px;font-size:13px;color:var(--mute)}}
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
.tabr{{position:absolute;opacity:0;pointer-events:none}}
.tabs{{display:flex;gap:6px;margin:6px 0 2px}} .tabs label{{flex:1;text-align:center;padding:9px 6px;border:1px solid var(--line);border-radius:10px;cursor:pointer;color:var(--mute);font-weight:600;font-size:15px}}
#tab1:checked ~ .tabs label[for=tab1],#tab2:checked ~ .tabs label[for=tab2]{{background:var(--card);color:var(--ink);border-color:#4a5158}}
.pane{{display:none}} #tab1:checked ~ .p1,#tab2:checked ~ .p2{{display:block}}
.cvintro{{margin-top:12px}}
.cvstrip{{display:flex;gap:6px;overflow-x:auto;padding:10px 0 6px;scrollbar-width:none}} .cvstrip::-webkit-scrollbar{{display:none}}
.cvstrip a{{flex:0 0 auto;display:flex;align-items:center;gap:6px;padding:6px 10px;border:1px solid var(--line);border-radius:16px;color:var(--ink);text-decoration:none;font-size:14px;font-weight:600}}
.cvstrip a.on{{background:var(--card);border-color:#9ecbff}}
.cvtrack{{display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;padding-bottom:10px;scrollbar-width:thin}}
.cvcard{{flex:0 0 100%;scroll-snap-align:center;scroll-snap-stop:always;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}}
.cvcard h4{{font-size:18px}} .cvname{{color:var(--mute);font-weight:400;font-size:15px}}
.cvbig{{font-size:40px;font-weight:800;line-height:1.1;margin-top:8px;font-variant-numeric:tabular-nums}} .cvbig.muted{{font-size:22px;color:var(--mute)}}
.cvzone{{font-size:18px;font-weight:700;margin-top:2px}} .cvlabel{{font-size:13px;color:#c9ced4;margin-top:6px}}
.cvwarn{{font-size:14px;color:var(--amber);margin-top:6px}}
.cvdial svg{{display:block;width:100%;max-width:340px;margin:8px auto 0}}
.cvblock{{border-top:1px solid var(--line);margin-top:14px;padding-top:12px}} .cvblock.lead{{border-top:0;margin-top:4px;padding-top:0}}
.cvblock.grey .cvdial{{filter:grayscale(1);opacity:.5}} .cvmethods{{font-size:13px;color:#c9ced4;margin-top:4px}}
.cvh{{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--mute);margin-top:10px}} .cvmid{{font-size:26px;font-weight:800;margin-top:4px}} .cvmid.muted{{font-size:18px}}
.cvsub{{font-size:13px;color:var(--mute);margin-top:4px}} .cvprice{{margin-top:8px}}
.cvbands{{margin-top:8px;font-size:14px;color:var(--ink)}} .cvbands td{{padding:3px 0}} .cvbands td:last-child{{text-align:right;font-variant-numeric:tabular-nums}}
.cvnote{{font-size:12px;color:var(--mute);margin-top:8px;font-style:italic}}
@media(min-width:700px){{.top{{grid-template-columns:150px 1fr;gap:22px}}.lamp{{margin:0}}.grid{{grid-template-columns:repeat(2,1fr)}}
.lines{{grid-template-columns:repeat(3,1fr);gap:18px}}.line{{border-top:0;border-left:1px solid var(--line);padding:0 0 0 14px}}.lines .line:first-child{{border-left:0;padding-left:0}}}}
@media(min-width:700px){{.cvcard{{flex-basis:calc(50% - 6px)}}}}
@media(min-width:1040px){{.grid{{grid-template-columns:repeat(3,1fr)}}.cvcard{{flex-basis:calc(33.333% - 8px)}}}}
</style></head><body><main>
<h1><span>macro-hub</span><span class="upd" id="upd" data-t="{esc(feed["generated_at"])}">updated {esc(feed["generated_at_hkt"])}</span></h1>
<input type="radio" name="tab" id="tab1" class="tabr" checked><input type="radio" name="tab" id="tab2" class="tabr">
<nav class="tabs"><label for="tab1">Dashboard</label><label for="tab2">Coin valuations</label></nav>
<div class="pane p1">
<section class="card" aria-label="Reading">
<div class="top">
<div class="lamp" role="img" aria-label="{esc(hl["word"])}"><span class="sym" aria-hidden="true">{hl["symbol"]}</span><span class="w">{esc(hl["word"])}</span></div>
<div class="why">
<p class="sentence">{esc(hl["sentence"])}</p>
<p class="disc">{esc(feed["disclaimer"])}{since}</p>
<p class="note">{esc(small)}</p>
</div>
</div>
<div class="tally"><p>{esc(ty["text"])}</p><div class="bar" role="img" aria-label="{esc(ty["text"])}">{bar}</div></div>
<div class="lines">
<div class="line"><p class="lbl">Backdrop</p><p><b>{esc(bd["text"])}</b></p>{f'<p class="disc">{esc(bd["early"])}</p>' if bd["early"] else ""}</div>
<div class="line"><p class="lbl">Bitcoin's weekly trend</p><p><b><span aria-hidden="true" style="color:{COL[tr["colour"]]}">{SYM[tr["colour"]]}</span> {esc(tr["text"])}</b></p><p class="disc">{esc(tr.get("detail", ""))}</p></div>
<div class="line"><p class="lbl">Altcoins</p><p><b><span aria-hidden="true" style="color:{COL[acol]}">{SYM[acol]}</span> {esc(aword)}</b></p><p class="disc">{esc(alt["why"][:1].upper() + alt["why"][1:])}.</p></div>
</div>
<details class="more"><summary>The detail behind this reading</summary>
<ul>{reasons}</ul>
<p><span class="lbl">What would change it</span><br>{esc(pl["what_would_change"])}</p>
{f'<p class="disc" style="margin-top:8px">{esc(price_line)}</p>' if price_line else ""}
</details>
</section>

{"".join(blocks)}

<h3>What they're watching</h3>
<section class="card"><p class="disc">{esc(w.get("note", ""))}</p></section>
</div>
<div class="pane p2" id="valuations">{valuations_pane(feed.get("valuations") or [])}</div>

<footer>
<h3>Sources: last successful fetch</h3>
<table>{srcs}</table>
<p>Coin price histories: <a href="https://coinmetrics.io">Coin Metrics</a> community data, CC BY-NC 4.0, used for non-commercial purposes.
Fees and stablecoin supply: <a href="https://defillama.com">DefiLlama</a>. Coin supply figures: CoinGecko.</p>
<p>On-chain data: Bitview (bitview.space), CC BY 4.0. The dollar index is computed from ECB reference rates and is not the official ICE index. The liquidity figure is a proxy.</p>
<p>Green = supports buying crypto, amber = neutral, red = argues against. A dial changes colour only after two runs in a row beyond a band edge.</p>
<p>Feed for bots: <a href="feed/latest.json">feed/latest.json</a> (version {esc(feed["version"])}) · <a href="feed/FEED.md">layout</a> · <a href="feed/verdicts.csv">verdict log</a></p>
<p>{esc(feed["disclaimer"])}. Public market data only.</p>
</footer>
</main>
<script>
(function(){{var e=document.getElementById('upd');if(!e)return;var t0=e.textContent;function f(){{var m=Math.round((Date.now()-new Date(e.dataset.t).getTime())/60000);
e.textContent=t0+' · '+(m<1?'just now':m<120?m+' min ago':Math.round(m/60)+' h ago');
e.className='upd'+(m>{int(feed.get("stale_minutes", 60))}?' late':'');}}f();setInterval(f,60000);
if(window.matchMedia('(min-width:1040px)').matches){{document.querySelectorAll('details.fam').forEach(function(d){{d.open=true}})}}
var t2=document.getElementById('tab2'),tr=document.getElementById('cvtrack');
function showVal(){{if(location.hash.indexOf('#cv')===0||location.hash==='#valuations')t2.checked=true;}}showVal();window.addEventListener('hashchange',showVal);
if(tr){{var links=document.querySelectorAll('.cvstrip a');
links.forEach(function(a){{a.addEventListener('click',function(ev){{ev.preventDefault();var c=document.getElementById(a.getAttribute('href').slice(1));
tr.scrollTo({{left:c.offsetLeft-tr.offsetLeft,behavior:'smooth'}});}})}});
function mark(){{var w=tr.firstElementChild?tr.firstElementChild.getBoundingClientRect().width+12:1,i=Math.round(tr.scrollLeft/w);
links.forEach(function(a,j){{a.classList.toggle('on',j===i)}});}}tr.addEventListener('scroll',function(){{window.requestAnimationFrame(mark)}});mark();}}
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
