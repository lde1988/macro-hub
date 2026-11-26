"""Reading RSS / Atom feeds (newsletters, podcasts, YouTube channels). Feed text is untrusted data."""
import datetime as dt
import email.utils
import html
import re
import xml.etree.ElementTree as ET

ATOM = "{http://www.w3.org/2005/Atom}"
ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"
MEDIA = "{http://search.yahoo.com/mrss/}"
YT = "{http://www.youtube.com/xml/schemas/2015}"


def parse_date(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = email.utils.parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def parse_duration(s):
    """itunes:duration as seconds: '3600', '59:10' or '1:02:03'."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        parts = [float(p) for p in s.split(":")]
    except ValueError:
        return None
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return int(sec)


def plain_text(s):
    """HTML to plain text, for summarising only."""
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s or "")
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"[ \t\r\f\v]+", " ", re.sub(r"\n\s*\n+", "\n\n", s)).strip()


def items(xml_bytes):
    """Every entry as a dict: title, link, date, duration_s, audio_url, text, video_id."""
    root = ET.fromstring(xml_bytes)
    out = []
    if root.tag.endswith("rss") or root.find("channel") is not None:
        ch = root.find("channel")
        for it in ch.findall("item"):
            enc = it.find("enclosure")
            body = it.findtext(CONTENT + "encoded") or it.findtext("description") or ""
            out.append({
                "title": (it.findtext("title") or "").strip(),
                "link": (it.findtext("link") or "").strip(),
                "date": parse_date(it.findtext("pubDate")),
                "duration_s": parse_duration(it.findtext(ITUNES + "duration")),
                "audio_url": enc.get("url") if enc is not None and "audio" in (enc.get("type") or "audio") else None,
                "text": plain_text(body),
                "video_id": None,
            })
    else:
        for e in root.findall(ATOM + "entry"):
            link = e.find(ATOM + "link")
            grp = e.find(MEDIA + "group")
            desc = grp.findtext(MEDIA + "description") if grp is not None else ""
            out.append({
                "title": (e.findtext(ATOM + "title") or "").strip(),
                "link": link.get("href") if link is not None else "",
                "date": parse_date(e.findtext(ATOM + "published") or e.findtext(ATOM + "updated")),
                "duration_s": None,
                "audio_url": None,
                "text": plain_text(desc or e.findtext(ATOM + "content") or e.findtext(ATOM + "summary") or ""),
                "video_id": e.findtext(YT + "videoId"),
            })
    return out


def in_window(item, start, end):
    return item["date"] is not None and start <= item["date"] < end
