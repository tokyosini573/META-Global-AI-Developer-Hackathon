"""Write a finished rehearsal: replay JSON for the screen, SQLite for analysis."""

import json
import math
import sqlite3

from . import screens

REACH = {"tiktok": "Saw the ad on TikTok.", "ambassador": "A campus ambassador showed off Kindred.",
         "friend": "A friend sent a Kindred link."}
SKIP = {"tiktok": "Scrolled past.", "ambassador": "Did not install it.", "friend": "Did not install it."}
OUTCOME = {"pay": "Paid for unlimited swipes.", "come_back_tomorrow": "Came back the next day.",
           "delete_app": "Deleted the app."}


def _day(d, days):
    return round(d, 2) if d is not None and d <= days else None


def _diary_day(d):
    return math.floor(d) + 1     # day 0.4 of the run is "Day 1" on screen


def story(p, decisions, provider, trial_days, days):
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

    def nearest(bucket):
        return f"Nearest person: {screens.MILES[bucket[1]]} miles."

    mine = [d for d in decisions if d[0] <= days]
    install = next(d for d in mine if d[2] == "install")
    diary = [[_diary_day(p.reached), f"{REACH[p.channel]} {'Installed it.' if p.installed is not None else SKIP[p.channel]}",
              quote(install)]]
    if p.matched is not None and p.matched <= days:
        diary.append([_diary_day(p.matched), "Got a first match.", None])
    walls = [d for d in mine if d[2] == "paywall"]
    if walls:
        first = walls[0]
        head = "Free month ended. " if trial_days else ""
        diary.append([first[0] + 1, f"{head}Hit the paywall. {nearest(first[4])} {OUTCOME[first[6]]}", quote(first)])
        last = walls[-1]
        if last is not first and last[6] != "come_back_tomorrow":
            diary.append([last[0] + 1, f"{nearest(last[4])} {OUTCOME[last[6]]}", quote(last)])
    if p.quit is not None and p.quit <= days and not (walls and walls[-1][6] == "delete_app"):
        diary.append([_diary_day(p.quit), "Stopped opening the app.", None])
    diary.sort(key=lambda x: x[0])
    who = getattr(provider, "pool", {}).get(p.persona, {})
    return {"sex": p.side, "persona": who.get("text"), "ad": screens.install_screen(install[3]),
            "last": screens.paywall_screen(walls[-1][4]) if walls else None, "diary": diary}


def plan_card(cfg, plan):
    """The plan in plain words, for the input screen."""
    cities = plan.get("cities", [])
    if cities:
        names = [c["name"].split(",")[0] for c in cities]
        where = names[0] + "".join(f", then {n} on day {c['open_day']}" for n, c in zip(names[1:], cities[1:]))
    else:
        where = "Nationwide from day 1"
    ads = {"tiktok": "TikTok, nationwide" if not cities else "local TikTok", "ambassador": "Campus ambassadors"}
    ads = " and ".join(ads[c["kind"]] for c in sorted(plan["channels"], key=lambda c: c["kind"] != "ambassador"))
    price = f"${cfg['price_per_week']:.2f} a week"
    if plan["trial_days"]:
        price = f"Free for each person's first {plan['trial_days']} days, then {price}"
    else:
        price += f". Free users get {plan['free_swipes_per_day']} swipes a day."
    return {"title": "City by city" if cities else "Nationwide", "where": where, "ads": ads[0].upper() + ads[1:],
            "price": price}


def replay(cfg, results, verdict, provider):
    """results: {plan key: Result} from one representative run (docs/replay-format.md)."""
    days = cfg["days"]
    decisions_source = provider.name
    plans = {k: {"name": p["name"], "summary": p["summary"], "events": p["events"], "card": plan_card(cfg, p)}
             for k, p in cfg["plans"].items()}
    people = {}
    for k, res in results.items():
        mine = {}
        for d in res.decisions:
            mine.setdefault(d[1], []).append(d)
        trial = cfg["plans"][k]["trial_days"]
        people[k] = [{"id": p.id, "name": p.name, "age": p.age, "place": p.place,
                      "lon": round(p.lon, 3), "lat": round(p.lat, 3), "reached": _day(p.reached, days),
                      "installed": _day(p.installed, days), "matched": _day(p.matched, days),
                      "quit": _day(p.quit, days), "paid": _day(p.paid, days),
                      "story": story(p, mine[p.id], provider, trial, days)}
                     for p in res.people if p.reached <= days]
    return {
        "version": 1,
        "meta": {"app": cfg["app"], "market": cfg["market"], "days": days, "budget_usd": cfg["budget_usd"],
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
