"""Phase 2, point 2: source test on one real week. Run on a GitHub runner (see sweep-source-test.yml).

Reads every source for every person for one week, tries each way of getting the words, turns a capped
sample into records, and writes a report table plus every record. Spends a little on xAI and Groq
(hard stop at TEST_BUDGET). All fetched text is untrusted data and is only ever summarised.
"""
import datetime as dt
import json
import os
import re
import sys
import tempfile
import traceback
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hub.sweep import discover, extract, feeds, transcribe, xai  # noqa: E402
from hub.sweep.net import Fetch  # noqa: E402

TEST_BUDGET = 6.00          # dollars: no further paid work once spent reaches this
AUDIO_CAP_S = 3 * 3600      # transcribe at most 3 hours in this test
EPISODE_CAP_S = 90 * 60     # and at most 90 minutes of any one episode
MAX_TRANSCRIBE = 3
MAX_NEWSLETTER_POSTS = 5

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
END = dt.datetime(2026, 11, 26, tzinfo=dt.timezone.utc)
START = END - dt.timedelta(days=7)
NOW = dt.datetime.now(dt.timezone.utc)

cfg = yaml.safe_load(open(ROOT / "config" / "sweep.yaml"))
MODEL = cfg["models"]["xai"]
spent = {"xai": 0.0, "groq": 0.0}
lines, records, notes = [], [], []
polite, browser = Fetch(), Fetch(browser=True)


def total():
    return sum(spent.values())


def clip(s, n=70):
    return re.sub(r"[\s|]+", " ", str(s or ""))[:n]


def fmt_d(d):
    return d.strftime("%Y-%m-%d") if d else "?"


def mmss(s):
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def add(person, source_type, source_name, title, date, url, recs, ts_segments=None, video=False):
    for r in recs:
        r.update({"person_id": person["id"], "person": person["name"], "source_type": source_type,
                  "source_name": source_name, "title": title, "date": r.get("date") or fmt_d(date)})
        r.setdefault("url", url)
        if ts_segments:
            t = extract.locate(r["quote"], ts_segments)
            r["timestamp_s"] = t
            if t is not None:
                r["at"] = mmss(t)
                if video:
                    r["url"] = f"{url}&t={int(t)}s"
        records.append(r)


# ---------- 1. Newsletters and blogs ----------
def substack_archive(feed_url):
    base = feed_url.rsplit("/feed", 1)[0]
    st, body = browser.get(base + "/api/v1/archive?sort=new&limit=12")
    if st != 200:
        return st, []
    try:
        posts = json.loads(body)
    except ValueError:
        return "not JSON", []
    out = []
    for p in posts:
        d = feeds.parse_date(p.get("post_date"))
        text = ""
        if d and START <= d < END and p.get("slug"):
            st2, b2 = browser.get(f"{base}/api/v1/posts/{p['slug']}")
            if st2 == 200:
                try:
                    j = json.loads(b2)
                    text = feeds.plain_text(j.get("body_html") or j.get("truncated_body_text") or "")
                except ValueError:
                    pass
        out.append({"title": p.get("title", ""), "link": p.get("canonical_url", ""), "date": d,
                    "text": text or p.get("description", ""), "paid": p.get("audience") not in (None, "everyone")})
    return 200, out


newsletter_items = []
lines += ["## 1. Newsletters and blogs", "",
          "| Person | Feed | Plain request | Browser-like request | Substack archive | Posts this week | Note |",
          "|---|---|---|---|---|---|---|"]
