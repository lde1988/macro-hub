"""The "What they're watching" panel (Phase 2 weekly sweep). Context only.

Everything shown comes from data/sweep/watching.json, written by the weekly sweep. All text in it was said by
other people and is untrusted: it is always escaped here and never treated as markup or instructions.
"""
import html
import json
from pathlib import Path

OFF = {"enabled": False, "note": "Weekly sweep (Phase 2) is switched off."}
STANCE_COL = {"positive": "#0aac23", "neutral": "#fbb315", "negative": "#dc3c3d", "mixed": "#8a8f96", None: "#3a3f44"}
STANCE_SYM = {"positive": "▲", "neutral": "●", "negative": "▼", "mixed": "◆", None: "·"}
STANCE_WORD = {"positive": "positive", "neutral": "neutral", "negative": "negative", "mixed": "mixed", None: "nothing said"}
TOPIC_HELP = {"credit_risk": "positive = credit looks healthy; negative = credit risk rising"}
STATUS_COL = {"right": "#0aac23", "wrong": "#dc3c3d", "open": "#a4abb3", "needs your judgement": "#fbb315"}


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def safe_url(u):
    u = str(u or "")
    return u if u.startswith("https://") else ""


def link(u, text):
    u = safe_url(u)
    return f'<a href="{esc(u)}" rel="noopener nofollow">{esc(text)}</a>' if u else esc(text)


def load(data):
    """The panel's data from the data branch, or the switched-off placeholder."""
    p = Path(data) / "sweep" / "watching.json"
    try:
        w = json.loads(p.read_text())
    except (OSError, ValueError):
        return dict(OFF)
    return w if isinstance(w, dict) and w.get("enabled") is True else dict(OFF)


def _chip(stance, title=""):
    return (f'<span class="wchip" style="color:{STANCE_COL.get(stance, "#3a3f44")}" title="{esc(title)}">'
            f'{STANCE_SYM.get(stance, "·")}</span>')


def _bar(t):
    total = sum(t.values()) or 1
    return '<div class="bar">' + "".join(
        f'<span style="width:{t[k] / total * 100:.1f}%;background:{STANCE_COL[k]}"></span>'
        for k in ("positive", "neutral", "negative", "mixed") if t.get(k)) + "</div>"


