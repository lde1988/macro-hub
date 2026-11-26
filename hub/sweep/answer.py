"""The owner's answer to a Coutts level question (Actions -> "Sweep: answer a level question").

    python -m hub.sweep.answer --data data --id ab12cd34 --answer yes [--value 72000] [--line break|reclaim]
"""
import argparse

from hub import notify
from hub.sweep import levels
from hub.util import load_config, utcnow

LINES = {"break": "btc_break", "reclaim": "btc_reclaim"}


def main(argv=None, sender=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--answer", required=True, choices=["yes", "no"])
    ap.add_argument("--value", default="")
    ap.add_argument("--line", default="", choices=["", "break", "reclaim"])
    a = ap.parse_args(argv)
    value = a.value.replace(",", "").replace("$", "").strip() or None
    ok, msg = levels.answer(a.data, load_config(), a.id.strip(), a.answer == "yes", utcnow(), value=value,
                            key=LINES.get(a.line))
    print(msg)
    (sender or notify.send)("macro-hub: level question answered" if ok else "macro-hub: level answer not applied",
                            msg, 3, ["pushpin"])
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
