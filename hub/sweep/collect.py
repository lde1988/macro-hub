"""The collect step of the weekly sweep: read every source for the week, turn it into records.

    python -m hub.sweep.collect --data data --out sweepout [--now 2026-11-29T12:07:00Z]

It only READS the data branch (month-to-date spend, items already processed) and writes its results to
--out for the save step. Everything it fetches is untrusted data and is only ever summarised into records.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import tempfile
import time
import traceback
from pathlib import Path

import yaml

from hub.sweep import budget as budgetmod, discover, extract, feeds, gemini, newsletters, transcribe, xai
from hub.sweep.net import Fetch
from hub.util import ROOT, scrub, utcnow


def load_cfg(path=None):
    return yaml.safe_load(open(path or ROOT / "config" / "sweep.yaml"))


def rec_id(r):
    return hashlib.sha1(f'{r.get("url")}|{r.get("person_id")}|{r.get("quote")}'.encode()).hexdigest()[:16]


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()[:40]


def mmss(s):
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


class Run:
    def __init__(self, cfg, data, now, fetch=None, browser=None):
        self.cfg, self.data, self.now = cfg, Path(data), now
        self.end = now
        self.start = now - dt.timedelta(days=cfg.get("window_days", 7))
        self.model = cfg["models"]["xai"]
        month = now.strftime("%Y-%m")
        self.budget = budgetmod.Budget(cfg["budget"]["monthly_usd"], cfg["budget"]["stop_at_share"],
                                       budgetmod.month_to_date(self.data / "sweep" / "costs.csv", month))
        seen_p = self.data / "sweep" / "seen.json"
        self.seen = set(json.loads(seen_p.read_text())) if seen_p.exists() else set()
        self.polite, self.browser = fetch or Fetch(), browser or Fetch(browser=True)
        self.records, self.log, self.new_seen = [], [], set()
        self.counts = {"x_posts": 0, "audio_s": 0, "video_s": 0, "episodes": 0, "videos": 0, "newsletter_posts": 0}
        self.waiting_for_gemini = []
        self.people = {p["id"]: p for p in cfg["people"]}
        self.by_name = {p["name"]: p for p in cfg["people"]}
        extract.set_metric_keys(list(cfg["metrics"]))

    def note(self, msg):
        self.log.append(scrub(msg)[:400])

    def add(self, person, kind, source_name, title, date, url, recs, segs=None, video=False, quote_checked=True):
        for r in recs:
            q = self.by_name.get(r.get("speaker"), person)
            r.update({"person_id": q["id"], "person": q["name"], "source_type": kind, "source_name": source_name,
                      "title": title, "date": r.get("date") or (date.strftime("%Y-%m-%d") if date else None),
                      "quote_checked": quote_checked, "found_through": r.get("found_through")})
            r.setdefault("url", url)
            if segs:
                t = extract.locate(r["quote"], segs)
                r["timestamp_s"] = t
                if t is not None:
                    r["at"] = mmss(t)
                    if video:
                        r["url"] = f"{url}&t={int(t)}s"
            r["week_end"] = self.end.strftime("%Y-%m-%d")
            r["id"] = rec_id(r)
            self.records.append(r)

    def read(self, speakers, desc, text, said):
        if not self.budget.allow(0.02, f"reading {desc}"):
            return [], ["budget"]
        recs, dropped, c = extract.from_text(self.model, speakers, desc, text, said=said)
        self.budget.add("xai", c)
        return recs, dropped

    # ---------------------------------------------------------------- newsletters
    def do_newsletters(self):
        caps = self.cfg["caps"]
        for p in self.cfg["people"]:
            for url in p.get("newsletters", []):
                how, posts = newsletters.week_posts(self.polite, self.browser, url, self.start, self.end)
                quote_checked = True
                if posts is None:
                    if not self.budget.allow(0.10, f"web search for {url}"):
                        self.note(f"{p['name']}: {url} blocked ({how}); web-search fallback skipped (budget)")
                        continue
                    try:
                        posts, c = newsletters.via_web_search(self.model, url, self.start, self.end)
                        self.budget.add("xai", c)
                        how, quote_checked = f"{how}; read through xAI web search", False
                    except xai.XaiError as e:
                        self.note(f"{p['name']}: {url} blocked and web search failed: {e}")
                        continue
                self.note(f"{p['name']}: {url}: {how}, {len(posts)} posts this week")
                for i in posts[:caps["newsletter_posts_per_person"]]:
                    key = i.get("link") or i["title"]
                    if key in self.seen or len(i.get("text") or "") < 400:
                        continue
                    recs, dropped = self.read([p["name"]], f"newsletter post: {i['title']}", i["text"], i["date"].date())
                    self.add(p, "newsletter", url, i["title"], i["date"], i.get("link"), recs, quote_checked=quote_checked)
                    self.new_seen.add(key)
                    self.counts["newsletter_posts"] += 1

    # ---------------------------------------------------------------- podcasts
    def find_episodes(self):
        caps, found = self.cfg["caps"], {}
        for p in self.cfg["people"]:
            for url in p.get("podcasts", []):
                st, body = self.polite.get(url, max_bytes=30_000_000)
                if st != 200:
                    self.note(f"{p['name']}: podcast feed {url} failed: {st}")
                    continue
                try:
                    its = feeds.items(body)
                except Exception as e:  # noqa: BLE001
                    self.note(f"{p['name']}: podcast feed {url} unreadable: {type(e).__name__}")
                    continue
                for i in its:
                    if feeds.in_window(i, self.start, self.end) and (i["duration_s"] or 0) >= caps["min_minutes"] * 60 \
                            and i.get("audio_url"):
                        found.setdefault(i["audio_url"], (p, "own show", i.get("show") or url, i))
            if self.cfg.get("guest_search") and p.get("guest_search", True):
                st, eps = discover.apple_episodes(self.polite, p["name"], self.start, self.end)
                if st != 200:
                    self.note(f"{p['name']}: podcast directory search failed: {st}")
                for e in eps:
                    if (e["duration_s"] or 0) >= caps["min_minutes"] * 60 and e.get("audio_url"):
                        found.setdefault(e["audio_url"], (p, "name search", e["show"], e))
        return found

    def speakers_for(self, p, title):
        t = (title or "").lower()
        names = [q["name"] for q in self.cfg["people"] if q["name"].split()[-1].lower() in t and len(q["name"].split()) > 1]
        if "macro mondays" in t or "drinks with the danes" in t:
            names += ["Andreas Steno Larsen", "Mikkel Rosenvold"]
        return list(dict.fromkeys([p["name"]] + names))

    def do_podcasts(self):
        caps = self.cfg["caps"]
        cap_s, ep_cap = caps["video_hours"] * 3600, caps["episode_max_minutes"] * 60
        found = self.find_episodes()
        per_person, done_titles = {}, set()
        order = sorted(found.values(), key=lambda v: (v[1] != "own show", -(v[3]["date"].timestamp())))
        for p, how, show, e in order:
            key = e["audio_url"]
            if key in self.seen or per_person.get(p["id"], 0) >= caps["episodes_per_person"]:
                continue
            if norm_title(e["title"]) in done_titles:
                continue
            left = cap_s - self.counts["audio_s"] - self.counts["video_s"]
            if left < caps["min_minutes"] * 60:
                self.note(f"audio cap reached ({caps['video_hours']} h): {e['title'][:60]} left out")
                continue
            max_s = min(ep_cap, left, e["duration_s"] or ep_cap)
            est = max_s / 3600 * (self.cfg["prices"]["groq_usd_per_hour"] + self.cfg["prices"]["xai_usd_per_text_hour"])
            if not self.budget.allow(est, f"podcast {e['title'][:40]}"):
                continue
            try:
                with tempfile.TemporaryDirectory() as td:
                    src = Path(td) / "episode.audio"
                    st = self.browser.download(e["audio_url"], src)
                    if st != 200:
                        self.note(f"{p['name']}: download failed ({st}): {e['title'][:60]}")
                        continue
                    segs, billed, cost = transcribe.transcribe(src, Path(td) / "parts", self.cfg["models"]["groq_transcribe"], max_s)
                self.budget.add("groq", cost)
                self.counts["audio_s"] += billed
                self.counts["episodes"] += 1
                text = " ".join(s["text"] for s in segs)
                recs, dropped = self.read(self.speakers_for(p, e["title"]), f"podcast {show}: {e['title']} ({how})",
                                          text, e["date"].date())
                for r in recs:
                    r["found_through"] = how
                self.add(p, "podcast", show, e["title"], e["date"], e.get("link") or e["audio_url"], recs, segs=segs)
                self.new_seen.add(key)
                done_titles.add(norm_title(e["title"]))
                per_person[p["id"]] = per_person.get(p["id"], 0) + 1
                self.note(f"{p['name']}: podcast '{e['title'][:60]}' ({how}): {billed / 60:.0f} min, {len(recs)} records, "
                          f"{len(dropped)} dropped")
            except Exception as ex:  # noqa: BLE001
                self.note(f"{p['name']}: podcast '{e['title'][:60]}' failed: {type(ex).__name__}: {ex}")
        self.podcast_titles = done_titles

    # ---------------------------------------------------------------- YouTube (Gemini only)
    def do_videos(self):
        caps = self.cfg["caps"]
        vids = {}
        for p in self.cfg["people"]:
            for cid in p.get("youtube", []):
                st, body = self.polite.get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}")
                if st != 200:
                    self.note(f"{p['name']}: YouTube channel feed failed: {st}")
                    continue
                flt = p.get("youtube_title_filter")
                for i in feeds.items(body):
                    if feeds.in_window(i, self.start, self.end) and (not flt or flt.lower() in i["title"].lower()):
                        vids.setdefault(i["video_id"], (p, "own channel", cid, i))
            if self.cfg.get("guest_search") and p.get("guest_search", True):
                st, found = discover.youtube_search(self.browser, p["name"], self.now, self.cfg.get("youtube_guest_channels", []))
                if st != 200:
                    self.note(f"{p['name']}: YouTube search failed: {st}")
                for v in found:
                    vids.setdefault(v["video_id"], (p, "name search", v["channel"], v))
        on = gemini.available(self.cfg)
        for vid, (p, how, ch, v) in vids.items():
            url = f"https://www.youtube.com/watch?v={vid}"
            if url in self.seen or norm_title(v["title"]) in getattr(self, "podcast_titles", set()):
                continue                                  # already heard as a podcast
            if not on:
                self.waiting_for_gemini.append({"person": p["name"], "title": v["title"], "url": url, "how": how})
                continue
            length = v.get("duration_s") or discover.video_length(self.polite, vid)
            if not length or length < caps["min_minutes"] * 60:
                continue
            left = caps["video_hours"] * 3600 - self.counts["audio_s"] - self.counts["video_s"]
            take = min(length, caps["episode_max_minutes"] * 60, left)
            if take < caps["min_minutes"] * 60:
                self.note(f"video cap reached: {v['title'][:60]} left out")
                continue
            if not self.budget.allow(take / 3600 * self.cfg["prices"]["gemini_usd_per_video_hour"], f"video {v['title'][:40]}"):
                continue
            try:
                segs, cost = gemini.transcribe(url, self.cfg["models"]["gemini_video"])
                self.budget.add("gemini", cost)
                self.counts["video_s"] += length
                self.counts["videos"] += 1
                text = " ".join(s["text"] for s in segs)
                recs, dropped = self.read(self.speakers_for(p, v["title"]), f"video {ch}: {v['title']} ({how})", text,
                                          (v.get("date") or self.now).date())
                for r in recs:
                    r["found_through"] = how
                self.add(p, "video", ch, v["title"], v.get("date"), url, recs, segs=segs, video=True)
                self.new_seen.add(url)
            except Exception as ex:  # noqa: BLE001
                self.note(f"{p['name']}: video '{v['title'][:60]}' failed: {type(ex).__name__}: {ex}")

    # ---------------------------------------------------------------- X
    def do_x(self):
        caps = self.cfg["caps"]
        handles, owner = [], {}
        for p in self.cfg["people"]:
            xs = p.get("x")
            for h in ([xs] if isinstance(xs, str) else xs or []):
                handles.append(h)
                owner[h.lower()] = p
        n = caps["x_handles_per_call"]
        start_s = self.start.strftime("%Y-%m-%d")
        end_s = (self.end - dt.timedelta(seconds=1)).strftime("%Y-%m-%d")
        for i in range(0, len(handles), n):
            batch = handles[i:i + n]
            if self.counts["x_posts"] >= caps["x_posts"]:
                self.note(f"X post cap reached ({caps['x_posts']}); not searched: {', '.join('@' + h for h in batch)}")
                continue
            if not self.budget.allow(self.cfg["prices"]["xai_usd_per_x_call"], f"X {batch}"):
                continue
            try:
                recs, dropped, c, use = extract.from_x(self.model, batch, start_s, end_s, max_turns=caps["x_max_turns"])
            except xai.XaiError as e:
                self.note(f"X {batch}: failed: {e}")
                continue
            self.budget.add("xai", c)
            self.counts["x_posts"] += int(use.get("x_posts_fetched") or 0)
            for r in recs:
                if r["url"] in self.seen:
                    continue
                self.add(owner[r["handle"]], "x", "@" + r["handle"], "", None, r["url"], [r], quote_checked=False)
                self.new_seen.add(r["url"])
            self.note(f"X {', '.join('@' + h for h in batch)}: {len(recs)} records, {len(dropped)} dropped, "
                      f"{use.get('x_posts_fetched')} posts, ${c:.3f}")

    def run(self):
        for step in (self.do_x, self.do_newsletters, self.do_podcasts, self.do_videos):
            try:
                step()
            except Exception as ex:  # noqa: BLE001
                self.note(f"{step.__name__} stopped: {type(ex).__name__}: {ex} | {traceback.format_exc(limit=2)}")
        if self.budget.refused:
            self.note(f"left out to stay within the budget: {len(self.budget.refused)} items")
        return {"window": [self.start.isoformat(), self.end.isoformat()], "counts": self.counts,
                "costs": {**{k: round(v, 4) for k, v in self.budget.by.items()}, "total": round(self.budget.run_total, 4)},
                "month_before": round(self.budget.before, 4), "budget_refused": self.budget.refused[:50],
                "waiting_for_gemini": self.waiting_for_gemini[:60], "gemini_on": gemini.available(self.cfg),
                "log": self.log, "new_seen": sorted(self.new_seen), "records": len(self.records)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--now")
    a = ap.parse_args(argv)
    now = dt.datetime.fromisoformat(a.now.replace("Z", "+00:00")) if a.now else utcnow()
    run = Run(load_cfg(), a.data, now)
    t0 = time.time()
    summary = run.run()
    summary["seconds"] = round(time.time() - t0)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "records.jsonl", "w") as f:
        for r in run.records:
            f.write(json.dumps(r, default=str, ensure_ascii=False) + "\n")
    (out / "run.json").write_text(json.dumps(summary, indent=1, default=str))
    print(f"sweep collect: {len(run.records)} records, ${summary['costs']['total']:.3f}, {summary['seconds']} s")
    for line in run.log:
        print(" -", line)


if __name__ == "__main__":
    main()
