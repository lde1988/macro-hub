"""Turning podcast audio into text with Groq (paid, about $0.04 an audio hour). Key: GROQ_API_KEY, never printed."""
import os
import subprocess
from pathlib import Path

import requests

from hub.util import scrub

URL = "https://api.groq.com/openai/v1/audio/transcriptions"
USD_PER_HOUR = 0.04          # whisper-large-v3-turbo list price, checked at the source test
MIN_BILLED_S = 10            # Groq bills at least 10 seconds per request
CHUNK_S = 1200               # 20-minute pieces, about 5 MB each at 32 kbit/s


class TranscribeError(Exception):
    pass


def duration_s(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=False)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None


def split(path, workdir, max_s):
    """Mono 16 kHz 32 kbit/s pieces of CHUNK_S seconds, cut at max_s. Returns [(file, offset_s)]."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-t", str(int(max_s)), "-ac", "1", "-ar", "16000",
                    "-b:a", "32k", "-f", "segment", "-segment_time", str(CHUNK_S), str(workdir / "part%03d.mp3")],
                   check=True)
    parts = sorted(workdir.glob("part*.mp3"))
    return [(p, i * CHUNK_S) for i, p in enumerate(parts)]


def transcribe(path, workdir, model, max_s):
    """Return (segments [{start, end, text}], seconds billed, cost)."""
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        raise TranscribeError("GROQ_API_KEY is not set")
    segs, billed = [], 0.0
    for part, offset in split(path, workdir, max_s):
        d = duration_s(part) or 0
        billed += max(d, MIN_BILLED_S)
        with open(part, "rb") as f:
            try:
                r = requests.post(URL, headers={"Authorization": f"Bearer {key}"}, timeout=300,
                                  files={"file": (part.name, f, "audio/mpeg")},
                                  data={"model": model, "response_format": "verbose_json", "language": "en"})
            except Exception as e:  # noqa: BLE001
                raise TranscribeError(scrub(f"{type(e).__name__}: {e}")[:200]) from None
        if r.status_code != 200:
            raise TranscribeError(scrub(f"HTTP {r.status_code}: {r.text}")[:300])
        for s in r.json().get("segments", []):
            segs.append({"start": offset + s["start"], "end": offset + s["end"], "text": s["text"].strip()})
    return segs, billed, billed / 3600 * USD_PER_HOUR
