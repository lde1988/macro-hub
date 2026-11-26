"""Web access for the sweep: browser-like headers, size limits, and errors scrubbed of secrets."""
import requests

from hub.util import scrub

BROWSER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/rss+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
POLITE = {"User-Agent": "Mozilla/5.0 (compatible; macro-hub weekly sweep)"}


class Fetch:
    def __init__(self, browser=False):
        self.s = requests.Session()
        self.s.headers.update(BROWSER if browser else POLITE)
        self.s.cookies.set("CONSENT", "YES+1", domain=".youtube.com")

    def get(self, url, timeout=30, max_bytes=5_000_000, **kw):
        """Return (status, bytes). Never raises; status is a number or a short error name."""
        try:
            with self.s.get(url, timeout=timeout, stream=True, **kw) as r:
                body = b""
                for chunk in r.iter_content(65536):
                    body += chunk
                    if len(body) > max_bytes:
                        break
                return r.status_code, body
        except Exception as e:  # noqa: BLE001
            return f"error {type(e).__name__}: {scrub(e)[:80]}", b""

    def download(self, url, path, max_bytes=400_000_000, timeout=120):
        try:
            with self.s.get(url, timeout=timeout, stream=True) as r:
                if r.status_code != 200:
                    return r.status_code
                n = 0
                with open(path, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        n += len(chunk)
                        if n > max_bytes:
                            return "too large"
                        f.write(chunk)
                return 200
        except Exception as e:  # noqa: BLE001
            return f"error {type(e).__name__}"
