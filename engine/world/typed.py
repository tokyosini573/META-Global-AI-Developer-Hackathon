"""Decisions per kind of person, for any market pack: Muse Wonder designs the kinds, Muse Spark answers.

    .venv/bin/python -m engine.world.typed plans/reloop.yaml     # Wonder's people, then Spark's table

Glimmer answers for every person in the dating demo's fixed pool (engine/world/glimmer.py), which
takes a GPU job of about an hour. Every other market, and every rehearsal run live from uploaded
screens, uses this provider instead: Wonder looks at the app's screens and the two plans and designs
6 to 10 kinds of people (each on one side of the market when the sides differ), and Spark answers
each decision once per kind of person. That is about 200 small calls, a few minutes in parallel.

The demo apps are fictional, so their questions go to the Spark contributor model; screens uploaded
by a person go to Spark standard, which is not used for training.

With a brief (cfg["brief"]) Wonder also reads the app's profile, audience and competition, and the
table gets the v2 questions: install per ad (the key's last part is the ad id, or "store"), sign-up,
and why someone stopped (a reason per kind and situation). New answers keep a reason for each choice,
so a person who did the less likely thing still has their own words, and a hash of the question, so
an answer asked with other words is asked again.
"""

import base64
import hashlib
import json
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from engine import packs
from engine.check_api import load_env

from . import screens, spark, wonder
from .decide import gate_key, gate_question, install_question, price_override, signup_question, why_quit_question
from .decide import nearby_bucket, week_bucket  # noqa: F401  (the buckets the gate keys use)

ROOT = Path(__file__).resolve().parent.parent.parent
CONTRIBUTOR = "muse-spark-1.3-contributor"
STANDARD = "muse-spark-1.3"
BUCKETS = [(m, n, w) for m in ("no", "yes") for n in ("none", "few", "many") for w in ("w1", "w2-4", "w5+")]

DESIGN_EXAMPLE = {
    "types": [{"id": "weekend_declutterer", "name": "Weekend declutterer", "side": "seller", "share": 0.15,
               "age_min": 28, "age_max": 45,
               "persona": "You are {age} and clear out a closet every few months, but hate haggling with strangers.",
               "work": "You work as {job}.", "jobs": ["teacher", "office manager", "nurse"]}],
    "rationale": "Why these kinds of people and shares, in 3 to 5 sentences.",
}


def check_design(d, pack, ages=None):
    """Refuse a design the engine cannot use."""
    sides = [s for s, _ in pack["sides"]]
    two_kinds = pack["mechanics"] == "transaction"
    types = d["types"]
    assert 6 <= len(types) <= 10, f"{len(types)} types"
    lo, hi = ages or pack["age"]
    for t in types:
        assert "{age}" in t["persona"] and t["persona"].startswith("You"), t["persona"]
        assert "{job}" in t["work"] and t["work"].startswith("You"), t["work"]
        assert len(t["jobs"]) >= 3 and t["age_min"] <= t["age_max"], t["id"]
        t["age_min"], t["age_max"] = max(lo, t["age_min"]), min(hi, t["age_max"])
        if t["age_min"] > t["age_max"]:          # a kind outside the audience's ages: keep its edge
            t["age_min"] = t["age_max"] = lo if t["age_min"] > hi else hi
        if two_kinds:
            assert t.get("side") in sides, (t["id"], t.get("side"))
        else:
            t.pop("side", None)
    if two_kinds:
        for s in sides:
            assert sum(t["side"] == s for t in types) >= 2, f"fewer than 2 kinds of {s}"


def age_range(cfg):
    """The brief's audience ages, inside the pack's limits (else the pack's)."""
    lo, hi = packs.of(cfg)["age"]
    want = ((cfg.get("brief") or {}).get("audience") or {}).get("age")
    if want:
        a, b = max(lo, int(want[0])), min(hi, int(want[1]))
        if a <= b:
            return a, b
    return lo, hi


INCOME = {"under_30k": "under $30,000 a year", "30_60k": "$30,000 to $60,000 a year",
          "60_100k": "$60,000 to $100,000 a year", "over_100k": "over $100,000 a year", "mixed": "mixed incomes"}
NEW_APPS = {"early": "try new apps early", "friends": "wait until friends use an app", "rarely": "rarely switch apps"}


