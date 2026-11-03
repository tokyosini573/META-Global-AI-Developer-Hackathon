"""Write a finished rehearsal: replay JSON for the screen, SQLite for analysis."""

import json
import math
import sqlite3

from engine import packs

from . import channels, screens


def _day(d, days):
    return round(d, 2) if d is not None and d <= days else None


def _diary_day(d):
    return math.floor(d) + 1     # day 0.4 of the run is "Day 1" on screen


def story(p, decisions, provider, trial_days, days, pack=None):
    """What the one-person drawer shows: the screens they saw and a short diary.

    A decision gets the person's own words (Glimmer's reason) only when they did what Glimmer
    thought most likely; otherwise the dice went the other way and the reason would not fit.
    """
    def quote(d):
        _, _, kind, screen, bucket, _, chosen = d
        if not hasattr(provider, "answer"):
            return None
        a = provider.answer(kind, p.persona, screen, bucket)
        return a["reason"] if chosen == max(a["probs"], key=a["probs"].get) else None

    pack = pack or packs.load("dating")
    st = pack["story"]
    nearest = st["nearest"]
    gate = pack["gates"][p.side]
    outcome = st["outcome"][gate]

    mine = [d for d in decisions if d[0] <= days]
    install = next(d for d in mine if d[2] == "install")
    skip = st["skip"].get(p.channel, st["skip_default"])
    diary = [[_diary_day(p.reached), f"{st['reach'][p.channel]} {'Installed it.' if p.installed is not None else skip}",
              quote(install)]]
    if p.matched is not None and p.matched <= days:
        diary.append([_diary_day(p.matched), st["success"][p.side], None])
    walls = [d for d in mine if d[2] == gate]
    if walls:
        first = walls[0]
        head = st.get("trial_head", "") if trial_days else ""
        diary.append([first[0] + 1, f"{head}{st['gate_head'][gate]} {nearest(first[4], p.side)} {outcome[first[6]]}",
                      quote(first)])
        last = walls[-1]
        if last is not first and last[6] != "come_back_tomorrow":
            diary.append([last[0] + 1, f"{nearest(last[4], p.side)} {outcome[last[6]]}", quote(last)])
    if p.quit is not None and p.quit <= days and not (walls and walls[-1][6] == "delete_app"):
        diary.append([_diary_day(p.quit), "Stopped opening the app.", None])
    diary.sort(key=lambda x: x[0])
    who = getattr(provider, "pool", {}).get(p.persona, {})
    return {"sex": p.side, "persona": who.get("text"), "ad": screens.install_screen(install[3], pack),
            "last": screens.gate_screen(gate, walls[-1][4], pack) if walls else None, "diary": diary}


def plan_card(cfg, plan):
    """The plan in plain words, for the input screen."""
    cities = plan.get("cities", [])
    if cities:
        names = [c["name"].split(",")[0] for c in cities]
        where = names[0] + "".join(f", then {n} on day {c['open_day']}" for n, c in zip(names[1:], cities[1:]))
    else:
        where = "Nationwide from day 1"
    pack = packs.of(cfg)
    words = pack.get("ad_words", {})      # the demo's own names for its channels (dating: TikTok, ambassadors)

    def ad(c):
        if c["kind"] in words:
            return words[c["kind"]][1 if cities else 0]
        return channels.LABELS[c["kind"]].lower() + (", nationwide" if c["where"] == "nationwide" else "")
    ads = " and ".join(ad(c) for c in sorted(plan["channels"], key=lambda c: c["kind"] != "event"))
    return {"title": "City by city" if cities else "Nationwide", "where": where, "ads": ads[0].upper() + ads[1:],
            "price": pack["price_words"](cfg, plan)}


def replay(cfg, results, verdict, provider):
    """results: {plan key: Result} from one representative run (docs/replay-format.md)."""
    days = cfg["days"]
    pack = packs.of(cfg)
    decisions_source = provider.name
    plans = {k: {"name": p["name"], "summary": p["summary"], "events": p["events"], "card": plan_card(cfg, p)}
             for k, p in cfg["plans"].items()}
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
                      "story": story(p, mine[p.id], provider, trial, days, pack)}
                     for p in res.people if p.reached <= days]
    return {
        "version": 1,
        "meta": {"app": cfg["app"], "market": cfg["market"], "days": days, "budget_usd": cfg["budget_usd"],
                 "pack": {"id": pack["id"], "header": pack["header"], **{k: v for k, v in pack["labels"].items()}},
                 "placeholder": decisions_source not in ("spark", "glimmer"), "people_per_dot": cfg["people_per_dot"],
                 "people_types": [t["name"] for t in getattr(provider, "types", [])]},
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
