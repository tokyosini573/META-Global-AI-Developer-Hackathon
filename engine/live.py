"""A rehearsal run live from uploaded screens and two plans. For the site's admin only.

The public site plays precomputed replays. The admin can instead upload an app's own screens (its ad,
its store page and the screen each side uses), set the two plans, and run them:

    1. Muse Wonder reads the screens and plans and designs the kinds of people (engine/world/typed.py)
    2. Muse Spark standard answers each decision once per kind of person: uploaded screens are not sent
       where they may be used for training
    3. the engine calibrates and runs both plans 30 times (engine/run.py rehearse)
    4. Muse Wonder writes why the winner won

A run takes a few minutes and costs well under a dollar, so it needs the admin key (ADMIN_KEY in .env
or in the host's secrets) and there is a daily cap. Runs live in runs/live/<id>/ (not committed).

The servers (engine/serve.py locally, engine/site_modal.py on Modal) expose:
    POST /api/live                      multipart: spec (JSON) + one image per screen -> {"id"}
    GET  /api/live/<id>                 -> progress
    GET  /api/live/<id>/replay          -> the replay, in the same format as web/public/replays
    GET  /api/live/<id>/screen/<name>   -> an uploaded screen, for the one-person drawer
"""

import copy
import json
import os
import re
import threading
import time
import traceback
import uuid
from pathlib import Path

import yaml

from engine import packs
from engine.world import channels, geo, screens, typed
from engine.world.decide import DecisionCache

ROOT = Path(__file__).resolve().parent.parent
DIR = Path(os.environ.get("LIVE_DIR", ROOT / "runs" / "live"))
EXAMPLES = {"dating": "kindred", "resale": "reloop", "rides": "hopway"}   # each market's plan file
DAILY = 10
STEPS = ["Reading your screens and plans", "Muse Wonder is designing the people",
         "Muse Spark is deciding for each kind of person", "Running both plans 30 times",
         "Muse Wonder is writing why the winner won"]
JOBS = {}
_today = {"day": "", "n": 0}
_lock = threading.Lock()


def screen_slots(pack_id):
    """The images a run needs: the ad, the store page, and the screen each side uses."""
    pack = packs.load(pack_id)
    return ["ad", "store"] + sorted(set(pack["gates"].values()))


def build_cfg(spec):
    """The example plan file for the market, with the admin's app, days and plans in place of the example's."""
    pack_id = spec["pack"]
    cfg = yaml.safe_load((ROOT / "plans" / f"{EXAMPLES[pack_id]}.yaml").read_text())
    cfg["app"] = re.sub(r"[^A-Za-z0-9 ]", "", spec.get("app") or cfg["app"]).strip()[:24] or cfg["app"]
    cfg["days"] = max(30, min(int(spec.get("days", cfg["days"])), 180))
    metro = {m[0]: m for m in geo.METROS}
    pack = packs.load(pack_id)
    sides = [s for s, _ in pack["sides"]]
    plans = {}
    for k in ("a", "b"):
        p = spec["plans"][k]
        cities = [{"name": c["name"], "lon": metro[c["name"]][1], "lat": metro[c["name"]][2],
                   "open_day": max(0, int(c.get("open_day", 0)))} for c in p.get("cities", []) if c["name"] in metro]
        chans = []
        for c in p["channels"]:
            assert c["kind"] in channels.KINDS, c["kind"]
            where = "cities" if cities and c.get("where", "cities") == "cities" else "nationwide"
            if c["kind"] == "event" and where != "cities":
                continue
            ch = {"kind": c["kind"], "where": where, "budget_share": float(c["budget_share"]),
                  "start_day": max(0, int(c["start_day"])), "end_day": min(cfg["days"], int(c["end_day"]))}
            if c.get("side") in sides:
                ch["side"] = c["side"]
            if ch["end_day"] > ch["start_day"]:
                chans.append(ch)
        assert chans, f"plan {k} has no channel"
        total = sum(c["budget_share"] for c in chans) or 1.0
        for c in chans:
            c["budget_share"] /= total
        base = cfg["plans"][k]
        plan = {"name": f"Plan {k.upper()}", "summary": p.get("summary") or base["summary"],
                "budget_usd": max(1000, min(float(p.get("budget_usd", cfg["budget_usd"])), 1_000_000)),
                "channels": chans, "events": [{"day": c["open_day"], "label": c["name"].split(",")[0]} for c in cities]
                or [{"day": 0, "label": "Nationwide"}]}
        if cities:
            plan["cities"] = cities
        if pack_id == "dating":
            plan["trial_days"] = max(0, int(p.get("trial_days", 0)))
            plan["free_swipes_per_day"] = max(1, int(p.get("free_swipes_per_day", 5)))
            plan["unlimited_swipes_per_day"] = base["unlimited_swipes_per_day"]
        plans[k] = plan
    cfg["plans"] = plans
    cfg["budget_usd"] = plans["a"]["budget_usd"]
    return cfg


def start(spec, images, env):
    """Check the request, save the uploads, and start the run in the background. Returns the run id."""
    day = time.strftime("%Y-%m-%d")
    with _lock:
        if _today["day"] != day:
            _today.update(day=day, n=0)
        if _today["n"] >= DAILY:
            raise PermissionError("The daily limit of live runs is reached.")
        _today["n"] += 1
    if spec.get("pack") not in EXAMPLES:
        raise ValueError("unknown market")
    missing = [s for s in screen_slots(spec["pack"]) if s not in images]
    if missing:
        raise ValueError("missing screens: " + ", ".join(missing))
    cfg = build_cfg(spec)
    rid = uuid.uuid4().hex[:12]
    d = DIR / rid
    d.mkdir(parents=True)
    for name, data in images.items():
        if name in screen_slots(spec["pack"]):
            (d / f"{name}.png").write_bytes(data)
    (d / "plans.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    JOBS[rid] = {"state": "running", "step": 0, "steps": STEPS, "done": 0, "total": 0, "error": None,
                 "started": time.time()}
    threading.Thread(target=_run, args=(rid, cfg, env), daemon=True).start()
    return rid


