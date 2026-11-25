"""ntfy pushes, with a fake sender. Nothing is sent."""
from hub import notify


class Reply:
    def __init__(self, code):
        self.status_code = code
        self.text = '{"topic":"my-secret-topic"}'


def test_push_carries_title_message_and_priority_in_the_body():
    seen = {}

    def post(url, json, timeout):
        seen.update(url=url, **json)
        return Reply(200)
    ok, why = notify.send("Reading changed", "Hold to Buy (staged)", priority=5, tags=["warning"], topic="my-secret-topic", post=post)
    assert ok and why == "sent"
    assert seen["url"] == "https://ntfy.sh/" and "my-secret-topic" not in seen["url"]     # topic never in the address
    assert seen["topic"] == "my-secret-topic" and seen["priority"] == 5 and seen["title"] == "Reading changed"


def test_failed_push_reports_without_leaking_the_topic(capsys):
    def boom(url, json, timeout):
        raise RuntimeError("connection to ntfy.sh/my-secret-topic failed")
    ok, why = notify.send("t", "m", topic="my-secret-topic", post=boom)
    assert not ok and "my-secret-topic" not in why
    ok, why = notify.send("t", "m", topic="my-secret-topic", post=lambda url, json, timeout: Reply(429))
    assert not ok and why == "ntfy answered HTTP 429" and "my-secret-topic" not in capsys.readouterr().out


def test_no_topic_means_no_push(monkeypatch):
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    assert notify.send("t", "m") == (False, "NTFY_TOPIC is not set")


def test_priority_is_kept_within_ntfy_range():
    seen = {}
    notify.send("t", "m", priority=9, topic="x", post=lambda url, json, timeout: seen.update(json) or Reply(200))
    assert seen["priority"] == 5
