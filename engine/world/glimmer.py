"""The distilled Muse Glimmer as the decision provider: every simulated person is someone.

Muse Wonder designs the market's people (engine/world/wonder.py: types, shares, ages and the
details that set people apart). From that design the market gets a fixed pool of fictional people
for every place, each with their own age, work, money, dating history and mood. A simulated person
reached in a place takes one of that place's people, and every decision is that person's own.

Each place has PLACE_POOL people split by type share x side share; places where a plan launches
city by city get CITY_POOL, so a city launch does not keep showing the same few stories.

The pool is fixed, so every decision it can need is known in advance (3 ads + 18 paywall
states per person). Glimmer answers all of them once on Modal and the answers are committed
as a table, like the Spark table: runs cost nothing and the demo survives without a GPU.

    .venv/bin/python -m engine.world.glimmer prepare     # pool + prompts -> glimmer-runs:/jobs/kindred.jsonl
    .venv/bin/modal run --detach engine/distill/glimmer_modal.py::decide_table --name kindred
    .venv/bin/python -m engine.world.glimmer collect     # -> data/decisions/kindred_glimmer.json
    .venv/bin/python -m engine.world.glimmer check       # Spark on a sample of the pool vs Glimmer's table
"""

import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

from . import geo, screens, wonder
from .decide import OPTIONS

ROOT = Path(__file__).resolve().parent.parent.parent
TABLE = ROOT / "data" / "decisions" / "kindred_glimmer.json"
CHECK = ROOT / "data" / "distill" / "wonder_pool_check.md"
JOBS = ROOT / "runs" / "glimmer_jobs"
RUN = "r1"                 # distillation run whose merged weights answer (docs/distillation.md)
PLACE_POOL = 48            # people in the pool for each place
CITY_POOL = 600            # people in each launch city: a city launch reaches up to ~550 dots a run
PLANS = ROOT / "plans" / "kindred.yaml"
SEED = 20261031
NAMES = {"m": ["Jordan", "Sam", "Alex", "Chris", "Marcus", "Luis", "Tyler", "Omar", "Ethan", "Kevin", "Drew",
               "Ryan", "Daniel", "Andre", "Noah", "Brandon"],
         "w": ["Maya", "Riley", "Taylor", "Jamie", "Ana", "Jasmine", "Nina", "Grace", "Leah", "Priya", "Avery",
               "Morgan", "Sofia", "Hannah", "Chloe", "Destiny"]}


def places():
    return [m[0] for m in geo.METROS] + [geo.SMALL_TOWN]


def launch_cities(cfg):
    return sorted({c["name"] for plan in cfg["plans"].values() for c in plan.get("cities", [])})


def design_hash(design):
    return hashlib.sha256(json.dumps(design, sort_keys=True).encode()).hexdigest()[:12]


def article(job):
    return ("an " if job[0].lower() in "aeiou" else "a ") + job


def make_pool(cfg, design):
    """{person id: person} drawn from Wonder's design, in the persona shape Glimmer was trained on."""
    from engine.distill.make_data import PLACES
    share = {"m": cfg["world"]["share_male"], "w": 1 - cfg["world"]["share_male"]}
    rng = random.Random(SEED)
    pool = {}
    for place in places():
        n = CITY_POOL if place in launch_cities(cfg) else PLACE_POOL
        for t in design["types"]:
            for side in ("m", "w"):
                for _ in range(max(1, round(n * t["share"] * share[side]))):
                    age = rng.randint(t["age_min"], t["age_max"])
                    where = (f"{rng.choice(PLACES['a small town'])} (a small town)" if place == geo.SMALL_TOWN
                             else f"{place} (a big city)")
                    parts = [t["persona"].format(age=age),
                             f"You are a {'man looking for women' if side == 'm' else 'woman looking for men'}.",
                             t["work"].format(job=article(rng.choice(t["jobs"]))) + f" You live in {where}.",
                             rng.choice(design["money"]), rng.choice(design["history"]), rng.choice(design["mood"]),
                             rng.choice(design["quirk"])]
                    pool[f"w{len(pool):04d}"] = {"place": place, "type": t["id"], "side": side, "age": age,
                                                 "name": rng.choice(NAMES[side]), "text": " ".join(parts)}
    return pool


