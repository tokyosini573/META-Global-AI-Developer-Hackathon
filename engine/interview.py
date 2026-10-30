"""Ask one simulated person why: the live Meta model calls of the demo (scene 6).

The question is spoken into the drawer (Muse Voice Transcribe turns it into text) or typed, and
Muse Spark answers as that person, from their own record in the replay: who they are, what they
saw and what they did, day by day. The server reads the record from the committed replay; the
browser only sends which person and the question.

Spark standard is used (not contributor): a visitor's question is not sent where it may be used
for training. Both calls are small, and serve.py caps how many a visitor can make.
"""

import json
import uuid
import urllib.error
import urllib.request
from pathlib import Path

from engine.check_api import call

ROOT = Path(__file__).resolve().parent.parent
REPLAYS = ROOT / "web" / "public" / "replays"
MODEL = "muse-spark-1.3"
TRANSCRIBE = "muse-voice-transcribe-1.0"
MAX_QUESTION = 300

SYSTEM = (
    "You are one real person being interviewed about a dating app you tried. Stay in character and speak "
    "in the first person, the way this person talks: plain, casual, honest. Answer in two or three short "
    "sentences, like talking to a friend: say what you saw on the screen and how it felt, with one concrete "
    "detail from your life. Do not repeat your earlier thoughts word for word. Base every answer on your "
    "record below; do not invent events that are not in it. If you are asked about something unrelated, say "
    "so briefly in character. Never mention simulations, models or AI."
)


def person(replay, plan, pid):
    if not replay.isidentifier():   # a replay name, never a path
        raise ValueError(replay)
    data = json.loads((REPLAYS / f"{replay}.json").read_text())
    p = next(x for x in data["people"][plan] if x["id"] == pid)
    return data, p


def record(data, plan, p):
    """The person's record in words: who they are and what happened, as the drawer shows it."""
    s = p["story"]
    lines = [f"You are {p['name']}, {p['age']}, from {p['place']}."]
    if s.get("persona"):
        lines.append(s["persona"])
    lines.append(f"The dating app is {data['meta']['app']}. It launched with this plan: {data['plans'][plan]['summary']}.")
    lines.append("What happened to you:")
    for day, what, words in s["diary"]:
        lines.append(f"- Day {day}: {what}" + (f' What went through your head: "{words}"' if words else ""))
    return "\n".join(lines)


def answer(env, replay, plan, pid, question):
    question = question.strip()[:MAX_QUESTION]
    data, p = person(replay, plan, pid)
    body = {"model": MODEL, "reasoning_effort": "low", "max_tokens": 1500,
            "messages": [{"role": "system", "content": SYSTEM + "\n\n" + record(data, plan, p)},
                         {"role": "user", "content": question}]}
    status, out, _ = call(env, "POST", "/chat/completions", body)
    if status != 200:
        raise RuntimeError(f"Spark HTTP {status}")
    return out["choices"][0]["message"]["content"].strip().strip('"')


def transcribe(env, wav):
    """16-bit mono WAV (16 or 24 kHz) -> text, with the file endpoint of Muse Voice Transcribe."""
    boundary = uuid.uuid4().hex
    request = json.dumps({"model": TRANSCRIBE, "audioEncoding": "WAV", "language": "en"})
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="request"\r\nContent-Type: application/json\r\n\r\n'
        f"{request}\r\n".encode(),
        f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; filename="question.wav"\r\n'
        "Content-Type: audio/wav\r\n\r\n".encode() + wav + b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    req = urllib.request.Request(env["MODEL_API_BASE_URL"].rstrip("/") + "/asr/transcribe", data=b"".join(parts),
                                 method="POST", headers={"Authorization": f"Bearer {env['MODEL_API_KEY']}",
                                                         "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())["transcript"].strip()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Voice Transcribe HTTP {e.code}") from e
