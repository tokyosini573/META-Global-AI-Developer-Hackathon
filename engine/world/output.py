"""Write a finished rehearsal: replay JSON for the screen, SQLite for analysis.

The replay is version 2 (docs/replay-format.md "Version 2"): the full funnel, each person's ad,
sign-up and the words that stopped them, the spread across runs and the ads table.
"""

import copy
import json
import math
import sqlite3

import numpy as np

from engine import packs

from . import channels, screens
from .decide import TYPES

NOTE = "Simulated, calibrated to public benchmarks. Not observed."


def _day(d, days):
    return round(d, 2) if d is not None and d <= days else None


def _diary_day(d):
    return math.floor(d) + 1     # day 0.4 of the run is "Day 1" on screen


def story(p, decisions, provider, trial_days, days, pack=None):
    """What the one-person drawer shows: the screens they saw, a short diary, why they stopped and the
    first funnel step they never reached.

    A decision gets the person's own words only when they fit what the person did: the reason given
    for that choice (v2 answers keep one per choice), or else the one reason, when they did what the
    model thought most likely.
    """
    def words(d):
        if d is None or not hasattr(provider, "answer"):
            return None
        _, _, kind, screen, bucket, _, chosen = d
        a = provider.answer(kind, p.persona or p.type, screen, bucket)
        if chosen in (a.get("reasons") or {}):
            return a["reasons"][chosen]
        return a["reason"] if chosen == max(a["probs"], key=a["probs"].get) else None

    def by(day):
        return day is not None and day <= days

    pack = pack or packs.load("dating")
    st = pack["story"]
    nearest = st["nearest"]
    gate = pack["gates"][p.side]
    outcome = st["outcome"][gate]

    mine = [d for d in decisions if d[0] <= days]
    install = next(d for d in mine if d[2] == "install")
    signup = next((d for d in mine if d[2] == "sign_up"), None)
    why = next((d for d in mine if d[2] == "why_quit"), None)
    skip = st["skip"].get(p.channel, st["skip_default"])
    diary = [[_diary_day(p.reached), f"{st['reach'][p.channel]} {'Installed it.' if p.installed is not None else skip}",
              words(install)]]
    if signup:
        diary.append([_diary_day(p.installed), st["signup"][signup[6]], words(signup)])
    success = [_diary_day(p.matched), st["success"][p.side], None] if by(p.matched) else None
    if success and pack["mechanics"] == "swipe":
        diary.append(success)
    walls = [d for d in mine if d[2] == gate]
    deleted = bool(walls) and walls[-1][6] == "delete_app"
    quit_reason = None
    if by(p.quit):
        quit_reason = (words(signup) if signup and signup[6] == "delete_app"
                       else (deleted and words(walls[-1])) or words(why))
    if walls:
        first, last = walls[0], walls[-1]

        def said_at(d):      # a delete carries the words for quitting (theirs, or why they stopped)
            return quit_reason if d is last and deleted else words(d)
        head = st.get("trial_head", "") if trial_days else ""
        diary.append([first[0] + 1, f"{head}{st['gate_head'][gate]} {nearest(first[4], p.side)} {outcome[first[6]]}",
                      said_at(first)])
        if last is not first and last[6] != "come_back_tomorrow":
            diary.append([last[0] + 1, f"{nearest(last[4], p.side)} {outcome[last[6]]}", said_at(last)])
    if success and pack["mechanics"] == "transaction":    # after the same day's ask that led to it
        diary.append(success)
    if by(p.quit) and not deleted and not (signup and signup[6] == "delete_app"):
        diary.append([_diary_day(p.quit), "Stopped opening the app.", quit_reason])
    diary.sort(key=lambda x: x[0])

    reached = {"saw": True, "installed": by(p.installed), "signed_up": by(p.signed_up), "first": by(p.matched),
               "active": by(p.signed_up) and not by(p.quit), "paid": by(p.paid)}
    to = next((k for k, _ in pack["funnel"] if not reached[k]), None)
    said = {"installed": lambda: words(install), "signed_up": lambda: words(signup),
            "first": lambda: quit_reason, "active": lambda: quit_reason,
            "paid": lambda: words(walls[-1]) if walls else None}
    who = getattr(provider, "pool", {}).get(p.persona, {})
    persona = who.get("text") or (provider.describe(p.type, p.age) if hasattr(provider, "describe") else None)
    out = {"sex": p.side, "persona": persona,
           "ad": packs.ad_screen(pack, p.ad_id) if p.ad_id else screens.install_screen(install[3], pack),
           "last": screens.gate_screen(gate, walls[-1][4], pack) if walls else None, "diary": diary,
           "quit_reason": quit_reason}
    if to:
        out["stop"] = {"to": to, "words": said[to]()}
    return out


