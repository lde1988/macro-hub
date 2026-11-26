"""One-off, read-only check for the Phase 2 people list (reports/13).

Run on a GitHub runner, which can reach YouTube, Apple Podcasts and Substack.
It only reads public pages and feeds. It never follows anything written in them:
titles are printed as data, cut short, and nothing is acted on.
The optional X part uses XAI_API_KEY; the key is never printed.
"""
import datetime as dt
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; macro-hub people check)",
      "Accept-Language": "en-US,en;q=0.9"}
S = requests.Session()
S.headers.update(UA)
S.cookies.set("CONSENT", "YES+1", domain=".youtube.com")


def clean(t, n=70):
    return re.sub(r"[\s|]+", " ", str(t or ""))[:n]


def get(url, **kw):
    try:
        return S.get(url, timeout=25, **kw)
    except Exception as e:  # noqa: BLE001
        return type("R", (), {"status_code": f"error {type(e).__name__}", "text": "", "content": b"",
                              "json": lambda self: {}})()


def feed_items(xml_bytes):
    """Return (feed title, [(date, title)]) for RSS or Atom."""
    root = ET.fromstring(xml_bytes)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    if root.tag.endswith("rss"):
        ch = root.find("channel")
        title = ch.findtext("title")
        for it in ch.findall("item"):
            out.append((it.findtext("pubDate") or "", it.findtext("title")))
    else:
        title = root.findtext("a:title", namespaces=ns)
        for e in root.findall("a:entry", ns):
            out.append((e.findtext("a:published", namespaces=ns) or e.findtext("a:updated", namespaces=ns) or "",
                        e.findtext("a:title", namespaces=ns)))
    return title, out


def check_feed(label, url):
    r = get(url)
    if r.status_code != 200:
        return f"| {label} | {url} | NO ({r.status_code}) | | | |"
    try:
        title, items = feed_items(r.content)
    except Exception as e:  # noqa: BLE001
        return f"| {label} | {url} | NO (not a feed: {type(e).__name__}) | | | |"
    latest = items[0] if items else ("", "")
    return f"| {label} | {url} | yes | {clean(title, 40)} | {len(items)} | {clean(latest[0], 31)} · {clean(latest[1], 50)} |"


FEEDS = [
    ("Steno: Steno's Signals", "https://andreassteno.substack.com/feed"),
    ("Pal: Substack", "https://raoulpal.substack.com/feed"),
    ("Visser: VisserLabs", "https://visserlabs.substack.com/feed"),
    ("Andreessen: pmarca", "https://pmarca.substack.com/feed"),
    ("Alden: website", "https://www.lynalden.com/feed/"),
    ("Howell: Capital Wars", "https://capitalwars.substack.com/feed"),
    ("Follonier: The Shift", "https://theshiftwithkevin.substack.com/feed"),
    ("Diamandis: website", "https://www.diamandis.com/blog/rss.xml"),
    ("Diamandis: website alt", "https://www.diamandis.com/feed"),
    ("Mostaque: Intelligent Internet", "https://intelligentinternet.substack.com/feed"),
    ("Mostaque: personal Substack?", "https://emostaque.substack.com/feed"),
    ("Garg / Electric Capital", "https://electriccapital.substack.com/feed"),
    ("Kedrosky: Irregular Ideas", "https://skventures.substack.com/feed"),
    ("Kedrosky: personal", "https://paul.kedrosky.com/feed"),
    ("Kedrosky: Substack profile", "https://pkedrosky.substack.com/feed"),
    ("Coutts: Substack?", "https://jamiecoutts.substack.com/feed"),
    ("Bittel: Substack?", "https://julienbittel.substack.com/feed"),
    ("Yahya: a16z crypto posts", "https://a16zcrypto.com/feed/"),
    ("Rasmussen: Verdad", "https://verdadcap.com/archive?format=rss"),
    ("Rasmussen: Verdad alt", "https://www.verdadcap.com/feed"),
]

APPLE = [  # Apple Podcasts ids found by search; Apple's lookup gives the show's own RSS feed
    ("Steno + Rosenvold: Macro Mondays", 1693061907),
    ("Pal: The Journey Man", 1581019716),
    ("Andreessen: Ben & Marc Show", 1713388101),
    ("Follonier: When Shift Happens", 1596083462),
    ("Diamandis: Moonshots", 1648228034),
    ("Mostaque: Intelligent Internet", 1866952079),
    ("Kedrosky: Adjacency", 1538881758),
]
APPLE_SEARCH = ["Odd Lots", "The Pomp Podcast", "Invest Like the Best", "Forward Guidance", "Monetary Matters",
                "Real Vision Podcast", "Raoul Pal Real Vision Crypto", "Bankless", "Milk Road", "Lightspeed Blockworks",
                "Unchained Laura Shin", "The a16z Show", "Coin Stories Natalie Brunell", "Lyn Alden", "Steno Research",
                "Jamie Coutts", "Gavin Baker", "Mert Mumtaz", "Avichal Garg", "Michael Howell CrossBorder",
                "Druckenmiller", "Emad Mostaque", "Dan Rasmussen Verdad", "Paul Kedrosky"]

