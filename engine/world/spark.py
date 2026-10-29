"""Muse Spark as the decision provider: a persona looks at a rendered app screen.

Every decision key (person type x screen x state bucket) is asked a few times and the
answers are averaged. Answers are stored in a JSON table committed to the repo, so
reruns and Monte Carlo cost nothing and the demo survives without API credit.

Only fictional people and a fictional app are sent: the contributor model's inputs
may be used by Meta for training.
"""

import base64
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from engine.check_api import call, load_env

from . import screens
from .decide import OPTIONS, TYPE_BY_ID, TYPES

MODEL = "muse-spark-1.3-contributor"
EFFORT = "medium"          # spike: minimal/low were unstable, medium was stable and cheap
REPEATS = 3
PRICE = (0.10, 0.20)       # USD per 1M tokens (input, output) for the contributor model

SYSTEM = (
    "You simulate one specific real person looking at their phone. Stay in character. "
    "Real people are impatient, careful with money and quit apps easily; do not be more patient or rational "
    "than they would be. Base your answer on what is actually visible on the screen. "
    "Profile photos are hidden in this simulation as gray placeholders; do not judge people by them."
)

PERSONA = {
    "student": "You are a {age}-year-old college student. Money is tight and you almost never pay for apps.",
    "new_in_town": "You are {age} and moved to this city a few months ago for work. You know few people here.",
    "busy_professional": "You are {age}, work long hours and earn well. You have little free time and will pay "
                         "to save it.",
    "casual_browser": "You are {age} and open dating apps mostly out of boredom, without a clear goal.",
    "serious_dater": "You are {age} and want a real relationship. You are tired of apps that lead nowhere.",
    "app_skeptic": "You are {age}, distrust new apps and delete them quickly when they waste your time.",
}

INSTALL_CONTEXT = {
    "tiktok_ad": "You are scrolling TikTok at night and this ad for a new dating app appears. What do you do?",
    "ambassador": "A student ambassador for a new dating app stopped you near campus and showed you its store page "
                  "on their phone. What do you do?",
    "friend": "A friend who recently matched with someone on this new dating app sent you this link. What do you do?",
}
WEEK = {"w1": "You installed Kindred 3 days ago.", "w2-4": "You installed Kindred about two weeks ago.",
        "w5+": "You installed Kindred over a month ago."}
MATCHED = {"no": "You have no matches yet.", "yes": "You have matched with someone on it."}
NEARBY = {"none": "Almost everyone it shows you is far away.", "few": "It shows you a handful of people in your area.",
          "many": "It keeps showing you people close by."}

TABLE = Path(__file__).resolve().parent.parent.parent / "data" / "decisions" / "kindred_spark.json"


def all_keys():
    for t in TYPES:
        for screen in INSTALL_CONTEXT:
            yield ("install", t["id"], screen, "-")
        for matched in MATCHED:
            for nearby in NEARBY:
                for week in WEEK:
                    yield ("paywall", t["id"], "paywall", (matched, nearby, week))


def _persona(type_id):
    lo, hi = TYPE_BY_ID[type_id]["age"]
    return PERSONA[type_id].format(age=(lo + hi) // 2)


def _prompt(kind, type_id, screen, bucket):
    """(persona, image name, question) for one decision key."""
    if kind == "install":
        return _persona(type_id), screens.install_screen(screen), INSTALL_CONTEXT[screen]
    matched, nearby, week = bucket
    history = " ".join([WEEK[week], MATCHED[matched], NEARBY[nearby]])
    return (_persona(type_id) + " " + history, screens.paywall_screen(bucket),
            "This is what Kindred shows you right now. What do you do?")


def _schema(actions):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["noticed", "probabilities", "reason"],
        "properties": {
            "noticed": {"type": "string", "description": "The one thing on the screen that matters most to you."},
            "probabilities": {
                "type": "object", "additionalProperties": False, "required": list(actions),
                "properties": {a: {"type": "number", "minimum": 0, "maximum": 1} for a in actions},
                "description": "How likely you are to do each action. Must sum to 1.",
            },
            "reason": {"type": "string", "description": "One short sentence in your own voice, under 15 words."},
        },
    }