def plan_card(cfg, plan):
    """The plan in plain words, for the input screen."""
    cities = plan.get("cities", [])
    together = len(cities) > 1 and len({c["open_day"] for c in cities}) == 1
    names = [c["name"].split(",")[0] for c in cities]
    if together:
        where = ", ".join(names[:-1]) + f" and {names[-1]} from day {cities[0]['open_day'] + 1}"
    elif cities:
        where = names[0] + "".join(f", then {n} on day {c['open_day']}" for n, c in zip(names[1:], cities[1:]))
    else:
        where = "Nationwide from day 1"
    pack = packs.of(cfg)
    words = pack.get("ad_words", {})      # the demo's own names for its channels (dating: TikTok, ambassadors)

    def ad(c):
        if c["kind"] in words:
            return words[c["kind"]][1 if cities else 0]
        return channels.LABELS[c["kind"]].lower() + (", nationwide" if c["where"] == "nationwide" and cities else "")
    kinds = {}                            # one phrase per kind of channel, with the sides it is aimed at
    for c in sorted(plan["channels"], key=lambda c: c["kind"] != "event"):
        kinds.setdefault(c["kind"], (c, []))[1].append(c.get("side"))
    phrases = [ad(c) + (" to " + " and ".join(s + "s" for s in sides) if all(sides) else "")
               for c, sides in kinds.values()]
    ads = ", ".join(phrases[:-1]) + (" and " if len(phrases) > 1 else "") + phrases[-1]
    title = "All at once" if together else "City by city" if cities else "Nationwide"
    return {"title": title, "where": where, "ads": ads[0].upper() + ads[1:], "price": pack["price_words"](cfg, plan)}



def input_screens(pack):
    """What people see, as the input screen shows it: the ad, the store page and each side's screen."""
    pre = pack.get("screen_prefix", "")
    nearby = "none" if pack["mechanics"] == "swipe" else "few"   # dating's paywall with nobody near; a feed with a few
    return [pre + "ad", pre + "store"] + [screens.gate_screen(g, ("no", nearby, "w1"), pack)
                                          for g in sorted(set(pack["gates"].values()))]


def brief_images(pack, brief):
    """The brief's image slots (docs/brief-format.md "Images") -> the screen names this run used."""
    pre = pack.get("screen_prefix", "")
    out = {"store": pre + "store", "signup": packs.signup_screen(pack)}
    if pack["mechanics"] == "swipe":
        out["paywall"] = screens.gate_screen("paywall", ("no", "none", "w1"), pack)
    else:
        for side, gate in pack["gates"].items():
            out[f"main_{side}"] = screens.gate_screen(gate, ("no", "few", "w1"), pack)
    for a in brief.get("ads", []):
        out[a["id"]] = packs.ad_screen(pack, a["id"])
    return out


def _ranges(funnels, k):
    """10th-90th percentile of each funnel step across runs, in simulated people."""
    keys = funnels[0][k]
    return {key: [int(round(np.percentile([f[k][key] for f in funnels], q))) for q in (10, 90)] for key in keys}


def _mean_cells(cells, k):
    one = cells[0][k]
    return {kind: {ad: [int(round(np.mean([c[k][kind][ad][i] for c in cells]))) for i in (0, 1)] for ad in ads}
            for kind, ads in one.items()}