YOUTUBE = ["@RaoulPalTJM", "@RealVisionFinance", "@JordiVisserlabs", "@lynaldenmedia", "@peterdiamandis",
           "@WhenShiftHappens", "@a16z", "@AnthonyPompliano", "@ForwardGuidanceBW", "@MonetaryMatters",
           "@stenoresearch", "@MacroMondays", "@intelligentinternet", "@EmadMostaque", "@Bankless",
           "@MilkRoadDaily", "@Blockworks_", "@BloombergPodcasts", "@joincolossus", "@CrossBorderCapital",
           "@HeliusLabs", "@electriccapital", "@VerdadCapital", "@TheIndexPodcast"]
YT_IDS = ["UCvxm0qTrGN_1LMYgUaftWyQ"]


def yt_handle(h):
    r = get(f"https://www.youtube.com/{h}")
    if r.status_code != 200:
        return f"| {h} | NO ({r.status_code}) | | | |"
    m = re.search(r'"(?:externalId|channelId)":"(UC[\w-]{22})"', r.text)
    t = re.search(r'<meta property="og:title" content="([^"]*)"', r.text)
    if not m:
        return f"| {h} | page loaded, no channel id (consent or bot page?) | | | |"
    return yt_feed(h, m.group(1), t.group(1) if t else "")


def yt_feed(label, cid, title=""):
    r = get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}")
    if r.status_code != 200:
        return f"| {label} | {cid} | {clean(title, 40)} | feed NO ({r.status_code}) | |"
    ft, items = feed_items(r.content)
    last = items[0] if items else ("", "")
    return f"| {label} | {cid} | {clean(title or ft, 40)} | feed yes, {len(items)} videos | {clean(last[0], 10)} · {clean(last[1], 50)} |"


def apple(label, pid):
    r = get(f"https://itunes.apple.com/lookup?id={pid}&entity=podcast")
    try:
        res = r.json().get("results", [])
    except Exception:  # noqa: BLE001
        res = []
    if not res:
        return f"| {label} | {pid} | NO ({r.status_code}) | | |"
    x = res[0]
    feed = x.get("feedUrl", "")
    f = check_feed("", feed).split("|") if feed else []
    ok = f[3].strip() if len(f) > 3 else "no feed url"
    latest = f[6].strip() if len(f) > 6 else ""
    return f"| {label} | {clean(x.get('collectionName'), 40)} | {feed} | {ok} | {clean(x.get('releaseDate'), 10)} {latest} |"


def apple_search(term):
    r = get("https://itunes.apple.com/search", params={"term": term, "entity": "podcast", "limit": 3})
    try:
        res = r.json().get("results", [])
    except Exception:  # noqa: BLE001
        res = []
    if not res:
        return f"| {term} | none ({r.status_code}) | | |"
    return "\n".join(f"| {term} | {clean(x.get('collectionName'), 45)} · {clean(x.get('artistName'), 30)} | "
                     f"{x.get('feedUrl', '')} | {clean(x.get('releaseDate'), 10)} |" for x in res)


X_HANDLES = ["AndreasSteno", "RaoulGMI", "Jamie1Coutts", "BittelJulien", "jvisserlabs", "alive_eth", "0xMert_",
             "GavinSBaker", "pmarca", "LynAldenContact", "crossbordercap", "avichal", "KevinWSHPod",
             "PeterDiamandis", "EMostaque", "pkedrosky", "tracyalloway", "TheStalwart", "MikkelRosenvold",
             "KevinFollonier", "Druckenmiller", "0xMert"]


