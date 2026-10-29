"""Spark decisions for backtest cases, from the name-removed description (text only).

Keys: (case, variant, person type, side, decision, situation). Answers are averaged over
REPEATS calls and kept in data/decisions/backtest_spark.json, like the demo table.
"""

import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from engine.check_api import call, load_env

MODEL = "muse-spark-1.3-contributor"
EFFORT = "medium"
REPEATS = 2
TABLE = Path(__file__).resolve().parent.parent.parent / "data" / "decisions" / "backtest_spark.json"
GENERIC_TABLE = TABLE.with_name("backtest_spark_generic.json")

SYSTEM = (
    "You simulate one specific real person deciding what to do with a new service. Stay in character. "
    "Real people are impatient, careful with money and drop services easily; do not be more patient or rational "
    "than they would be. Judge only from what you are told."
)
TYPES = {
    "careful": "You are careful with money and try new apps only when they clearly save you something.",
    "ordinary": "You are an ordinary person with a normal budget and a busy week.",
    "early": "You like trying new apps and services before your friends do.",
}
NEARBY = {"none": "There is almost nobody on the other side near you.",
          "few": "There are a handful of people on the other side near you.",
          "many": "There are plenty of people on the other side near you."}
OPTIONS = {"join": ("join", "ignore"), "buy": ("buy", "skip"), "stay": ("keep_using", "stop_using"),
           "pay": ("pay", "stay_free")}


def _price_text(v, side, case):
    if side == "supply" and not case["sides"].get("symmetric"):
        return "Joining this side is free; you get paid or matched through the service."
    p = v["price"]
    if p["model"] == "subscription":
        week = p.get("subscription_usd_week", 0)
        if not p.get("free_tier", True):
            return f"There is no free version: it costs about ${week * 4.33:.0f} per month from the start."
        return f"It is free to start; full access costs about ${week:.2f} per week."
    if p["model"] == "take_rate":
        price = v.get("transaction_price_usd", 0)
        disc = v.get("first_transaction_discount", 0)
        promo = f" Your first one is {disc:.0%} off." if disc else ""
        return f"Each use costs about ${price:.0f}.{promo}"
    return "It is free to use."


def generic_description(case, variant):
    """Anonymization test: a description built only from the case's structured fields (the two sides,
    country, one city or nationwide). No era, no product features, no city names, no history."""
    v = case["variants"][variant]
    d, s = case["sides"]["demand"]["label"], case["sides"]["supply"]["label"]
    country = {"us": "the United States", "jp": "Japan"}[v["market"]]
    if v.get("nationwide") or not v.get("cities"):
        where = f"It is available across {country}."
    else:
        more = len(v["cities"]) - 1
        where = f"It opens in one city in {country} first" + (
            f" and adds {more} more {'city' if more == 1 else 'cities'} over the following months." if more else ".")
    return f"A new phone app that connects {d} with {s}. {where}"


def situation_text(case, variant, side, decision, situation, generic=False):
    v = case["variants"][variant]
    me = case["sides"][side]["label"]
    about = generic_description(case, variant) if generic else case["description"].strip()
    text = f"About the service: {about}\nYou are one of the {me}. {_price_text(v, side, case)}\n"
    if decision == "join":
        return text + "You just came across it through its launch. Do you sign up and try it?"
    if decision == "buy":
        first, worked = situation
        if first == "first":
            text += "You need it this week and it found someone near you. This would be your first time."
        else:
            text += ("You need it again this week and it found someone near you. The first-time discount is gone; "
                     f"it is the full price now. Last time {'it went well' if worked == 'yes' else 'was not great'}.")
        return text + " Do you go ahead?"
    if decision == "stay":
        worked, nearby = situation
        return text + (f"You signed up a few weeks ago. It has {'already' if worked == 'yes' else 'not yet'} "
                       f"worked for you. {NEARBY[nearby]} What do you do this week?")
    if decision == "pay":
        worked, nearby = situation
        return text + (f"You are on the free version. It has {'already' if worked == 'yes' else 'not yet'} worked for "
                       f"you. {NEARBY[nearby]} Do you pay for full access this week?")
    raise ValueError(decision)


def _schema(actions):
    return {"type": "object", "additionalProperties": False, "required": ["probabilities", "reason"],
            "properties": {
                "probabilities": {"type": "object", "additionalProperties": False, "required": list(actions),
                                  "properties": {a: {"type": "number", "minimum": 0, "maximum": 1} for a in actions},
                                  "description": "How likely you are to do each action. Must sum to 1."},
                "reason": {"type": "string", "description": "One short sentence in your own voice, under 15 words."}}}


def _ask(env, case, key, generic=False):
    _, variant, type_id, side, decision, situation = key
    actions = OPTIONS[decision]
    body = {"model": MODEL, "reasoning_effort": EFFORT, "max_tokens": 6000,
            "messages": [{"role": "system", "content": SYSTEM + "\n\n" + TYPES[type_id]},
                         {"role": "user", "content": situation_text(case, variant, side, decision, situation, generic)}],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "decision", "strict": True, "schema": _schema(actions)}}}
    for attempt in range(4):
        try:
            status, data, _ = call(env, "POST", "/chat/completions", body)
        except OSError:              # read timeout or dropped connection: retry
            status, data = None, None
        if status == 200:
            try:
                return json.loads(data["choices"][0]["message"]["content"])
            except (KeyError, TypeError, ValueError):
                pass
        time.sleep(2 ** attempt * (5 if status == 429 else 1))
    raise RuntimeError(f"no answer for {key}: HTTP {status}")


def key_str(key):
    return json.dumps(list(key[:5]) + [list(key[5]) if isinstance(key[5], tuple) else key[5]])


class BacktestDecisions:
    def __init__(self, cases, generic=False):
        self.cases = cases
        self.generic = generic
        table = GENERIC_TABLE if generic else TABLE
        self.path = table
        self.entries = json.loads(table.read_text())["entries"] if table.exists() else {}

    def get(self, key):
        return self.entries[key_str(key)]["probs"]

    def prefill(self, keys, workers=24):
        todo = sorted({k for k in keys if key_str(k) not in self.entries}, key=key_str)
        if not todo:
            return 0
        env = load_env()
        jobs = [k for k in todo for _ in range(REPEATS)]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            answers = list(pool.map(lambda k: _ask(env, self.cases[k[0]], k, self.generic), jobs))
        for i, key in enumerate(todo):
            got = answers[i * REPEATS:(i + 1) * REPEATS]
            actions = OPTIONS[key[4]]
            probs = {a: statistics.mean(x["probabilities"][a] for x in got) for a in actions}
            total = sum(probs.values()) or 1
            self.entries[key_str(key)] = {"probs": {a: v / total for a, v in probs.items()},
                                          "reasons": [x["reason"] for x in got]}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"model": MODEL, "reasoning_effort": EFFORT, "repeats": REPEATS,
                                         "description": "generic" if self.generic else "name-removed",
                                         "entries": dict(sorted(self.entries.items()))}, indent=1))
        return len(todo)