def _image_map(pack, d):
    """Every image name the pack's decisions ask for -> the uploaded file for that screen."""
    pre = pack.get("screen_prefix", "")
    out = {pre + "ad": d / "ad.png", pre + "store": d / "store.png"}
    for gate in set(pack["gates"].values()):
        for m in ("no", "yes"):
            for n in screens.NEARBY:
                out[screens.gate_screen(gate, (m, n, "w1"), pack)] = d / f"{gate}.png"
    return out


def _run(rid, cfg, env):
    from engine.run import rehearse
    job = JOBS[rid]
    d = DIR / rid
    try:
        pack = packs.of(cfg)
        cfg["verdict_cache"] = str(d / "verdicts.json")
        images = _image_map(pack, d)
        job["step"] = 1
        typed.design(cfg, [d / f"{s}.png" for s in screen_slots(pack["id"])], d / "people.json")
        job["step"] = 2
        provider = typed.TypedProvider(cfg, d / "people.json", d / "decisions.json", model=typed.STANDARD,
                                       images={k: str(v) for k, v in images.items()}, repeats=2, env=env)

        def progress(i, n):
            job["done"], job["total"] = i, n
        provider.prefill(progress=progress)
        job["step"] = 3
        cache = DecisionCache(provider)
        rep, summary, _ = rehearse(cfg, cache, 30, use_wonder=False, log=lambda *a: None)
        job["step"] = 4
        try:
            from engine.run import wonder_reason
            w = rep["verdict"]["winner"]
            goal = pack["goal_key"]
            runs = summary["runs"]
            wins = sum(r[w][goal] > r["b" if w == "a" else "a"][goal] for r in runs)
            rep["verdict"]["reason"] = f"{wonder_reason(cfg, runs, rep)} {cfg['plans'][w]['name']} won {wins} of {len(runs)} runs."
        except (SystemExit, Exception):     # keep the plain win-count reason if Wonder fails or uses a number
            pass
        for ppl in rep["people"].values():   # the drawer shows the uploaded screens
            for p in ppl:
                s = p["story"]
                for f in ("ad", "last"):
                    if s.get(f):
                        s[f] = f"/api/live/{rid}/screen/{images[s[f]].stem}"
        rep["meta"]["pack"]["screens"] = [f"/api/live/{rid}/screen/{s}" for s in screen_slots(pack["id"])]
        rep["meta"]["live"] = True
        (d / "replay.json").write_text(json.dumps(rep, separators=(",", ":")))
        job["state"] = "done"
    except Exception as e:
        traceback.print_exc()
        job["state"], job["error"] = "error", str(e)[:300]


def status(rid):
    job = JOBS.get(rid)
    if not job:
        raise KeyError(rid)
    return {k: job[k] for k in ("state", "step", "steps", "done", "total", "error")}


def replay(rid):
    if not re.fullmatch(r"[a-z0-9]{12}", rid):
        raise KeyError(rid)
    return (DIR / rid / "replay.json").read_bytes()


def screen(rid, name):
    if not re.fullmatch(r"[a-z0-9]{12}", rid) or not re.fullmatch(r"[a-z_]+", name):
        raise KeyError(name)
    return (DIR / rid / f"{name}.png").read_bytes()


def authorized(env, key):
    admin = env.get("ADMIN_KEY", "").strip()      # a pasted key often carries a space or a newline
    return bool(admin) and key.strip() == admin


def example_spec(pack_id):
    """The example plans of a market as a spec, so the admin form starts filled in."""
    cfg = yaml.safe_load((ROOT / "plans" / f"{EXAMPLES[pack_id]}.yaml").read_text())
    plans = {}
    for k, p in cfg["plans"].items():
        q = {"summary": p["summary"], "budget_usd": p.get("budget_usd", cfg["budget_usd"]),
             "cities": [{"name": c["name"], "open_day": c["open_day"]} for c in p.get("cities", [])],
             "channels": copy.deepcopy(p["channels"])}
        if pack_id == "dating":
            q["trial_days"], q["free_swipes_per_day"] = p["trial_days"], p["free_swipes_per_day"]
        plans[k] = q
    pack = packs.load(pack_id)
    two = pack["mechanics"] == "transaction"
    labels = {"ad": "The ad", "store": "The store page"}
    for side, gate in pack["gates"].items():
        labels[gate] = f"What a {side} sees" if two else "The paywall"
    return {"pack": pack_id, "app": cfg["app"], "days": cfg["days"], "plans": plans,
            "slots": [{"name": s, "label": labels[s], "example": f"/screens/{example_screen(pack, s)}.png"}
                      for s in screen_slots(pack_id)],
            "sides": [s for s, _ in pack["sides"]] if two else [], "metros": [m[0] for m in geo.METROS]}


def example_screen(pack, slot):
    """The demo app's own image for an upload slot, so the admin form starts with the example's screens."""
    pre = pack.get("screen_prefix", "")
    return pre + slot if slot in ("ad", "store") else screens.gate_screen(slot, ("no", "few", "w1"), pack)
