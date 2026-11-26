"""xAI calls (Responses API). The key comes from XAI_API_KEY and is never printed, logged or stored."""
import json
import os

import requests

from hub.util import scrub

URL = "https://api.x.ai/v1/responses"


class XaiError(Exception):
    pass


def call(body, timeout=300):
    """Return (parsed JSON, cost in USD as reported by xAI, the text output)."""
    key = os.environ.get("XAI_API_KEY", "").strip()
    if not key:
        raise XaiError("XAI_API_KEY is not set")
    try:
        r = requests.post(URL, json=body, timeout=timeout, headers={"Authorization": f"Bearer {key}"})
    except Exception as e:  # noqa: BLE001
        raise XaiError(scrub(f"{type(e).__name__}: {e}")[:200]) from None
    if r.status_code != 200:
        raise XaiError(scrub(f"HTTP {r.status_code}: {r.text}")[:300])
    j = r.json()
    cost = ((j.get("usage") or {}).get("cost_in_usd_ticks") or 0) / 1e10
    text = "".join(c.get("text", "") for o in j.get("output", []) for c in (o.get("content") or [])
                   if c.get("type") == "output_text")
    return j, cost, text


def usage_line(j):
    u = j.get("usage") or {}
    d = u.get("server_side_tool_usage_details") or {}
    return {"input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),
            "x_search_calls": d.get("x_search_calls"), "x_posts_fetched": d.get("x_posts_fetched"),
            "x_users_fetched": d.get("x_users_fetched"), "web_search_calls": d.get("web_search_calls")}


def first_json(text):
    """The first JSON object in the model's answer, or None."""
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except ValueError:
                        break
        start = text.find("{", start + 1)
    return None
