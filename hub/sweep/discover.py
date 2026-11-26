"""Finding guest appearances by name: Apple's podcast directory and YouTube search. Results are untrusted data."""
import datetime as dt
import json
import re
import urllib.parse

from hub.sweep.feeds import parse_date


def apple_episodes(fetch, name, start, end, limit=50):
    """Podcast episodes from the last week whose title or description names the person."""
    url = "https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": name, "entity": "podcastEpisode", "limit": limit, "country": "US"})
    status, body = fetch.get(url)
    if status != 200:
        return status, []
    try:
        res = json.loads(body).get("results", [])
    except ValueError:
        return "not JSON", []
    surname = name.split()[-1].lower()
    out = []
    for r in res:
        d = parse_date(r.get("releaseDate"))
        text = f"{r.get('trackName', '')} {r.get('description', '')}".lower()
        if d is None or not (start <= d < end) or surname not in text:
            continue
        out.append({"title": r.get("trackName", ""), "show": r.get("collectionName", ""),
                    "date": d, "duration_s": (r.get("trackTimeMillis") or 0) // 1000 or None,
                    "audio_url": r.get("episodeUrl"), "link": r.get("trackViewUrl", ""),
                    "feed": r.get("feedUrl", ""), "text": r.get("description", "")})
    return 200, out


_AGO = re.compile(r"(\d+)\s+(minute|hour|day|week)s?\s+ago")


def _length_s(t):
    parts = [int(p) for p in re.findall(r"\d+", t or "")]
    s = 0
    for p in parts:
        s = s * 60 + p
    return s or None


def youtube_search(fetch, name, now, channels=None):
    """Videos uploaded this week whose title has the person's full name (YouTube's 'this week' filter).
    With `channels`, only videos from those channel names are kept: YouTube is full of re-upload and
    clickbait channels that put famous names on clips and made-up quotes."""
    url = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": name, "sp": "EgIIAw=="})
    status, body = fetch.get(url, max_bytes=8_000_000)
    if status != 200:
        return status, []
    m = re.search(rb"var ytInitialData = (\{.*?\});</script>", body, re.S)
    if not m:
        return "no results block (consent or bot page)", []
    try:
        data = json.loads(m.group(1))
    except ValueError:
        return "results block unreadable", []
    found = []

    def walk(x):
        if isinstance(x, dict):
            if "videoRenderer" in x:
                found.append(x["videoRenderer"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(data)
    full = name.lower()
    allowed = {c.lower() for c in channels} if channels is not None else None
    out = []
    for v in found:
        title = "".join(r.get("text", "") for r in v.get("title", {}).get("runs", []))
        channel = "".join(r.get("text", "") for r in v.get("ownerText", {}).get("runs", []))
        if full not in title.lower():
            continue
        if allowed is not None and not any(channel.lower().startswith(a) for a in allowed):
            continue
        ago = (v.get("publishedTimeText") or {}).get("simpleText", "")
        a = _AGO.search(ago)
        date = None
        if a:
            n, unit = int(a.group(1)), a.group(2)
            date = now - dt.timedelta(**{unit + "s": n})
        out.append({"video_id": v.get("videoId"), "title": title,
                    "channel": channel,
                    "duration_s": _length_s((v.get("lengthText") or {}).get("simpleText")),
                    "date": date, "link": f"https://www.youtube.com/watch?v={v.get('videoId')}"})
    return 200, out