def brief_text(brief):
    """What the founder says about the app, its audience and competition, for Wonder's design."""
    if not brief:
        return ""
    from .decide import _cut
    prof, aud, comp = brief["profile"], brief.get("audience", {}), brief.get("competition") or {}
    lines = [f"What the app does: {_cut(prof['does'], 300)}", f"Why people would pick it: {_cut(prof['why'], 200)}"]
    if prof.get("features"):
        lines.append("Key features: " + "; ".join(_cut(f, 40) for f in prof["features"][:5]))
    if aud.get("who"):
        lines.append(f"Who it is for: {_cut(aud['who'], 200)}")
    if aud.get("income") in INCOME:
        lines.append(f"Their income: {INCOME[aud['income']]}")
    for k, label in (("lifestyle", "Work and lifestyle"), ("interests", "Interests")):
        if aud.get(k):
            lines.append(f"{label}: {_cut(aud[k], 120)}")
    if aud.get("new_apps") in NEW_APPS:
        lines.append(f"Most of them {NEW_APPS[aud['new_apps']]}")
    if comp.get("now"):
        lines.append(f"What people use now: {_cut(comp['now'], 200)}")
    if comp.get("switch"):
        lines.append(f"Why they would switch: {_cut(comp['switch'], 200)}")
    return "What the founder says (their view, not a fact):\n" + "\n".join("- " + x for x in lines) + "\n\n"


def design(cfg, images, out_path):
    """Ask Wonder for the kinds of people this market's launch could reach, and save the design."""
    pack = packs.of(cfg)
    lo, hi = age_range(cfg)
    if pack["mechanics"] == "transaction":
        (a, a_you), (b, b_you) = pack["sides"]
        who = (f"Two sides use the app: {a}s ('{a_you}') and {b}s ('{b_you}'). Give 3 to 5 kinds of people for "
               f"each side, each with a \"side\" of \"{a}\" or \"{b}\"; shares add up to 1 within each side.")
    else:
        who = ("Everyone uses the app the same way; leave out \"side\". Gender and where each person lives are set "
               "elsewhere: do not tie a kind of person to gender or to a place.")
    text = (f"You design the simulated people for a launch rehearsal of {cfg['app']}, {pack['category']}, in the "
            f"{cfg['market']} for {cfg['days']} days. The images are the app's own ad, its store page and the "
            f"screens people see while using it. The two launch plans:\n{wonder.plan_text(cfg)}\n\n"
            f"{brief_text(cfg.get('brief'))}"
            f"Design who these plans could reach: adults aged {lo} to {hi} in the {cfg['market']}. {who} "
            "Make the kinds differ in how they would react to these screens (price, trust, how much they need the "
            "app, how busy they are), with shares that fit the market. Do not tie a kind of person to a city. "
            "Everyone is fictional: no real names, no real company or app names. Plain words, no jargon. Every "
            "sentence except the rationale speaks to the person as 'you'; the rationale is written for the founder."
            "\n\nAnswer with one JSON object only, in exactly this shape (the values here are an example of the "
            "style, not the answer):\n" + json.dumps(DESIGN_EXAMPLE, indent=1))
    content = [{"type": "image_url", "image_url": {"url": _data_url(p)}} for p in images] + [{"type": "text", "text": text}]
    out = wonder.ask([{"role": "user", "content": content}])
    check_design(out, pack, (lo, hi))
    for side in {t.get("side") for t in out["types"]}:
        mine = [t for t in out["types"] if t.get("side") == side]
        total = sum(t["share"] for t in mine)
        for t in mine:
            t["share"] = t["share"] / total
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"model": wonder.MODEL, "app": cfg["app"], **out}, indent=1))
    return out


def _data_url(path):
    """The image as a data URL with its real media type (uploads may be JPEG or WebP saved as .png)."""
    data = Path(path).read_bytes()
    kind = ("image/jpeg" if data[:3] == b"\xff\xd8\xff" else
            "image/webp" if data[:4] == b"RIFF" and data[8:12] == b"WEBP" else "image/png")
    return f"data:{kind};base64," + base64.b64encode(data).decode()


def _key_str(key):
    kind, who, screen, bucket = key
    return json.dumps([kind, who, screen, list(bucket) if isinstance(bucket, tuple) else bucket])