for p in cfg["people"]:
    for url in p.get("newsletters", []):
        s1, b1 = polite.get(url)
        s2, b2 = (s1, b1) if s1 == 200 else browser.get(url)
        s3, arch = ("not tried", [])
        its, note = [], ""
        body = b1 if s1 == 200 else b2 if s2 == 200 else None
        if body:
            try:
                its = feeds.items(body)
            except Exception as e:  # noqa: BLE001
                note = f"not a feed ({type(e).__name__})"
        if not body and "substack.com" in url:
            s3, arch = substack_archive(url)
            its = arch
        week = [i for i in its if i["date"] and START <= i["date"] < END]
        latest = max((i["date"] for i in its if i["date"]), default=None)
        note = note or (f"latest {fmt_d(latest)}" if its else "")
        if any(i.get("paid") for i in week):
            note += "; some posts paid (summary only)"
        lines.append(f"| {p['name']} | {url} | {s1} | {s2 if s1 != 200 else '-'} | {s3} | {len(week)} | {note} |")
        for i in week:
            newsletter_items.append((p, url, i))

# ---------- 2. Podcasts: own feeds and guest appearances ----------
episodes = {}
lines += ["", "## 2. Podcasts this week (10 minutes or longer)", "",
          "| Person | Found through | Show | Episode | Date | Length | Audio file? |", "|---|---|---|---|---|---|---|"]
for p in cfg["people"]:
    for url in p.get("podcasts", []):
        st, body = polite.get(url, max_bytes=30_000_000)
        if st != 200:
            lines.append(f"| {p['name']} | own feed | {url} | feed failed: {st} | | | |")
            continue
        for i in feeds.items(body):
            if feeds.in_window(i, START, END) and (i["duration_s"] or 0) >= cfg["caps"]["min_minutes"] * 60:
                episodes.setdefault(i["audio_url"] or i["link"], (p, "own feed", url, i))
    if p["id"] in ("oddlots",):
        continue
    st, eps = discover.apple_episodes(polite, p["name"], START, END)
    if st != 200:
        notes.append(f"Apple episode search failed for {p['name']}: {st}")
    for e in eps:
        if (e["duration_s"] or 0) >= cfg["caps"]["min_minutes"] * 60:
            episodes.setdefault(e["audio_url"] or e["link"], (p, "name search", e["show"], e))
for key, (p, how, show, e) in sorted(episodes.items(), key=lambda kv: (kv[1][0]["name"], kv[1][3]["date"])):
    lines.append(f"| {p['name']} | {how} | {clip(show if how == 'name search' else '', 40)} | {clip(e['title'], 60)} | "
                 f"{fmt_d(e['date'])} | {mmss(e['duration_s']) if e['duration_s'] else '?'} | {'yes' if e.get('audio_url') else 'no'} |")

# ---------- 3. YouTube: own channels and name search ----------
videos = {}
lines += ["", "## 3. YouTube this week", "",
          "| Person | Found through | Channel | Video | Date | Length |", "|---|---|---|---|---|---|"]
for p in cfg["people"]:
    for cid in p.get("youtube", []):
        st, body = polite.get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}")
        if st != 200:
            lines.append(f"| {p['name']} | own channel | {cid} | feed failed: {st} | | |")
            continue
        for i in feeds.items(body):
            flt = p.get("youtube_title_filter")
            if feeds.in_window(i, START, END) and (not flt or flt.lower() in i["title"].lower()):
                videos.setdefault(i["video_id"], (p, "own channel", cid, {**i, "channel": cid}))
    if p["id"] in ("oddlots",):
        continue
    st, vids = discover.youtube_search(browser, p["name"], NOW)
    if st != 200:
        notes.append(f"YouTube search for {p['name']}: {st}")
    for v in vids:
        if (v["duration_s"] or 0) >= cfg["caps"]["min_minutes"] * 60:
            videos.setdefault(v["video_id"], (p, "name search", v["channel"], v))
for vid, (p, how, ch, v) in sorted(videos.items(), key=lambda kv: kv[1][0]["name"]):
    lines.append(f"| {p['name']} | {how} | {clip(v.get('channel') or ch, 30)} | {clip(v['title'], 60)} | "
                 f"{fmt_d(v.get('date'))} | {mmss(v['duration_s']) if v.get('duration_s') else '? (feed gives none)'} |")

