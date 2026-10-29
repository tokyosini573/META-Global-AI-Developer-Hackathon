"""Write a finished rehearsal: replay JSON for the screen, SQLite for analysis."""

import json
import sqlite3


def _day(d, days):
    return round(d, 2) if d is not None and d <= days else None


def replay(cfg, results, verdict, decisions_source):
    """results: {plan key: Result} from one representative run (docs/replay-format.md)."""
    days = cfg["days"]
    plans = {k: {"name": p["name"], "summary": p["summary"], "events": p["events"]} for k, p in cfg["plans"].items()}
    people = {}
    for k, res in results.items():
        people[k] = [{"id": p.id, "name": p.name, "age": p.age, "place": p.place,
                      "lon": round(p.lon, 3), "lat": round(p.lat, 3), "reached": _day(p.reached, days),
                      "installed": _day(p.installed, days), "matched": _day(p.matched, days),
                      "quit": _day(p.quit, days), "paid": _day(p.paid, days)}
                     for p in res.people if p.reached <= days]
    return {
        "version": 1,
        "meta": {"app": cfg["app"], "market": cfg["market"], "days": days, "budget_usd": cfg["budget_usd"],
                 "placeholder": decisions_source != "spark", "people_per_dot": cfg["people_per_dot"]},
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
                             name TEXT, age INT, reached REAL, installed REAL, matched REAL, quit REAL, paid REAL,
                             matches INT, PRIMARY KEY (plan, id));
        CREATE TABLE decisions (plan TEXT, day INT, person INT, kind TEXT, screen TEXT, bucket TEXT,
                                probs TEXT, chosen TEXT);
        CREATE TABLE matches (plan TEXT, a INT, b INT, day REAL);
        CREATE TABLE summary (key TEXT PRIMARY KEY, value TEXT);
    """)
    for k, res in results.items():
        db.executemany("INSERT INTO agents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       [(k, p.id, p.type, p.side, p.channel, p.place, p.lon, p.lat, p.name, p.age, p.reached,
                         p.installed, p.matched, p.quit, p.paid, len(p.match_days)) for p in res.people])
        db.executemany("INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?)",
                       [(k, d[0], d[1], d[2], d[3], json.dumps(d[4]), json.dumps(d[5]), d[6]) for d in res.decisions])
        db.executemany("INSERT INTO matches VALUES (?,?,?,?)", [(k, *m) for m in res.matches])
    db.executemany("INSERT INTO summary VALUES (?,?)", [(k, json.dumps(v)) for k, v in summary.items()])
    db.commit()
    db.close()