class TypedProvider:
    """One answer per (decision, kind of person, screen, situation), asked a few times and averaged."""
    name = "spark"

    def __init__(self, cfg, design_path, table_path, model=CONTRIBUTOR, images=None, repeats=3, env=None):
        self.cfg, self.pack, self.brief = cfg, packs.of(cfg), cfg.get("brief")
        d = json.loads(Path(design_path).read_text())
        self.types = kinds(d)
        self._design = {t["id"]: t for t in d["types"]}
        self.path, self.model, self.repeats, self.env = Path(table_path), model, repeats, env
        self.images = images or {}      # image name -> file (uploaded screens); else the pack's rendered screens
        self._file = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.entries = self._file.get("entries", {})
        self.cost = 0.0

    def describe(self, type_id, age):
        t = self._design[type_id]
        side = dict(self.pack["sides"]).get(t.get("side"), "")
        if side in t["persona"]:       # Wonder sometimes repeats the side's sentence in the persona
            side = ""
        return " ".join(x for x in [t["persona"].format(age=age), side,
                                    t["work"].format(job=wonder_article(t["jobs"][0]))] if x)

    def keys(self):
        contexts = sorted(set(self.pack["channel_context"].values()))
        ads = sorted({a for k in self.cfg["plans"] for a in packs.experiment_ads(self.brief, k)})
        for t in self.types:
            for c in contexts:
                if not self.brief:
                    yield ("install", t["id"], c, "-")
                elif self.pack["context_screen"][c] == "ad":
                    yield from (("install", t["id"], c, a) for a in ads)
                else:
                    yield ("install", t["id"], c, "store")
            if self.brief:
                yield ("sign_up", t["id"], packs.signup_screen(self.pack), "-")
            gates = [self.pack["gates"][t["side"]]] if "side" in t else sorted(set(self.pack["gates"].values()))
            for g in gates:
                for b in BUCKETS:
                    for screen in sorted({gate_key(self.pack, p, g) for p in self.cfg["plans"].values()}):
                        yield (g, t["id"], screen, b)
                    if self.brief:
                        yield ("why_quit", t["id"], g, b)

    def _image(self, name):
        return self.images.get(name) or screens.path(name)

    def _prompt(self, key):
        """(persona, image name, question, options, answer shape) for one key. Shapes: "v1" one reason,
        "each" a reason for every choice, "reason" a reason only (why_quit)."""
        kind, who, screen, bucket = key
        lo, hi = self._design[who]["age_min"], self._design[who]["age_max"]
        persona = self.describe(who, (lo + hi) // 2)
        app = self.cfg["app"]
        if kind == "install":
            if bucket == "-":
                return (persona, screens.install_screen(screen, self.pack), self.pack["contexts"][screen],
                        ("install", "scroll_past"), "v1")
            ad = next((a for a in self.brief["ads"] if a["id"] == bucket), None)
            image = packs.ad_screen(self.pack, bucket) if ad else self.pack.get("screen_prefix", "") + "store"
            return persona, image, install_question(self.pack, screen, self.brief, ad), ("install", "scroll_past"), "each"
        if kind == "sign_up":
            return persona, screen, signup_question(app, self.brief), ("finish", "delete_app"), "each"
        gate, price = price_override(screen) if kind != "why_quit" else (screen, None)
        gate = gate if kind == "why_quit" else kind
        g = self.pack["gate"][gate]
        success, near, week = bucket
        persona += " " + " ".join([g["week"][week], g["success"][success], g["nearby"][near]])
        image = screens.gate_screen(gate, bucket, self.pack)
        if kind == "why_quit":
            return persona, image, why_quit_question(app, self.brief), ("quit",), "reason"
        return persona, image, gate_question(g["question"], self.brief, price), g["options"], "v1"

    def _q(self, key):
        persona, image, question, *_ = self._prompt(key)
        return hashlib.sha256(f"{self.model}|{persona}|{image}|{question}".encode()).hexdigest()[:12]

    def _fresh(self, key):
        e = self.entries.get(_key_str(key))
        return e is not None and e.get("q", self._q(key)) == self._q(key)

    def _request(self, key):
        persona, image, question, options, shape = self._prompt(key)
        schema = {"v1": spark._schema(options), "each": _each_schema(options), "reason": REASON_SCHEMA}[shape]
        body = {
            "model": self.model, "reasoning_effort": spark.EFFORT, "max_tokens": 6000,
            "messages": [
                {"role": "system", "content": spark.SYSTEM + "\n\n" + persona},
                {"role": "user", "content": [{"type": "image_url", "image_url": {"url": _data_url(self._image(image))}},
                                             {"type": "text", "text": question}]},
            ],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "decision", "strict": True, "schema": schema}},
        }
        return body, options

    def prefill(self, keys=None, workers=24, progress=None):
        """Ask every missing key `repeats` times in parallel and save the table."""
        todo = [k for k in (keys or list(self.keys())) if not self._fresh(k)]
        if not todo:
            return 0.0
        self.env = self.env or load_env()
        jobs = [k for k in todo for _ in range(self.repeats)]
        done = [0]

        def ask(k):
            body, _ = self._request(k)
            out = spark.ask_body(self.env, body, k)
            done[0] += 1
            if progress:
                progress(done[0], len(jobs))
            return out

        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(ask, jobs))
        cost = 0.0
        for i, key in enumerate(todo):
            answers = [results[i * self.repeats + j][0] for j in range(self.repeats)]
            cost += sum(results[i * self.repeats + j][1] for j in range(self.repeats))
            *_, options, shape = self._prompt(key)
            e = {"q": self._q(key)}
            if shape == "reason":
                e.update(probs={"quit": 1.0}, reasons=[a["reason"] for a in answers])
            else:
                probs = {a: statistics.mean(max(0.0, float(x["probabilities"][a])) for x in answers) for a in options}
                total = sum(probs.values()) or 1.0
                e["probs"] = {a: v / total for a, v in probs.items()}
                if shape == "each":
                    e["by_choice"] = [a["reasons"] for a in answers]
                else:
                    e["reasons"] = [a["reason"] for a in answers]
                e["noticed"] = [a["noticed"] for a in answers]
            self.entries[_key_str(key)] = e
        self.cost += cost
        self.save()
        return cost

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({**self._file, "model": self._file.get("model", self.model),
                                         "repeats": self._file.get("repeats", self.repeats),
                                         "entries": dict(sorted(self.entries.items()))}, indent=1))

    def decide(self, kind, who, screen, bucket):
        key = (kind, who, screen, bucket)
        if not self._fresh(key):
            self.prefill([key])
        return self.entries[_key_str(key)]["probs"]

    def answer(self, kind, who, screen, bucket):
        e = self.entries[_key_str((kind, who, screen, bucket))]
        if "by_choice" in e:
            each = e["by_choice"][0]
            return {"probs": e["probs"], "reason": each[max(e["probs"], key=e["probs"].get)], "reasons": each}
        return {"probs": e["probs"], "reason": e["reasons"][0]}


