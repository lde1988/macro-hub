"""Small shared helpers: config loading, time, and a web session that never leaks secrets."""
import datetime as dt
import os
import re
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
SECRET_NAMES = ["FRED_API_KEY", "COINALYZE_API_KEY", "NTFY_TOPIC", "XAI_API_KEY", "GEMINI_API_KEY", "YOUTUBE_API_KEY", "GROQ_API_KEY"]


def utcnow():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def load_config(path=None):
    return load_yaml(path or ROOT / "config" / "thresholds.yaml")


def load_registry(path=None):
    reg = load_yaml(path or ROOT / "registry" / "series.yaml")
    ids = [s["id"] for s in reg["series"]]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate series ids in registry: {sorted(dupes)}")
    return reg


def scrub(text):
    """Remove any secret value from text before it is logged, stored or raised."""
    text = str(text)
    for name in SECRET_NAMES:
        val = os.environ.get(name, "").strip()
        if len(val) >= 4:
            text = text.replace(val, "***")
    return re.sub(r"(api_key=)[^&\s'\"]+", r"\1***", text)


class SourceError(Exception):
    """A source failed. The message is always scrubbed of secrets."""

    def __init__(self, msg):
        super().__init__(scrub(msg)[:300])


class Web:
    """requests wrapper: timeouts, a polite user agent, and scrubbed errors."""

    def __init__(self):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = "Mozilla/5.0 (compatible; macro-hub)"

    def get(self, url, ok=(200,), **kw):
        kw.setdefault("timeout", 45)
        try:
            r = self.s.get(url, **kw)
        except requests.RequestException as e:
            raise SourceError(f"{type(e).__name__} from {url.split('?')[0]}") from None
        if r.status_code not in ok:
            raise SourceError(f"HTTP {r.status_code} from {url.split('?')[0]}")
        return r
