"""Muse Wonder, the planner: it designs the market's people before a run and explains the result after.

    .venv/bin/python -m engine.world.wonder people     # -> data/wonder/kindred_people.json

Before: Wonder looks at the app's own screens (the ad, the store page, the paywall), the market and
the two plans, and designs who could be reached: person types with their share and age range, and
the details that make each person different (work, money, dating history, mood, habits). The pool of
fictional people (engine/world/glimmer.py) is drawn from this design.

After: Wonder reads the run's numbers and what people said, and writes the one-sentence reason under
the verdict. It is told not to use numbers; the win count is added by the engine from the runs.

Answers are saved, so a rerun with the same inputs costs nothing. Wonder is the standard model, and
only fictional people and a fictional app are sent.
"""

import hashlib
import json
import sys
from pathlib import Path

import yaml

from engine.check_api import call, load_env

from . import screens

MODEL = "muse-wonder-1.0"
PRICE = (4.00, 20.00)      # USD per 1M tokens (input, output)
ROOT = Path(__file__).resolve().parent.parent.parent
PEOPLE = ROOT / "data" / "wonder" / "kindred_people.json"
VERDICTS = ROOT / "data" / "wonder" / "kindred_verdicts.json"
PLANS = ROOT / "plans" / "kindred.yaml"

VERDICT_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["reason"],
    "properties": {"reason": {"type": "string", "description": "One or two short sentences, under 30 words, "
                                                                "no numbers."}},
}


EXAMPLE = {
    "types": [{"id": "night_shift_worker", "name": "Night shift worker", "share": 0.1, "age_min": 22, "age_max": 34,
               "persona": "You are {age} and work nights, so you are awake when your friends are asleep.",
               "work": "You work as {job}.", "jobs": ["nurse", "security guard", "warehouse picker", "baker"]}],
    "money": ["You have about $60 a month left for anything fun."],
    "history": ["You have never used a dating app."],
    "mood": ["You are on your break at 3 a.m."],
    "quirk": ["You read every review before you download anything."],
    "rationale": "Why these types and shares, in 3 to 5 sentences.",
}


def check_people(d):
    """Refuse a design the pool cannot use, before anything is built from it."""
    types = d["types"]
    assert 6 <= len(types) <= 10, f"{len(types)} types"
    for t in types:
        assert "{age}" in t["persona"] and t["persona"].startswith("You"), t["persona"]
        assert "{job}" in t["work"] and t["work"].startswith("You"), t["work"]
        assert len(t["jobs"]) >= 3 and t["age_min"] <= t["age_max"], t["id"]
        t["age_min"], t["age_max"] = max(18, t["age_min"]), min(34, t["age_max"])   # the market is 18 to 34
    for k in ("money", "history", "mood", "quirk"):
        assert len(d[k]) >= 5 and all(x.startswith("You") for x in d[k]), (k, d[k][:2])


def _image(name):
    import base64
    return {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(
        screens.path(name).read_bytes()).decode()}}


def ask(messages, schema=None, name=None):
    """One Wonder call. With a schema the API enforces it; without, the answer is JSON in plain text."""
    env = load_env()
    body = {"model": MODEL, "messages": messages, "max_tokens": 16000}
    if schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}}
    status, data, sec = call(env, "POST", "/chat/completions", body, timeout=600)
    if status != 200:
        raise SystemExit(f"Wonder failed: HTTP {status} {data}")
    usage = data.get("usage", {})
    cost = (usage.get("prompt_tokens", 0) * PRICE[0] + usage.get("completion_tokens", 0) * PRICE[1]) / 1e6
    print(f"Wonder: {sec:.0f}s, ${cost:.3f}")
    text = data["choices"][0]["message"]["content"]
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def plan_text(cfg):
    lines = []
    for k, p in cfg["plans"].items():
        where = ", ".join(c["name"] for c in p.get("cities", [])) or "nationwide"
        chans = ", ".join(f"{c['kind']} ({c['where']})" for c in p["channels"])
        lines.append(f"- {p['name']}: {p['summary']}. Where: {where}. Channels: {chans}. "
                     f"Free swipes a day: {p['free_swipes_per_day']}. Free trial days: {p['trial_days']}.")
    return "\n".join(lines)