def _image(name):
    return "data:image/png;base64," + base64.b64encode(screens.path(name).read_bytes()).decode()


def request_body(persona, image, question, actions):
    return {
        "model": MODEL, "reasoning_effort": EFFORT, "max_tokens": 6000,
        "messages": [
            {"role": "system", "content": SYSTEM + "\n\n" + persona},
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": _image(image)}},
                                         {"type": "text", "text": question}]},
        ],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "decision", "strict": True, "schema": _schema(actions)}},
    }


def ask_once(env, key):
    kind, type_id, screen, bucket = key
    persona, image, question = _prompt(kind, type_id, screen, bucket)
    return ask_body(env, request_body(persona, image, question, OPTIONS[kind]), key)


def ask_body(env, body, key):
    for attempt in range(4):
        try:
            status, data, _ = call(env, "POST", "/chat/completions", body)
        except OSError:              # read timeout or dropped connection: retry
            status, data = None, None
        if status == 200:
            try:
                answer = json.loads(data["choices"][0]["message"]["content"])
                usage = data.get("usage", {})
                cost = (usage.get("prompt_tokens", 0) * PRICE[0] + usage.get("completion_tokens", 0) * PRICE[1]) / 1e6
                return answer, cost
            except (KeyError, TypeError, ValueError):
                pass
        time.sleep(2 ** attempt * (5 if status == 429 else 1))
    raise RuntimeError(f"no answer for {key}: HTTP {status}")


def _average(answers, actions):
    probs = {a: statistics.mean(x["probabilities"][a] for x in answers) for a in actions}
    total = sum(probs.values()) or 1
    return {a: v / total for a, v in probs.items()}


def _key_str(key):
    return json.dumps([key[0], key[1], key[2], list(key[3]) if isinstance(key[3], tuple) else key[3]])


class SparkProvider:
    name = "spark"

    def __init__(self, table=TABLE):
        self.path = table
        self.entries = json.loads(table.read_text())["entries"] if table.exists() else {}
        self.env = None

    def decide(self, kind, type_id, screen, bucket):
        key = (kind, type_id, screen, bucket)
        k = _key_str(key)
        if k not in self.entries:
            self.prefill([key])
        return self.entries[k]["probs"]

    def prefill(self, keys=None, workers=24):
        """Ask every missing key REPEATS times in parallel and save the table."""
        todo = [k for k in (keys or list(all_keys())) if _key_str(k) not in self.entries]
        if not todo:
            return 0.0
        self.env = self.env or load_env()
        jobs = [k for k in todo for _ in range(REPEATS)]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(lambda k: ask_once(self.env, k), jobs))
        cost = 0.0
        for i, key in enumerate(todo):
            answers = [results[i * REPEATS + j][0] for j in range(REPEATS)]
            cost += sum(results[i * REPEATS + j][1] for j in range(REPEATS))
            self.entries[_key_str(key)] = {
                "probs": _average(answers, OPTIONS[key[0]]),
                "samples": [a["probabilities"] for a in answers],
                "reasons": [a["reason"] for a in answers],
                "noticed": [a["noticed"] for a in answers],
            }
        self.save()
        return cost

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"model": MODEL, "reasoning_effort": EFFORT, "repeats": REPEATS,
                                         "entries": dict(sorted(self.entries.items()))}, indent=1))


if __name__ == "__main__":
    import sys
    p = SparkProvider()
    keys = list(all_keys())
    if "--sample" in sys.argv:
        keys = [keys[0], keys[3]]
    t0 = time.time()
    cost = p.prefill(keys)
    print(f"{len(p.entries)} keys in the table · this run ${cost:.4f} · {time.time() - t0:.0f}s -> {p.path}")
