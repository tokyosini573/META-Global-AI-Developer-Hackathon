"""A rehearsal run live from an uploaded brief and screens. For the site's admin only.

The public site plays precomputed replays. The admin can instead fill in an app's brief
(docs/brief-format.md: what the app is, and the two experiments to try) on the Setup page, upload
its screens, and run both experiments:

    1. Muse Wonder reads the screens and the brief and designs the kinds of people (engine/world/typed.py)
    2. Muse Spark standard answers each decision once per kind of person: uploaded screens are not sent
       where they may be used for training
    3. the engine calibrates and runs both experiments 30 times (engine/run.py rehearse)
    4. Muse Wonder writes why the winner won, and sorts why people left into themes (engine/world/report.py)

A run takes a few minutes and costs well under a dollar, so it needs the admin key (ADMIN_KEY in .env
or in the host's secrets) and there is a daily cap. Runs live in runs/live/<id>/ (not committed).

The servers (engine/serve.py locally, engine/site_modal.py on Modal) expose:
    POST /api/live                      multipart: brief (JSON) + one image per name in image_slots -> {"id"}
    GET  /api/live/<id>                 -> progress
    GET  /api/live/<id>/replay          -> the replay, in the same format as web/public/replays
    GET  /api/live/<id>/screen/<name>   -> an uploaded screen, for the drawer and the Setup page
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
RUNS = 30                    # Monte Carlo runs per experiment
STEPS = ["Reading your brief and screens", "Muse Wonder is designing the people",
         "Muse Spark is deciding for each kind of person", "Running both experiments 30 times",
         "Muse Wonder is writing why the winner won and why people left"]
JOBS = {}
_today = {"day": "", "n": 0}
_lock = threading.Lock()

# The brief's choices and text limits (docs/brief-format.md)
PEOPLE = (1000, 5000, 10000)
DAYS = (7, 14, 30, 90)
ANGLES = ("feature", "price", "trust", "other")
SIGNUP = ("email", "phone", "apple", "google", "facebook")
PERMISSIONS = ("location", "camera", "photos", "contacts", "notifications")
INCOME = ("under_30k", "30_60k", "60_100k", "over_100k", "mixed")
NEW_APPS = ("early", "friends", "rarely")
MODELS = ("subscription", "service_fee", "per_ride_fee", "one_time")
PER = ("week", "month", "transaction", "percent")
PAYWALL = ("after_signup", "after_free_limit", "after_trial", "at_checkout")
MAX_ADS = 3
IMAGE_TYPES = {b"\x89PNG": "image/png", b"\xff\xd8\xff": "image/jpeg", b"RIFF": "image/webp"}


def image_slots(category, n_ads=MAX_ADS):
    """The images a run needs (docs/brief-format.md "Images"), as web/src/brief.ts imageSlots."""
    main = {"dating": ["main", "paywall"]}.get(category) or [f"main_{s}" for s, _ in packs.load(category)["sides"]]
    return ["store", "signup", *main, *[f"ad_{i + 1}" for i in range(n_ads)]]


def screen_name(pack, slot):
    """The demo screen (web/public/screens/<name>.png) or decision screen an upload slot stands for."""
    pre = pack.get("screen_prefix", "")
    if slot == "ad_1":
        return pre + "ad"
    if slot == "paywall" or slot.startswith("main_"):
        side = slot[5:] if slot.startswith("main_") else pack["sides"][0][0]
        return screens.gate_screen(pack["gates"][side], ("no", "few", "w1"), pack)
    return pre + slot                  # store, signup, main, ad_2, ad_3


def _text(v, n):
    return " ".join(str(v).split())[:n] if v is not None else ""


def _pick(v, choices, default):
    return v if v in choices else default


def _snap(v, choices):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return choices[-1]
    return min(choices, key=lambda c: abs(c - v))


def clean_brief(brief):
    """The brief with every field checked and trimmed to docs/brief-format.md; unknown fields are dropped."""
    cat = brief.get("category")
    if cat not in EXAMPLES:
        raise ValueError("unknown category")
    pack = packs.load(cat)
    b = {"version": 2, "app": re.sub(r"[^A-Za-z0-9 ]", "", str(brief.get("app") or "")).strip()[:24],
         "category": cat, "market": "United States"}
    if not b["app"]:
        raise ValueError("the app needs a name")
    p = brief.get("profile") or {}
    b["profile"] = {"does": _text(p.get("does"), 300), "why": _text(p.get("why"), 200),
                    "features": [_text(f, 40) for f in (p.get("features") or [])[:5] if _text(f, 40)]}
    a = brief.get("audience") or {}
    lo, hi = pack["age"]
    try:
        age = sorted(max(lo, min(int(x), hi)) for x in a.get("age", (lo, hi))[:2])
    except (TypeError, ValueError):
        age = [lo, hi]
    b["audience"] = {"age": age if len(age) == 2 else [lo, hi], "who": _text(a.get("who"), 200)}
    for key, n in (("lifestyle", 120), ("interests", 120)):
        if _text(a.get(key), n):
            b["audience"][key] = _text(a.get(key), n)
    for key, choices in (("income", INCOME), ("new_apps", NEW_APPS)):
        if a.get(key) in choices:
            b["audience"][key] = a[key]
    pr = brief.get("product") or {}
    b["product"] = {"signup_methods": [m for m in SIGNUP if m in (pr.get("signup_methods") or [])] or ["email"],
                    "permissions": [m for m in PERMISSIONS if m in (pr.get("permissions") or [])],
                    "free_limits": _text(pr.get("free_limits"), 80)}
    m = brief.get("money") or {}
    try:
        price = max(0.0, float(m.get("price", 0)))
    except (TypeError, ValueError):
        price = 0.0
    b["money"] = {"model": _pick(m.get("model"), MODELS, MODELS[0]), "price": price,
                  "per": _pick(m.get("per"), PER, PER[0]), "trial_days": max(0, min(int(m.get("trial_days") or 0), 90)),
                  "paywall": _pick(m.get("paywall"), PAYWALL, PAYWALL[0]),
                  "free": _text(m.get("free"), 120), "paid": _text(m.get("paid"), 120)}
    ads = []
    for ad in (brief.get("ads") or [])[:MAX_ADS]:
        ads.append({"id": f"ad_{len(ads) + 1}", "angle": _pick(ad.get("angle"), ANGLES, "other"),
                    "line": _text(ad.get("line"), 80)})
    if not ads:
        raise ValueError("the brief needs at least one ad")
    b["ads"] = ads
    for key, (f1, f2) in (("competition", ("now", "switch")), ("retention", ("back", "leave"))):
        x = brief.get(key) or {}
        if _text(x.get(f1), 200) or _text(x.get(f2), 200):
            b[key] = {f1: _text(x.get(f1), 200), f2: _text(x.get(f2), 200)}
    allowed = {"dating": ("women_share", "free_likes_per_day"), "resale": ("fee_share", "seller_share"),
               "rides": ("fare_usd", "driver_share")}[cat]
    extra = {}
    for k, v in (brief.get("extra") or {}).items():
        if k in allowed and isinstance(v, (int, float)):
            extra[k] = max(1, min(int(v), 100)) if k == "free_likes_per_day" else \
                max(1.0, min(float(v), 500.0)) if k == "fare_usd" else max(0.01, min(float(v), 0.99))
    if extra:
        b["extra"] = extra
    s = brief.get("setup") or {}
    ids = [ad["id"] for ad in ads]
    b["setup"] = {"people": _snap(s.get("people"), PEOPLE), "days": _snap(s.get("days"), DAYS)}
    if s.get("campaign"):
        c = s["campaign"]
        b["setup"]["campaign"] = {"budget_usd": c.get("budget_usd", 40000), "channels": c.get("channels") or [],
                                  "cities": c.get("cities") or [],
                                  "ads": [x for x in (c.get("ads") or ids) if x in ids] or ids}
    ex = s.get("experiments") or {}
    b["setup"]["experiments"] = {}
    for k in ("a", "b"):
        e = ex.get(k) or {}
        out = {"changes": _text(e.get("changes"), 120) or ("Nothing: the shared campaign" if k == "a" else "")}
        for f in ("budget_usd", "channels", "cities", "price", "trial_days"):
            if e.get(f) is not None:
                out[f] = e[f]
        if e.get("ads") is not None:
            out["ads"] = [x for x in e["ads"] if x in ids] or ids
        b["setup"]["experiments"][k] = out
    return b


def _plan(cfg, pack, base, shared, exp, k):
    """One experiment's plan: the shared campaign with this experiment's changes (live runs)."""
    metro = {m[0]: m for m in geo.METROS}
    sides = [s for s, _ in pack["sides"]]
    days = cfg["days"]
    p = {**shared, **{f: exp[f] for f in ("budget_usd", "channels", "cities") if f in exp}}
    cities = [{"name": c["name"], "lon": metro[c["name"]][1], "lat": metro[c["name"]][2],
               "open_day": max(0, int(c.get("open_day", 0)))} for c in p.get("cities") or []
              if c.get("name") in metro and int(c.get("open_day", 0)) < days]
    chans = []
    for c in p.get("channels") or []:
        assert c["kind"] in channels.KINDS, c["kind"]
        where = "cities" if cities and c.get("where", "cities") == "cities" else "nationwide"
        if c["kind"] == "event" and where != "cities":
            continue
        ch = {"kind": c["kind"], "where": where, "budget_share": max(0.0, float(c.get("budget_share", 1))),
              "start_day": max(0, int(c.get("start_day", 0))), "end_day": min(days, int(c.get("end_day", days)))}
        if c.get("side") in sides:
            ch["side"] = c["side"]
        if ch["end_day"] > ch["start_day"]:
            chans.append(ch)
    assert chans, f"experiment {k} has no channel"
    total = sum(c["budget_share"] for c in chans) or 1.0
    for c in chans:
        c["budget_share"] = c["budget_share"] / total if total else 1 / len(chans)
    plan = {"name": f"Plan {k.upper()}", "summary": exp["changes"] or base["summary"], "changes": exp["changes"],
            "budget_usd": max(1000.0, min(float(p.get("budget_usd") or cfg["budget_usd"]), 1_000_000.0)),
            "channels": chans, "ads": exp.get("ads") or shared["ads"],
            "events": [{"day": c["open_day"], "label": c["name"].split(",")[0]} for c in cities]
            or [{"day": 0, "label": "Nationwide"}]}
    if cities:
        plan["cities"] = cities
    return plan


def build_cfg(brief, rid=None):
    """The example plan file for the brief's category, with the brief applied.

    App, days, people, price and the category's extra values come from the brief. With a shared
    campaign (live runs) plans A and B are that campaign plus each experiment's changes; without one
    (the demo apps' briefs) the example's plans stay and only take the experiments' words and ads.
    cfg["brief"] is the cleaned brief, with "images": {slot: image path} (/api/live/<rid>/screen/<slot>
    for a live run, else the demo app's /screens/<name>.png).
    """
    b = clean_brief(brief)
    cat = b["category"]
    pack = packs.load(cat)
    cfg = yaml.safe_load((ROOT / "plans" / f"{EXAMPLES[cat]}.yaml").read_text())
    cfg["app"] = b["app"]
    cfg["days"] = b["setup"]["days"]
    cfg["people"] = b["setup"]["people"]
    money, extra = b["money"], b.get("extra", {})
    if cat == "dating":
        if money["price"] > 0:
            cfg["price_per_week"] = round(money["price"] if money["per"] != "month" else money["price"] * 12 / 52, 2)
        if "women_share" in extra:
            cfg["world"]["share_male"] = round(1 - extra["women_share"], 3)
    elif cat == "resale":
        if "fee_share" in extra or money["per"] == "percent":
            cfg["fee_share"] = extra.get("fee_share", max(0.01, min(money["price"], 0.99)))
        if "seller_share" in extra:
            cfg["world"]["share_seller"] = extra["seller_share"]
    else:
        if "fare_usd" in extra or money["per"] == "transaction" and money["price"] > 0:
            cfg["fare_usd"] = extra.get("fare_usd", money["price"])
        if money["per"] == "percent" and money["price"] > 0:
            cfg["fee_share"] = max(0.01, min(money["price"], 0.99))
        if "driver_share" in extra:
            cfg["world"]["share_driver"] = extra["driver_share"]
    ids = [ad["id"] for ad in b["ads"]]
    shared = b["setup"].get("campaign")
    plans = {}
    for k in ("a", "b"):
        base, exp = cfg["plans"][k], b["setup"]["experiments"][k]
        if shared:
            plan = _plan(cfg, pack, base, shared, exp, k)
        else:
            plan = {**copy.deepcopy(base), "changes": exp["changes"], "ads": exp.get("ads") or ids}
            for c in plan["channels"]:
                c["end_day"] = min(c["end_day"], cfg["days"])
        if cat == "dating":
            plan["trial_days"] = int(exp.get("trial_days", base["trial_days"] if not shared else money["trial_days"]))
            plan["free_swipes_per_day"] = extra.get("free_likes_per_day", base["free_swipes_per_day"])
            plan["unlimited_swipes_per_day"] = base["unlimited_swipes_per_day"]
        if exp.get("price") is not None:       # an experiment's own price (docs/brief-format.md "price?")
            key = {"dating": "price_per_week", "resale": "fee_share", "rides": "fare_usd"}[cat]
            plan[key] = max(0.0, float(exp["price"]))
        plans[k] = plan
    cfg["plans"] = plans
    cfg["budget_usd"] = plans["a"].get("budget_usd", cfg["budget_usd"])
    b["images"] = {s: f"/api/live/{rid}/screen/{s}" if rid else f"/screens/{screen_name(pack, s)}.png"
                   for s in image_slots(cat, len(b["ads"]))}
    cfg["brief"] = b
    cfg["ads"] = [{**ad, "screen": screen_name(pack, ad["id"])} for ad in b["ads"]]
    return cfg


def image_type(data):
    """The image's media type from its first bytes, or None when it is not a PNG, JPEG or WebP."""
    return next((t for magic, t in IMAGE_TYPES.items() if data[:len(magic)] == magic), None)


def start(brief, images, env):
    """Check the request, save the uploads, and start the run in the background. Returns the run id."""
    if not isinstance(brief, dict):
        raise ValueError("bad brief")
    rid = uuid.uuid4().hex[:12]
    cfg = build_cfg(brief, rid)
    slots = image_slots(cfg["brief"]["category"], len(cfg["brief"]["ads"]))
    missing = [s for s in slots if s not in images]
    if missing:
        raise ValueError("missing images: " + ", ".join(missing))
    bad = [s for s in slots if not image_type(images[s])]
    if bad:
        raise ValueError("not a PNG, JPEG or WebP image: " + ", ".join(bad))
    day = time.strftime("%Y-%m-%d")
    with _lock:
        if _today["day"] != day:
            _today.update(day=day, n=0)
        if _today["n"] >= DAILY:
            raise PermissionError("The daily limit of live runs is reached.")
        _today["n"] += 1
    d = DIR / rid
    d.mkdir(parents=True)
    for s in slots:
        (d / f"{s}.png").write_bytes(images[s])
    (d / "plans.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    JOBS[rid] = {"state": "running", "step": 0, "steps": STEPS, "done": 0, "total": 0, "error": None,
                 "started": time.time()}
    threading.Thread(target=_run, args=(rid, cfg, env), daemon=True).start()
    return rid


def image_map(pack, d, slots):
    """Every image name the pack's decisions ask for -> the uploaded file for that screen."""
    pre = pack.get("screen_prefix", "")
    out = {}
    for s in slots:
        if s == "paywall" or s.startswith("main_"):
            side = s[5:] if s.startswith("main_") else None
            for gate in {pack["gates"][side]} if side else set(pack["gates"].values()):
                for m in ("no", "yes"):
                    for n in screens.NEARBY:
                        out[screens.gate_screen(gate, (m, n, "w1"), pack)] = d / f"{s}.png"
        else:
            out[pre + "ad" if s == "ad_1" else pre + s] = d / f"{s}.png"
    return out


def resolve_screens(rep, rid, images, slots):
    """Point every screen name in the replay at the run's uploads (/api/live/<rid>/screen/<slot>)."""
    url = lambda name: f"/api/live/{rid}/screen/{images[name].stem}"     # noqa: E731
    for ppl in rep["people"].values():
        for p in ppl:
            s = p.get("story") or {}
            for f, v in list(s.items()):
                if isinstance(v, str) and v in images:
                    s[f] = url(v)
    for ad in rep["meta"].get("ads", []):
        if ad.get("screen") in images:
            ad["screen"] = url(ad["screen"])
    rep["meta"].setdefault("pack", {})["screens"] = [f"/api/live/{rid}/screen/{s}" for s in slots]
    rep["meta"]["live"] = True


def _run(rid, cfg, env):
    from engine.run import rehearse
    from engine.world import report
    job = JOBS[rid]
    d = DIR / rid
    try:
        pack = packs.of(cfg)
        cfg["verdict_cache"] = str(d / "verdicts.json")
        slots = image_slots(pack["id"], len(cfg["brief"]["ads"]))
        images = image_map(pack, d, slots)
        job["step"] = 1
        typed.design(cfg, [d / f"{s}.png" for s in slots], d / "people.json")
        job["step"] = 2
        provider = typed.TypedProvider(cfg, d / "people.json", d / "decisions.json", model=typed.STANDARD,
                                       images={k: str(v) for k, v in images.items()}, repeats=2, env=env)

        def progress(i, n):
            job["done"], job["total"] = i, n
        provider.prefill(progress=progress)
        job["step"] = 3
        cache = DecisionCache(provider)
        rep, summary, _ = rehearse(cfg, cache, RUNS, use_wonder=False, log=lambda *a: None)
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
        report.build(rep, cfg, use_wonder=True, log=print)   # rehearse grouped identical sentences; now Wonder's themes
        rep["meta"]["brief"] = cfg["brief"]
        resolve_screens(rep, rid, images, slots)
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
    """(media type, bytes) of an uploaded screen."""
    if not re.fullmatch(r"[a-z0-9]{12}", rid) or not re.fullmatch(r"[a-z][a-z0-9_]{0,23}", name):
        raise KeyError(name)
    data = (DIR / rid / f"{name}.png").read_bytes()
    return image_type(data) or "application/octet-stream", data


def authorized(env, key):
    admin = env.get("ADMIN_KEY", "").strip()      # a pasted key often carries a space or a newline
    return bool(admin) and key.strip() == admin