def key(kind, who, screen, bucket):
    return f"{who}|{kind}|{screen if kind == 'install' else ','.join(bucket)}"


def situations():
    """(kind, screen, bucket, image, history, question) for every decision a person can face."""
    from .spark import INSTALL_CONTEXT, MATCHED, NEARBY, WEEK
    for screen, question in INSTALL_CONTEXT.items():
        yield "install", screen, "-", screens.install_screen(screen), "", question
    for matched in MATCHED:
        for nearby in NEARBY:
            for week in WEEK:
                bucket = (matched, nearby, week)
                yield ("paywall", "paywall", bucket, screens.paywall_screen(bucket),
                       " ".join([WEEK[week], MATCHED[matched], NEARBY[nearby]]),
                       "This is what Kindred shows you right now. What do you do?")


def prepare():
    """Write one chat prompt per (person, situation) not yet in the table and upload them with the pool."""
    import yaml
    from engine.distill.format import chat
    design = wonder.people()
    pool = make_pool(yaml.safe_load(PLANS.read_text()), design)
    old = json.loads(TABLE.read_text()) if TABLE.exists() else {}
    done = old["entries"] if old.get("design") == design_hash(design) else {}
    JOBS.mkdir(parents=True, exist_ok=True)
    rows = []
    for pid, person in pool.items():
        for kind, screen, bucket, image, history, question in situations():
            if key(kind, pid, screen, bucket) in done:
                continue
            ex = {"persona": (person["text"] + " " + history).strip(), "question": question,
                  "options": list(OPTIONS[kind])}
            rows.append({"id": key(kind, pid, screen, bucket), "image": image + ".png", "options": ex["options"],
                         "messages": chat(ex)})
    (JOBS / "kindred.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (JOBS / "pool.json").write_text(json.dumps({"design": design_hash(design), "pool": pool}))
    # relative paths: the modal CLI rejects the absolute path of this folder (non-ASCII characters)
    subprocess.run([".venv/bin/modal", "volume", "put", "--force", "glimmer-runs",
                    str((JOBS / "kindred.jsonl").relative_to(ROOT)), "/jobs/kindred.jsonl"],
                   check=True, cwd=ROOT, capture_output=True)
    print(f"{len(pool)} people, {len(rows)} prompts -> glimmer-runs:/jobs/kindred.jsonl")


def collect():
    """Download Glimmer's answers and write the committed table."""
    out = JOBS / "kindred_out.jsonl"
    subprocess.run([".venv/bin/modal", "volume", "get", "--force", "glimmer-runs", "/jobs/kindred_out.jsonl",
                    str(out.relative_to(ROOT))], check=True, cwd=ROOT, capture_output=True)
    job = json.loads((JOBS / "pool.json").read_text())
    pool, design = job["pool"], wonder.people()
    old = json.loads(TABLE.read_text()) if TABLE.exists() else {}
    entries = old["entries"] if old.get("design") == job["design"] else {}
    missing = 0
    for line in out.read_text().splitlines():
        r = json.loads(line)
        if r["probs"] is None:
            missing += 1
            continue
        total = sum(max(0.0, v) for v in r["probs"].values()) or 1.0
        entries[r["id"]] = {"probs": {o: round(max(0.0, v) / total, 4) for o, v in r["probs"].items()},
                            "noticed": r["noticed"], "reason": r["reason"]}
    entries = {k: v for k, v in entries.items() if k.split("|")[0] in pool}
    TABLE.write_text(json.dumps({"model": f"Muse Glimmer 30B, distilled run {RUN}", "design": job["design"],
                                 "types": [{"id": t["id"], "name": t["name"], "weight": t["share"],
                                            "age": [t["age_min"], t["age_max"]]} for t in design["types"]],
                                 "place_pool": PLACE_POOL, "city_pool": CITY_POOL, "pool": pool, "entries": dict(sorted(entries.items()))}, separators=(",", ":")))
    print(f"{len(entries)} answers ({missing} without valid JSON) -> {TABLE.relative_to(ROOT)}")


def check(n=300, workers=24):
    """Glimmer was trained on people from a hand-written generator; the pool now comes from Wonder.
    Ask Spark the same questions for a random sample of the pool and see how often Glimmer agrees."""
    import statistics
    from concurrent.futures import ThreadPoolExecutor
    from engine.check_api import load_env
    from engine.distill.score import compare, norm
    from .spark import ask_body, request_body
    g = GlimmerProvider()
    sits = {}
    for kind, screen, bucket, image, history, question in situations():
        sits[(kind, screen, bucket)] = (image, history, question)
    rng = random.Random(SEED)
    sample = rng.sample(sorted(g.entries), n)
    env = load_env()

    def ask(k):
        pid, kind, rest = k.split("|")
        screen, bucket = (rest, "-") if kind == "install" else ("paywall", tuple(rest.split(",")))
        image, history, question = sits[(kind, screen, bucket)]
        persona = (g.pool[pid]["text"] + " " + history).strip()
        return ask_body(env, request_body(persona, image, question, OPTIONS[kind]), k)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        answers = list(pool.map(ask, sample))
    rows, cost = {"install": [], "paywall": []}, 0.0
    for k, (ans, c) in zip(sample, answers):
        cost += c
        kind = k.split("|")[1]
        opts = OPTIONS[kind]
        rows[kind].append(compare(norm(ans["probabilities"], opts), norm(g.entries[k]["probs"], opts), opts))
    lines = ["# Glimmer on Wonder's people", "",
             f"Spark (contributor, reasoning medium) answered {n} decisions drawn at random from the pool designed by "
             f"Muse Wonder; Glimmer's committed answers are compared with Spark's. Spark cost ${cost:.2f}.", "",
             "| Decisions | Count | Same top choice | Mean abs. difference |", "|---|---|---|---|"]
    for name, rs in (("All", rows["install"] + rows["paywall"]), ("Install", rows["install"]),
                     ("Paywall", rows["paywall"])):
        lines.append(f"| {name} | {len(rs)} | {sum(r[0] for r in rs) / len(rs):.0%} | "
                     f"{statistics.mean(r[1] for r in rs):.3f} |")
    lines += ["", "For reference, on the distillation test people (same generator as training): Glimmer 85% / 0.079, "
              "Spark asked twice 86% / 0.078 (docs/distillation.md)."]
    CHECK.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


class GlimmerProvider:
    name = "glimmer"
    per_person = True

    def __init__(self, table=TABLE):
        data = json.loads(table.read_text())
        self.pool, self.entries = data["pool"], data["entries"]
        self.types = data["types"]          # Wonder's types: who is reached, and how often
        self.cells = {}
        for pid, p in self.pool.items():
            self.cells.setdefault((p["place"], p["type"], p["side"]), []).append(pid)

    def persona(self, rng, place, type_id, side, taken=()):
        """One person from the pool who lives in `place` and fits the type and side, someone new
        to this run (`taken`) while there is anyone left."""
        ids = self.cells[(place, type_id, side)]
        free = [i for i in ids if i not in taken] or ids
        return free[rng.integers(len(free))]

    def answer(self, kind, who, screen, bucket):
        k = key(kind, who, screen, bucket)
        if k not in self.entries:
            raise KeyError(f"{k} is not in {TABLE.name}; rerun `python -m engine.world.glimmer prepare` and the table job")
        return self.entries[k]

    def decide(self, kind, who, screen, bucket):
        return self.answer(kind, who, screen, bucket)["probs"]


if __name__ == "__main__":
    {"prepare": prepare, "collect": collect, "check": check}[sys.argv[1]]()