REASON_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["reason"],
    "properties": {"reason": {"type": "string", "description": "One short sentence in your own voice, under 15 words."}},
}


def _each_schema(options):
    """The decision schema with a reason for every choice instead of one."""
    s = spark._schema(options)
    s["properties"].pop("reason")
    s["properties"]["reasons"] = {
        "type": "object", "additionalProperties": False, "required": list(options),
        "properties": {o: {"type": "string", "description": "One short sentence in your own voice, under 15 words: "
                                                            "why you would do this if you did."} for o in options}}
    s["required"] = ["noticed", "probabilities", "reasons"]
    return s


def kinds(design):
    """Wonder's design as the kinds of people the simulation draws from."""
    return [{"id": t["id"], "name": t["name"], "weight": t["share"], "age": [t["age_min"], t["age_max"]],
             **({"side": t["side"]} if "side" in t else {})} for t in design["types"]]


def wonder_article(job):
    return ("an " if job[0].lower() in "aeiou" else "a ") + job


def paths(cfg):
    app = cfg["app"].lower()
    return ROOT / "data" / "wonder" / f"{app}_people.json", ROOT / "data" / "decisions" / f"{app}_spark.json"


def main(plan_file):
    from engine.run import load_plan
    cfg = load_plan(ROOT / plan_file)
    pack = packs.of(cfg)
    design_path, table_path = paths(cfg)
    if not design_path.exists():
        pre = pack.get("screen_prefix", "")
        gates = sorted(set(pack["gates"].values()))
        images = [screens.path(pre + "ad"), screens.path(pre + "store")] + \
                 [screens.path(screens.gate_screen(g, ("no", "few", "w1"), pack)) for g in gates]
        d = design(cfg, images, design_path)
        for t in d["types"]:
            print(f"{t['share']:.2f} {t.get('side', '')} {t['id']} {t['age_min']}-{t['age_max']}: {t['persona']}")
        print(d["rationale"])
    p = TypedProvider(cfg, design_path, table_path)
    keys = list(p.keys())
    if pack["id"] == "dating":          # the dating demo: Glimmer answers what it was trained on
        from .glimmer import trained_on
        keys = [k for k in keys if not trained_on(k[0], k[3])]
    cost = p.prefill(keys, progress=lambda i, n: print(f"\r{i}/{n}", end="", flush=True) if i % 50 == 0 or i == n else None)
    print(f"\n{len(p.entries)} keys · this run ${cost:.3f} -> {table_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1])
