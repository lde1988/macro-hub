"""ntfy pushes. The topic name is a secret (anyone who knows it can read the
alerts), so it travels in the request body, never in a web address, and neither
the topic nor ntfy's reply is ever printed or stored.

    python -m hub.notify --test      send one test push (needs NTFY_TOPIC)
"""
import argparse
import os
import sys

import requests

from hub.util import scrub

URL = "https://ntfy.sh/"


def send(title, message, priority=3, tags=None, topic=None, post=None):
    """Send one push. Returns (ok, short reason). Never raises, never leaks the topic."""
    topic = (topic if topic is not None else os.environ.get("NTFY_TOPIC", "")).strip()
    if not topic:
        return False, "NTFY_TOPIC is not set"
    body = {"topic": topic, "title": title[:200], "message": message[:3500], "priority": int(min(max(priority, 1), 5))}
    if tags:
        body["tags"] = list(tags)
    try:
        r = (post or requests.post)(URL, json=body, timeout=30)
    except Exception as ex:
        return False, scrub(type(ex).__name__).replace(topic, "***")
    return (True, "sent") if r.status_code == 200 else (False, f"ntfy answered HTTP {r.status_code}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    if ap.parse_args().test:
        ok, why = send("macro-hub: test push",
                       "If you can read this on your iPhone, alerts are working. This is only a test: no market reading has changed.",
                       priority=3, tags=["white_check_mark"])
        print("test push:", why)
        sys.exit(0 if ok else 1)
