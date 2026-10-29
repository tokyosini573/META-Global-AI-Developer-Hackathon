"""The distilled Muse Glimmer as the decision provider: every simulated person is someone.

The Spark table answers once per person type. Glimmer is fast enough to answer for each
person, so the market gets a pool of fictional people, a few for every (place, type, side):
their own age, job, money, dating history and mood. A simulated person reached in a place
takes one of that place's people, and every decision is that person's own.

Places where a plan launches city by city get many more people (CITY_POOL), split by how often
each type and side arrives, so a city launch does not keep showing the same few stories.

The pool is fixed, so every decision it can need is known in advance (3 ads + 18 paywall
states per person). Glimmer answers all of them once on Modal and the answers are committed
as a table, like the Spark table: runs cost nothing and the demo survives without a GPU.

    .venv/bin/python -m engine.world.glimmer prepare     # pool + prompts -> glimmer-runs:/jobs/kindred.jsonl
    .venv/bin/modal run --detach engine/distill/glimmer_modal.py::decide_table --name kindred
    .venv/bin/python -m engine.world.glimmer collect     # -> data/decisions/kindred_glimmer.json
    .venv/bin/python -m engine.world.glimmer compare     # per type: Spark's answer vs Glimmer's people
"""

import json
import random
import subprocess
import sys
from pathlib import Path

from . import geo, screens
from .decide import OPTIONS, TYPES, TYPE_BY_ID

ROOT = Path(__file__).resolve().parent.parent.parent
TABLE = ROOT / "data" / "decisions" / "kindred_glimmer.json"
JOBS = ROOT / "runs" / "glimmer_jobs"
RUN = "r1"                 # distillation run whose merged weights answer (docs/distillation.md)
PER_CELL = 4               # people in the pool for each (place, type, side)
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


def make_pool(cfg):
    """{person id: person} with the same persona sentences the distillation data used.

    PER_CELL people everywhere first (ids stay stable when launch cities change), then the
    launch cities are topped up to CITY_POOL people in proportion to type weight x side share.
    """
    from engine.distill.make_data import HISTORY, MONEY, MOOD, PLACES, QUIRK, work
    from .spark import PERSONA
    pool = {}

    def add(rng, place, type_id, side):
        age = rng.randint(*TYPE_BY_ID[type_id]["age"])
        where = (f"{rng.choice(PLACES['a small town'])} (a small town)" if place == geo.SMALL_TOWN
                 else f"{place} (a big city)")
        parts = [PERSONA[type_id].format(age=age),
                 f"You are a {'man looking for women' if side == 'm' else 'woman looking for men'}.",
                 work(rng, type_id) + f" You live in {where}.",
                 rng.choice(MONEY), rng.choice(HISTORY), rng.choice(MOOD), rng.choice(QUIRK)]
        pool[f"g{len(pool):04d}"] = {"place": place, "type": type_id, "side": side, "age": age,
                                     "name": rng.choice(NAMES[side]), "text": " ".join(x for x in parts if x)}

    rng = random.Random(SEED)
    for place in places():
        for t in TYPES:
            for side in ("m", "w"):
                for _ in range(PER_CELL):
                    add(rng, place, t["id"], side)
    rng = random.Random(SEED + 1)
    share = {"m": cfg["world"]["share_male"], "w": 1 - cfg["world"]["share_male"]}
    for place in launch_cities(cfg):
        for t in TYPES:
            for side in ("m", "w"):
                for _ in range(max(0, round(CITY_POOL * t["weight"] * share[side]) - PER_CELL)):
                    add(rng, place, t["id"], side)
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
    pool = make_pool(yaml.safe_load(PLANS.read_text()))
    done = json.loads(TABLE.read_text())["entries"] if TABLE.exists() else {}
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
    (JOBS / "pool.json").write_text(json.dumps(pool))
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
    pool = json.loads((JOBS / "pool.json").read_text())
    entries, missing = json.loads(TABLE.read_text())["entries"] if TABLE.exists() else {}, 0
    for line in out.read_text().splitlines():
        r = json.loads(line)
        if r["probs"] is None:
            missing += 1
            continue
        total = sum(max(0.0, v) for v in r["probs"].values()) or 1.0
        entries[r["id"]] = {"probs": {o: round(max(0.0, v) / total, 4) for o, v in r["probs"].items()},
                            "noticed": r["noticed"], "reason": r["reason"]}
    TABLE.write_text(json.dumps({"model": f"Muse Glimmer 30B, distilled run {RUN}", "per_cell": PER_CELL,
                                 "city_pool": CITY_POOL, "pool": pool, "entries": dict(sorted(entries.items()))}, separators=(",", ":")))
    print(f"{len(entries)} answers ({missing} without valid JSON) -> {TABLE.relative_to(ROOT)}")


def compare():
    """Per type: Spark's one answer next to the spread of Glimmer's answers for that type's people."""
    import statistics
    from .spark import SparkProvider
    spark, g = SparkProvider(), GlimmerProvider()
    print("| Type | Decision | Spark (type table) | Glimmer, mean of people | Glimmer, middle 80% of people |")
    print("|---|---|---|---|---|")
    for t in TYPES:
        people = [pid for pid, p in g.pool.items() if p["type"] == t["id"]]
        for kind, option in (("install", "install"), ("paywall", "pay"), ("paywall", "delete_app")):
            sp, gl = [], []
            for _, screen, bucket, *_ in (x for x in situations() if x[0] == kind):
                sp.append(spark.decide(kind, t["id"], screen, bucket)[option])
                gl += [g.decide(kind, pid, screen, bucket)[option] for pid in people]
            q = statistics.quantiles(gl, n=10)
            print(f"| {t['id']} | {option} | {statistics.mean(sp):.2f} | {statistics.mean(gl):.2f} | "
                  f"{q[0]:.2f}-{q[-1]:.2f} |")


class GlimmerProvider:
    name = "glimmer"
    per_person = True

    def __init__(self, table=TABLE):
        data = json.loads(table.read_text())
        self.pool, self.entries = data["pool"], data["entries"]
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
    {"prepare": prepare, "collect": collect, "compare": compare}[sys.argv[1]]()