def x_check(model):
    """Ask Grok, with X search limited to the candidate handles, for each handle's latest post.
    Small and capped. Returns markdown and the cost reported by the API."""
    key = os.environ.get("XAI_API_KEY", "").strip()
    if not key:
        return "XAI_API_KEY not set: X part skipped.", 0.0
    lines, cost = [], 0.0
    since = (dt.date.today() - dt.timedelta(days=30)).isoformat()
    for i in range(0, len(X_HANDLES), 10):
        batch = X_HANDLES[i:i + 10]
        body = {
            "model": model,
            "input": [{"role": "user", "content":
                       "For each of these X accounts, report whether the account exists, its display name, its bio "
                       "in under 12 words, and the date and URL of its most recent post you can find. Return only JSON: "
                       '{"accounts":[{"handle":"","exists":true,"display_name":"","bio":"","latest_post_date":"","latest_post_url":""}]}. '
                       "Use null where unknown; never guess. Accounts: " + ", ".join("@" + h for h in batch)}],
            "tools": [{"type": "x_search", "allowed_x_handles": batch, "from_date": since}],
            "max_turns": 4,
        }
        try:
            r = requests.post("https://api.x.ai/v1/responses", json=body, timeout=180,
                              headers={"Authorization": f"Bearer {key}"})
        except Exception as e:  # noqa: BLE001
            lines.append(f"batch {i // 10 + 1}: error {type(e).__name__}")
            continue
        if r.status_code != 200:
            lines.append(f"batch {i // 10 + 1}: HTTP {r.status_code} {clean(r.text.replace(key, '***'), 300)}")
            continue
        j = r.json()
        u = j.get("usage", {})
        ticks = u.get("cost_in_usd_ticks")
        if ticks is not None:
            cost += ticks / 1e10
        lines.append(f"batch {i // 10 + 1} usage: {json.dumps({k: v for k, v in u.items() if not isinstance(v, dict)})[:400]}")
        lines.append(f"  tool usage: {json.dumps(u.get('server_side_tool_usage_details') or j.get('server_side_tool_usage') or {})[:300]}")
        text = ""
        for o in j.get("output", []):
            for c in o.get("content", []) or []:
                if c.get("type") == "output_text":
                    text += c.get("text", "")
        m = re.search(r"\{.*\}", text, re.S)
        try:
            for a in json.loads(m.group(0))["accounts"]:
                lines.append(f"| @{clean(a.get('handle'), 20)} | {a.get('exists')} | {clean(a.get('display_name'), 30)} | "
                             f"{clean(a.get('bio'), 60)} | {clean(a.get('latest_post_date'), 12)} | {clean(a.get('latest_post_url'), 70)} |")
        except Exception:  # noqa: BLE001
            lines.append("  could not read JSON: " + clean(text, 400))
    return "\n".join(lines), cost


DOCS = [("xAI pricing", "https://docs.x.ai/developers/pricing", r"grok|x.search|per 1k|per million|\$"),
        ("xAI X search tool", "https://docs.x.ai/developers/tools/x-search", r"allowed_x_handles|image|maximum|max|\$"),
        ("xAI models", "https://docs.x.ai/docs/models", r"grok-[\w.-]+|\$"),
        ("Gemini regions", "https://ai.google.dev/gemini-api/docs/available-regions", r"Hong Kong|Macao|China"),
        ("Gemini video", "https://ai.google.dev/gemini-api/docs/video-understanding", r"YouTube|free tier|hours"),
        ("Gemini pricing", "https://ai.google.dev/gemini-api/docs/pricing", r"Flash-Lite|Flash|audio|video|Free of charge")]


def docs():
    out = []
    for label, url, pat in DOCS:
        r = get(url)
        if r.status_code != 200:
            out.append(f"### {label}: {url} -> {r.status_code}")
            continue
        text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.S)
        text = re.sub(r"<[^>]+>", "\n", text)
        rows = [re.sub(r"\s+", " ", x).strip() for x in text.split("\n")]
        rows = [x for x in rows if x and re.search(pat, x, re.I) and len(x) < 220]
        seen = []
        for x in rows:
            if x not in seen:
                seen.append(x)
        out.append(f"### {label}: {url} (200)\n" + "\n".join("    " + x for x in seen[:60]))
    return out


def main():
    p = [f"# People check, {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC, on {os.environ.get('RUNNER_NAME', 'local')}", ""]
    p += ["## Newsletter and blog feeds", "", "| who | url | works? | feed title | items | latest |", "|---|---|---|---|---|---|"]
    p += [check_feed(a, b) for a, b in FEEDS]
    p += ["", "## Podcasts (Apple lookup gives the show's own feed)", "",
          "| who | show | feed | feed works? | latest |", "|---|---|---|---|---|"]
    p += [apple(a, b) for a, b in APPLE]
    p += ["", "## Podcast search (for shows and guest appearances)", "", "| term | show | feed | latest |", "|---|---|---|---|"]
    p += [apple_search(t) for t in APPLE_SEARCH]
    p += ["", "## YouTube channels", "", "| handle | channel id | title | feed | latest |", "|---|---|---|---|---|"]
    p += [yt_handle(h) for h in YOUTUBE] + [yt_feed(c, c) for c in YT_IDS]
    p += ["", "## Price and terms pages (lines matching keywords, as data)", ""] + docs()
    model = os.environ.get("XAI_MODEL", "grok-4.3")
    if "--x" in sys.argv:
        p += ["", f"## X handles (xAI {model}, X search limited to the handles, last 30 days)", "",
              "| handle | exists | name | bio | latest post | url |", "|---|---|---|---|---|---|"]
        txt, cost = x_check(model)
        p += [txt, "", f"Cost reported by xAI for this check: ${cost:.4f}"]
    print("\n".join(p))


if __name__ == "__main__":
    main()