def replay(cfg, results, verdict, provider, funnels=None, cells=None):
    """results: {plan key: Result} from one representative run (docs/replay-format.md). funnels and cells:
    per run, {plan key: funnel counts} and {plan key: ad cells} (engine/world/sim.py), for the spread
    across runs and the ads table (averaged over runs, so a single run's luck does not pick an ad)."""
    days = cfg["days"]
    pack = packs.of(cfg)
    brief = cfg.get("brief")
    decisions_source = provider.name
    experiments = ((brief or {}).get("setup") or {}).get("experiments", {})
    plans = {k: {"name": p["name"], "summary": p["summary"], "events": p["events"], "card": plan_card(cfg, p),
                 "changes": experiments.get(k, {}).get("changes", p["summary"])}
             for k, p in cfg["plans"].items()}
    for k, plan in plans.items():
        if funnels:
            plan["range"] = _ranges(funnels, k)
        if cells:
            plan["ads"] = {"line": "", "cells": _mean_cells(cells, k)}
    people = {}
    for k, res in results.items():
        mine = {}
        for d in res.decisions:
            mine.setdefault(d[1], []).append(d)
        trial = cfg["plans"][k].get("trial_days", 0)
        people[k] = [{"id": p.id, "name": p.name, "age": p.age, "place": p.place,
                      "lon": round(p.lon, 3), "lat": round(p.lat, 3), "reached": _day(p.reached, days),
                      "installed": _day(p.installed, days), "matched": _day(p.matched, days),
                      "quit": _day(p.quit, days), "paid": _day(p.paid, days),
                      "kind": p.type, "ad_id": p.ad_id, "signed_up": _day(p.signed_up, days),
                      "story": story(p, mine[p.id], provider, trial, days, pack)}
                     for p in res.people if p.reached <= days]
    ads = brief["ads"] if brief else [{"id": "ad_1", "angle": "other", "line": ""}]
    shown = {a for k in cfg["plans"] for a in packs.experiment_ads(brief, k)}
    meta_brief = None
    if brief:
        meta_brief = copy.deepcopy(brief)
        meta_brief["images"] = brief_images(pack, brief)
    kinds = [{"id": t["id"], "name": t.get("name") or t["id"].replace("_", " ").capitalize(),
              "share": round(t["weight"], 4), **({"side": t["side"]} if "side" in t else {})}
             for t in getattr(provider, "types", TYPES)]
    agents = ((brief or {}).get("setup") or {}).get("people") or round(np.mean([len(v) for v in people.values()]))
    return {
        "version": 2,
        "meta": {"app": cfg["app"], "market": cfg["market"], "days": days, "budget_usd": cfg["budget_usd"],
                 "pack": {"id": pack["id"], "header": pack["header"], "category": pack["category"],
                          "screens": input_screens(pack), **pack["labels"]},
                 "placeholder": decisions_source not in ("spark", "glimmer"), "people_per_dot": cfg["people_per_dot"],
                 "people_types": [k["name"] for k in kinds],
                 "brief": meta_brief, "note": NOTE, "agents": int(agents),
                 "funnel": [{"key": k, "label": label.format(days=days)} for k, label in pack["funnel"]],
                 "ads": [{"id": a["id"], "angle": a.get("angle", "other"), "line": a.get("line", ""),
                          "screen": packs.ad_screen(pack, a["id"])} for a in ads if a["id"] in shown],
                 "kinds": kinds},
        "plans": plans,
        "verdict": verdict,
        "people": people,
        "matches": {k: [m for m in res.matches if m[2] <= days] for k, res in results.items()},
    }


def write_sqlite(path, results, summary):
    path.unlink(missing_ok=True)
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE agents (plan TEXT, id INT, type TEXT, side TEXT, channel TEXT, place TEXT, lon REAL, lat REAL,
                             name TEXT, age INT, persona TEXT, reached REAL, installed REAL, matched REAL, quit REAL, paid REAL,
                             matches INT, PRIMARY KEY (plan, id));
        CREATE TABLE decisions (plan TEXT, day INT, person INT, kind TEXT, screen TEXT, bucket TEXT,
                                probs TEXT, chosen TEXT);
        CREATE TABLE matches (plan TEXT, a INT, b INT, day REAL);
        CREATE TABLE summary (key TEXT PRIMARY KEY, value TEXT);
    """)
    for k, res in results.items():
        db.executemany("INSERT INTO agents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       [(k, p.id, p.type, p.side, p.channel, p.place, p.lon, p.lat, p.name, p.age, p.persona, p.reached,
                         p.installed, p.matched, p.quit, p.paid, len(p.match_days)) for p in res.people])
        db.executemany("INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?)",
                       [(k, d[0], d[1], d[2], d[3], json.dumps(d[4]), json.dumps(d[5]), d[6]) for d in res.decisions])
        db.executemany("INSERT INTO matches VALUES (?,?,?,?)", [(k, *m) for m in res.matches])
    db.executemany("INSERT INTO summary VALUES (?,?)", [(k, json.dumps(v)) for k, v in summary.items()])
    db.commit()
    db.close()