# ---------- 4. Getting the words from video ----------
lines += ["", "## 4. Getting the words from YouTube, tried from this runner", ""]
cap_rows = []
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    for vid in list(videos)[:3]:
        try:
            t = api.fetch(vid, languages=["en"])
            cap_rows.append(f"- Captions for {vid}: **worked**, {len(list(t))} lines")
        except Exception as e:  # noqa: BLE001
            cap_rows.append(f"- Captions for {vid}: **failed**: {type(e).__name__}: {clip(e, 160)}")
except Exception as e:  # noqa: BLE001
    cap_rows.append(f"- Captions library failed to load: {type(e).__name__}")
if videos:
    import subprocess
    vid = list(videos)[0]
    r = subprocess.run(["yt-dlp", "--no-warnings", "-f", "bestaudio", "--get-url",
                        f"https://www.youtube.com/watch?v={vid}"], capture_output=True, text=True, timeout=120)
    cap_rows.append(f"- Audio download (yt-dlp) for {vid}: " +
                    ("**worked**" if r.returncode == 0 else f"**failed**: {clip(r.stderr, 200)}"))
cap_rows.append(f"- Gemini reading the YouTube link: **switched off** until GEMINI_API_KEY exists "
                f"(set now: {'yes' if os.environ.get('GEMINI_API_KEY') else 'no'})")
lines += cap_rows

# ---------- 5. Paid transcription of podcast audio (Groq) ----------
lines += ["", "## 5. Podcast audio transcribed by Groq (capped sample)", "",
          "| Person | Episode | Minutes transcribed | Cost | Records kept | Dropped |", "|---|---|---|---|---|---|"]
picked, used_s = [], 0
by_person = {}
for key, (p, how, show, e) in episodes.items():
    if e.get("audio_url") and p["id"] not in by_person:
        by_person[p["id"]] = (p, how, show, e)
preferred = ["steno", "pal", "oddlots", "kedrosky", "howell", "alden", "diamandis", "follonier"]
for pid in preferred + list(by_person):
    if pid in by_person and by_person[pid] not in picked and len(picked) < MAX_TRANSCRIBE:
        picked.append(by_person[pid])
for p, how, show, e in picked:
    if total() >= TEST_BUDGET or used_s >= AUDIO_CAP_S:
        break
    max_s = min(EPISODE_CAP_S, AUDIO_CAP_S - used_s)
    try:
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "episode.audio"
            st = browser.download(e["audio_url"], src)
            if st != 200:
                lines.append(f"| {p['name']} | {clip(e['title'], 50)} | download failed: {st} | | | |")
                continue
            segs, billed, cost = transcribe.transcribe(src, Path(td) / "parts", cfg["models"]["groq_transcribe"], max_s)
        spent["groq"] += cost
        used_s += billed
        text = "\n".join(f"[{mmss(s['start'])}] {s['text']}" for s in segs)
        recs, dropped, c2 = extract.from_text(MODEL, p["name"], f"podcast {show}: {e['title']} ({how})", text)
        spent["xai"] += c2
        add(p, "podcast", show if how == "name search" else e.get("title", ""), e["title"], e["date"],
            e.get("link") or e["audio_url"], recs, ts_segments=segs)
        lines.append(f"| {p['name']} | {clip(e['title'], 50)} | {billed / 60:.0f} | ${cost:.3f} + ${c2:.3f} reading | "
                     f"{len(recs)} | {len(dropped)} {('(' + ', '.join(sorted(set(dropped))) + ')') if dropped else ''} |")
    except Exception as ex:  # noqa: BLE001
        lines.append(f"| {p['name']} | {clip(e['title'], 50)} | failed: {type(ex).__name__}: {clip(ex, 120)} | | | |")

# ---------- 6. Newsletter posts into records ----------
lines += ["", "## 6. Newsletter posts turned into records", "",
          "| Person | Post | Date | Records kept | Dropped |", "|---|---|---|---|---|"]