def render(w):
    if not w.get("enabled"):
        return f'<section class="card"><p class="disc">{esc(w.get("note", ""))}</p></section>'
    topics = w["topics"]
    names = w.get("names", {})
    out = [f'<section class="card wpanel"><p class="disc">Week to {esc(w["week_end"])}. {esc(w["note"])}</p>']

    # 1. tally across the group
    rows = []
    for t, label in topics.items():
        c = w["tally"][t]
        words = " · ".join(f'{c[k]} {k}' for k in ("positive", "neutral", "negative", "mixed") if c.get(k))
        rows.append(f'<div class="wt"><p><b>{esc(label)}</b> <span class="disc">{esc(words or "nobody said")}</span></p>'
                    f'{_bar(c)}{f"<p class=note>{esc(TOPIC_HELP[t])}</p>" if t in TOPIC_HELP else ""}</div>')
    out.append('<h4 class="wh">Across the group (latest stance of each person)</h4>' + "".join(rows))

    # 2. changes of mind
    if w["changes"]:
        items = "".join(
            f'<li><b>{esc(c["person"])}</b> on {esc(topics[c["topic"]].lower())}: {_chip(c["from"])} {esc(c["from"])} '
            f'({esc(c.get("from_date"))}) → {_chip(c["to"])} {esc(c["to"])} ({esc(c.get("to_date"))}). '
            f'“{esc(c["to_quote"][:220])}” {link(c.get("url"), "source")}</li>' for c in w["changes"])
        out.append(f'<h4 class="wh">⚑ Changed their mind this week</h4><ul class="wl">{items}</ul>')
    else:
        out.append('<h4 class="wh">Changed their mind this week</h4><p class="disc">Nobody.</p>')

    # 3. data points several cited
    if w["cited"]:
        items = "".join(
            f'<li><b>{esc(c["label"])}</b>: {c["count"]} people ({esc(", ".join(names.get(p, p) for p in c["people"]))})'
            f'{"" if c["tracked_by_hub"] else " · <i>not a hub dial</i>"}</li>' for c in w["cited"])
        out.append(f'<h4 class="wh">Cited by several this week</h4><ul class="wl">{items}</ul>')

    # 4. each person
    people = []
    for p in w["people"]:
        lat = p.get("latest", {})
        chips = "".join(_chip((lat.get(t) or {}).get("stance"), f'{topics[t]}: {STANCE_WORD[(lat.get(t) or {}).get("stance")]}')
                        for t in topics)
        detail = "".join(
            f'<li>{esc(topics[t])}: <b style="color:{STANCE_COL[v["stance"]]}">{esc(v["stance"])}</b> '
            f'({esc(v.get("date"))}) “{esc(v["quote"][:260])}” '
            f'{link(v.get("url"), "at " + v["at"] if v.get("at") else "source")}</li>'
            for t, v in lat.items() if t in topics)
        flags = (" ⚑" if p.get("changed") else "") + (' <span class="tag">sceptic</span>' if p.get("balancing") else "")
        unc = (f'<p class="note">{p["uncertain_this_week"]} of this week\'s records come from shared shows, where who said what '
               f'is not certain; they are not counted.</p>') if p.get("uncertain_this_week") else ""
        people.append(f'<details class="wp"><summary><span class="wn">{esc(p["name"])}{flags}</span><span class="wc">{chips}</span>'
                      f'<span class="wd">{esc(p.get("last_seen") or "no records yet")}</span></summary>'
                      f'<ul class="wl">{detail or "<li>No stance stated yet.</li>"}</ul>{unc}</details>')
    legend = " ".join(f'{_chip(k)} {k}' for k in ("positive", "neutral", "negative", "mixed"))
    out.append(f'<h4 class="wh">Each person</h4><p class="disc">Order of symbols: '
               f'{esc(", ".join(topics.values()))}. {legend}</p>' + "".join(people))

    # 5. calibration
    if w["calibration"]:
        trs = []
        for c in w["calibration"][:15]:
            hub = f'{c["hub"]:,.2f}' if c.get("hub") is not None else "–"
            gap = f'{c["gap_pct"]:+.1f}%' if c.get("gap_pct") is not None else (c.get("note") or "–")
            chart = " (chart)" if c.get("from_chart_only") else ""
            trs.append(f'<tr><td>{esc(names.get(c["person_id"], c["person_id"]))}<br>{esc(c["date"])}</td>'
                       f'<td>{esc(c["metric"])}</td><td>{link(c.get("url"), c["their_text"])}{chart}</td>'
                       f'<td>{esc(hub)}</td><td>{esc(gap)}</td></tr>')
        trs = "".join(trs)
        out.append('<h4 class="wh">Coutts and Pal against the hub</h4><table class="wtab"><tr><td>Who</td><td>Measure</td>'
                   f'<td>They said</td><td>Hub, same day</td><td>Gap</td></tr>{trs}</table>')

    # 6. scorecard
    if w["scorecard"]:
        trs = "".join(
            f'<tr><td>{esc(names.get(s["person_id"], s["person_id"]))}</td><td>{link(s.get("url"), s["text"][:140])}'
            f'{"" if s.get("speaker_certain") else " (speaker not certain)"}</td><td>{esc(s.get("made"))} → {esc(s["by"])}</td>'
            f'<td style="color:{STATUS_COL.get(s["status"], "#a4abb3")}">{esc(s["status"])}'
            f'{"<br>" + esc(s["outcome"]) if s.get("outcome") else ""}</td></tr>' for s in w["scorecard"][:25])
        right = sum(1 for s in w["scorecard"] if s["status"] == "right")
        wrong = sum(1 for s in w["scorecard"] if s["status"] == "wrong")
        out.append(f'<h4 class="wh">Scorecard of dated calls</h4><p class="disc">Judged so far: {right} right, {wrong} wrong. '
                   f'Open calls are judged when their date passes.</p><table class="wtab">{trs}</table>')

    # 7. proposals
    if w["proposals"]:
        items = "".join(f'<li><b>{esc(x["label"])}</b>: cited by {len(x["people"])} people in {len(x["weeks"])} of the last 4 weeks. '
                        f'{esc(x["status"])}.</li>' for x in w["proposals"])
        out.append(f'<h4 class="wh">Proposed new dials (proposals only)</h4><ul class="wl">{items}</ul>')

    # 8. Coutts' levels
    lv = w.get("levels") or {}
    parts = []
    for q in lv.get("pending", []):
        parts.append(f'<li class="warnl">Waiting for your answer (id {esc(q["id"])}): {esc(q.get("key") or "a level")} '
                     f'{esc(q.get("level_text") or q.get("new"))}. {esc(q["reason"])}. {link(q.get("url"), "post")}</li>')
    for x in reversed(lv.get("log", [])[-5:]):
        old, new = f'{x.get("old") or 0:,.0f}', f'{x.get("new") or 0:,.0f}'
        parts.append(f'<li>{esc(x.get("time_utc", "")[:10])}: {esc(x.get("key"))} {esc(old)} → {esc(new)}, '
                     f'{esc(x.get("how"))}. {link(x.get("url"), "post")}</li>')
    if parts:
        out.append(f'<h4 class="wh">Coutts\' levels</h4><ul class="wl">{"".join(parts)}</ul>')

    r = w["run"]
    c = r["counts"]
    out.append(f'<p class="disc">Last sweep {esc(r["time_utc"])}: {r["records"]} records from {c["x_posts"]} X posts, '
               f'{c["episodes"]} podcast episodes, {c["videos"]} videos and {c["newsletter_posts"]} newsletter posts. '
               f'Cost ${r["cost_usd"]:.2f}; this month ${r["month_to_date_usd"]:.2f} of ${r["budget_usd"]:.0f}.'
               + (f' {r["waiting_for_gemini"]} YouTube-only videos wait for the Gemini key.' if not r.get("gemini_on") and r.get("waiting_for_gemini") else "")
               + "</p></section>")
    return "".join(out)


CSS = """
.wh{font-size:14px;margin:16px 0 6px;color:var(--ink)} .wt{margin-top:8px} .wt p{font-size:14px}
.wl{margin:4px 0;padding-left:18px;font-size:14px;color:#c9ced4} .wl li{margin:4px 0} .warnl{color:var(--amber)}
.wchip{font-size:15px;margin-right:3px} .wp{border-top:1px solid var(--line)}
.wp summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:1fr auto;gap:2px 10px;padding:8px 0;align-items:center}
.wn{font-weight:600;font-size:15px} .wc{white-space:nowrap} .wd{grid-column:1 / -1;font-size:12px;color:var(--mute)}
.wtab{font-size:12px} .wtab tr:first-child td{color:var(--mute);text-transform:uppercase;font-size:11px;letter-spacing:.04em}
"""
