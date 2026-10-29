"""Distillation data: Spark's decisions for thousands of individual, fictional people.

    .venv/bin/python -m engine.distill.make_data --n 4000

The demo table asks Spark once per person type. Here every example is a different person
(age, job, place, money, dating history, mood) looking at the same Kindred screens in the
same situations as the demo, so Glimmer can learn to decide per person. Everyone is made up:
the contributor model's inputs may be used by Meta for training.

Each line of data/distill/examples.jsonl is one Spark answer. Test examples are asked twice,
so the evaluation can say how often Spark agrees with itself.
"""

import argparse
import json
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from engine.check_api import load_env
from engine.world import screens
from engine.world.decide import OPTIONS, TYPES
from engine.world.spark import INSTALL_CONTEXT, MATCHED, NEARBY, PERSONA, WEEK, ask_body, request_body

OUT = Path(__file__).resolve().parent.parent.parent / "data" / "distill" / "examples.jsonl"
SEED = 20261030
SPLITS = (("train", 0.8), ("val", 0.1), ("test", 0.1))

PLACES = {
    "a big city": ["Chicago", "Houston", "Philadelphia", "Atlanta", "Seattle", "Denver", "Phoenix", "Boston"],
    "a college town": ["Ann Arbor", "Boulder", "Madison", "Athens, Georgia", "Gainesville", "State College"],
    "a suburb": ["a suburb of Dallas", "a suburb of Minneapolis", "a suburb of Charlotte", "a suburb of Sacramento"],
    "a small town": ["a small town in Ohio", "a small town in Kansas", "a small town in Maine", "a small town in Utah"],
}
JOBS = ["nurse", "barista", "software tester", "warehouse worker", "teacher", "line cook", "accountant",
        "retail manager", "graduate student", "electrician", "marketing assistant", "dental hygienist",
        "truck driver", "bank teller", "freelance designer", "physical therapist", "call center agent",
        "lab technician", "real estate agent", "bartender", "pharmacy technician", "mechanic", "paralegal",
        "personal trainer", "data analyst", "hair stylist", "sales rep", "security guard", "chef", "librarian"]
MONEY = ["You have about $40 a month left for anything fun.", "You have about $120 a month left for fun.",
         "You have about $300 a month left for fun.", "Money is not a worry for you right now.",
         "You are paying off a credit card and watch every dollar."]
HISTORY = ["You have never used a dating app.", "You deleted two dating apps last year after nothing came of them.",
           "You met your last partner on an app.", "You use another dating app most days.",
           "You tried apps once and felt ignored.", "You only date people you meet through friends so far."]
MOOD = ["It is late at night and you cannot sleep.", "You are on your lunch break.", "It is a slow Sunday afternoon.",
        "You are on the bus to work.", "You just got home from a long shift.", "You are waiting for a friend."]
PRO_JOBS = ["software engineer", "consultant", "attorney", "product manager", "financial analyst", "physician",
            "architect", "sales director", "pharmacist", "engineering manager"]
QUIRK = ["You hate paying before you see that something works.", "You trust apps your friends already use.",
         "You have felt lonely since a breakup a few months ago.", "You are picky and swipe left on most people.",
         "You get bored with apps within days.", "You like trying new apps before anyone else.",
         "You want someone who lives close by.", "You are wary of fake profiles.", ""]


def work(rng, type_id):
    if type_id == "student":
        return f"You study full time and work a few hours a week as a {rng.choice(JOBS)}."
    if type_id == "busy_professional":
        return f"You work as a {rng.choice(PRO_JOBS)}."
    return f"You work as a {rng.choice(JOBS)}."


def make_person(rng, i):
    t = rng.choices(TYPES, weights=[x["weight"] for x in TYPES])[0]
    age = rng.randint(*t["age"])
    man = rng.random() < 0.7
    kind = rng.choice(list(PLACES))
    parts = [PERSONA[t["id"]].format(age=age),
             f"You are a {'man looking for women' if man else 'woman looking for men'}.",
             work(rng, t["id"]) + f" You live in {rng.choice(PLACES[kind])} ({kind}).",
             rng.choice(MONEY), rng.choice(HISTORY), rng.choice(MOOD), rng.choice(QUIRK)]
    return {"id": f"p{i:05d}", "type": t["id"], "text": " ".join(x for x in parts if x)}


def make_situation(rng):
    if rng.random() < 0.4:
        channel = rng.choice(list(INSTALL_CONTEXT))
        return {"kind": "install", "screen": screens.install_screen(channel), "bucket": channel,
                "history": "", "question": INSTALL_CONTEXT[channel]}
    bucket = (rng.choice(list(MATCHED)), rng.choice(list(NEARBY)), rng.choice(list(WEEK)))
    matched, nearby, week = bucket
    return {"kind": "paywall", "screen": screens.paywall_screen(bucket), "bucket": "|".join(bucket),
            "history": " ".join([WEEK[week], MATCHED[matched], NEARBY[nearby]]),
            "question": "This is what Kindred shows you right now. What do you do?"}


def examples(n):
    rng = random.Random(SEED)
    out = []
    for i in range(n):
        person, sit = make_person(rng, i), make_situation(rng)
        r = rng.random()
        split = "train" if r < SPLITS[0][1] else "val" if r < SPLITS[0][1] + SPLITS[1][1] else "test"
        persona = (person["text"] + " " + sit["history"]).strip()
        out.append({"id": f"x{i:05d}", "split": split, "person": person["id"], "type": person["type"],
                    "persona": persona, "kind": sit["kind"], "screen": sit["screen"], "bucket": sit["bucket"],
                    "question": sit["question"], "options": list(OPTIONS[sit["kind"]])})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4000)
    ap.add_argument("--workers", type=int, default=36)
    args = ap.parse_args()
    todo = []
    for ex in examples(args.n):
        todo.append((ex, 0))
        if ex["split"] == "test":
            todo.append((ex, 1))          # second Spark answer: how often Spark agrees with itself
    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            r = json.loads(line)
            done.add((r["id"], r["repeat"]))
    todo = [(ex, k) for ex, k in todo if (ex["id"], k) not in done]
    print(f"{len(todo)} calls to make ({len(done)} already in {OUT.name})", flush=True)
    env = load_env()
    lock = threading.Lock()
    cost, t0, n = 0.0, time.time(), 0

    def ask(ex):
        body = request_body(ex["persona"], ex["screen"], ex["question"], ex["options"])
        return ask_body(env, body, ex["id"])

    with ThreadPoolExecutor(max_workers=args.workers) as pool, OUT.open("a") as f:
        futures = {pool.submit(ask, ex): (ex, k) for ex, k in todo}
        for fut in as_completed(futures):
            ex, k = futures[fut]
            try:
                answer, c = fut.result()
            except RuntimeError as e:
                print("skip", e, flush=True)
                continue
            with lock:
                f.write(json.dumps({**ex, "repeat": k, "spark": answer}) + "\n")
                f.flush()
                cost += c
                n += 1
                if n % 200 == 0:
                    print(f"{n}/{len(todo)}  ${cost:.2f}  {time.time() - t0:.0f}s", flush=True)
    print(f"done: {n} answers, ${cost:.2f}, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