for p, url, i in newsletter_items[:MAX_NEWSLETTER_POSTS]:
    if total() >= TEST_BUDGET or len(i.get("text") or "") < 400:
        lines.append(f"| {p['name']} | {clip(i['title'], 50)} | {fmt_d(i['date'])} | skipped (too short or budget) | |")
        continue
    try:
        recs, dropped, c = extract.from_text(MODEL, p["name"], f"newsletter post: {i['title']}", i["text"])
        spent["xai"] += c
        add(p, "newsletter", url, i["title"], i["date"], i["link"], recs)
        lines.append(f"| {p['name']} | {clip(i['title'], 50)} | {fmt_d(i['date'])} | {len(recs)} | {len(dropped)} |")
    except Exception as ex:  # noqa: BLE001
        lines.append(f"| {p['name']} | {clip(i['title'], 50)} | failed: {clip(ex, 120)} | | |")

# ---------- 7. X ----------
lines += ["", "## 7. X, limited to the listed handles, images read", ""]
handles, owner = [], {}
for p in cfg["people"]:
    xs = p.get("x")
    for h in ([xs] if isinstance(xs, str) else xs or []):
        handles.append(h)
        owner[h.lower()] = p
handles.append("mert")      # candidate for Mert Mumtaz, checked below; records kept only if confirmed
owner["mert"] = {"id": "mumtaz", "name": "Mert Mumtaz (candidate @mert)"}
batches = [handles[:10], handles[10:20]]
for b in batches:
    if total() >= TEST_BUDGET or not b:
        continue
    try:
        recs, dropped, c, use = extract.from_x(MODEL, b, START.strftime("%Y-%m-%d"),
                                               (END - dt.timedelta(days=1)).strftime("%Y-%m-%d"))
        spent["xai"] += c
        for r in recs:
            p = owner.get(r["handle"])
            add(p, "x", "@" + r["handle"], "", None, r["url"], [r])
        lines.append(f"- Batch {', '.join('@' + h for h in b)}: {len(recs)} records kept, {len(dropped)} dropped "
                     f"{sorted(set(dropped)) if dropped else ''}; cost ${c:.3f}; usage {json.dumps(use)}")
    except Exception as ex:  # noqa: BLE001
        lines.append(f"- Batch {b}: failed: {clip(ex, 200)}")

# Who are Ali Yahya and Mert Mumtaz on X now?
if total() < TEST_BUDGET:
    q = ("Find the current X (Twitter) accounts of (1) Ali Yahya, who was a general partner at a16z crypto until "
         "October 2026, and (2) Mert Mumtaz, CEO of Helius (Solana). For each give the handle, display name, bio and "
         "the date and URL of one recent post. Say 'not found' rather than guess.")
    try:
        j, c, text = xai.call({"model": MODEL, "max_turns": 4, "input": [{"role": "user", "content": q}],
                               "tools": [{"type": "x_search"}]})
        spent["xai"] += c
        lines += ["", "### Handle search: Ali Yahya and Mert Mumtaz (cost ${:.3f})".format(c), "",
                  "> " + clip(text, 1500).replace("\n", " ")]
    except Exception as ex:  # noqa: BLE001
        lines.append(f"Handle search failed: {clip(ex, 200)}")

# ---------- write ----------
head = [f"# Source test, week {START:%d %b} to {(END - dt.timedelta(days=1)):%d %b %Y}",
        f"Run {NOW:%Y-%m-%d %H:%M} UTC on {os.environ.get('RUNNER_NAME', 'local')}. Model {MODEL}.", "",
        f"**Spent: xAI ${spent['xai']:.3f}, Groq ${spent['groq']:.3f}, total ${total():.3f}** (test cap ${TEST_BUDGET:.2f}).",
        f"Records: {len(records)} ({', '.join(f'{k} {sum(1 for r in records if r['source_type'] == k)}' for k in ('x', 'newsletter', 'podcast', 'video'))}).",
        ""]
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "source_test.md").write_text("\n".join(head + lines + ["", "## Notes", ""] + [f"- {n}" for n in notes]) + "\n")
with open(OUT / "records.jsonl", "w") as f:
    for r in records:
        f.write(json.dumps(r, default=str, ensure_ascii=False) + "\n")
print("\n".join(head))