def design_people():
    cfg = yaml.safe_load(PLANS.read_text())
    text = (f"You design the simulated people for a launch rehearsal of {cfg['app']}, a new swipe dating app, "
            f"in the {cfg['market']} for {cfg['days']} days. The images are the app's own TikTok ad, its store "
            f"page and its paywall. The two launch plans:\n{plan_text(cfg)}\n\n"
            "Design who these plans could reach: single adults aged 18 to 34 in the United States who might see "
            f"this ad or be shown the app. About {cfg['world']['share_male']:.0%} of them are men looking for women, "
            "the rest women looking for men. Gender and where each person lives are set elsewhere: do not tie a "
            "type or a detail to gender or to a city, town or kind of place. "
            "Give 6 to 10 person types that differ in how they would react to these screens (price, novelty, "
            "trust, how much they want a relationship, how busy they are), with shares that fit the US market. "
            "Then give detail sentences that apply to any type, so two people of one type still differ. "
            "Everyone is fictional: no real names, no real company or app names. Plain words, no jargon. "
            "Every sentence except the rationale speaks to the person as 'you'; the rationale is written for the "
            "founder.\n\n"
            "Answer with one JSON object only, in exactly this shape (the values here are an example of the style, "
            "not the answer):\n" + json.dumps(EXAMPLE, indent=1))
    content = [_image(screens.install_screen("tiktok_ad")), _image(screens.install_screen("ambassador")),
               _image(screens.paywall_screen(("no", "none", "w1"))), {"type": "text", "text": text}]
    out = ask([{"role": "user", "content": content}])
    (PEOPLE.parent / "people_raw.json").write_text(json.dumps(out, indent=1))   # kept to see what Wonder said
    check_people(out)
    total = sum(t["share"] for t in out["types"])
    for t in out["types"]:
        t["share"] = t["share"] / total
    PEOPLE.parent.mkdir(parents=True, exist_ok=True)
    PEOPLE.write_text(json.dumps({"model": MODEL, "plans": cfg["plans"], **out}, indent=1))
    for t in out["types"]:
        print(f"{t['share']:.2f} {t['id']} {t['age_min']}-{t['age_max']}: {t['persona']}")
    print(out["rationale"])


def people():
    return json.loads(PEOPLE.read_text())


def verdict_reason(cfg, facts):
    """One sentence on why the winner won, from the run's numbers and people's own words. Cached by input."""
    text = (f"A launch rehearsal of {cfg['app']}, a new swipe dating app, ran two plans in the {cfg['market']} "
            f"for {cfg['days']} days with the same budget, many times over.\nPlans:\n{plan_text(cfg)}\n\n"
            f"What happened (medians across runs, and what simulated people said):\n{json.dumps(facts, indent=1)}\n\n"
            f"{facts['winner']} wins. Write the reason a founder reads under the headline '{facts['winner']} wins.': "
            "the mechanism that made the difference, in plain words a non-expert understands, one or two short "
            "sentences, under 30 words. Use no numbers (the win count is shown next to it). Say only what the "
            "facts above support.")
    key = hashlib.sha256(text.encode()).hexdigest()[:16]
    cache = json.loads(VERDICTS.read_text()) if VERDICTS.exists() else {}
    if key not in cache:
        cache[key] = ask([{"role": "user", "content": text}], VERDICT_SCHEMA, "verdict")["reason"]
        VERDICTS.parent.mkdir(parents=True, exist_ok=True)
        VERDICTS.write_text(json.dumps(cache, indent=1))
    return cache[key]


if __name__ == "__main__":
    {"people": design_people}[sys.argv[1]]()
