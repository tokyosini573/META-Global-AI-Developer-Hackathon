"""Write web/public/replays/fixture_v2.json: the Kindred replay with made-up v2 fields.

    python3 scripts/fixture_v2.py

The screens for the v2 redesign (Setup, Main funnel, Report, Ads, drawer) are built against this file
before the engine writes v2 (docs/replay-format.md, "Version 2"). Every v2 number and sentence in it is
a placeholder. Delete this script and the fixture once engine.json is v2.
"""

import json
import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REASONS = {
    "installed": [("Not sure the people are real", "Sounds nice but I need proof they're real first."),
                  ("Already on other apps", "I have two dating apps I never open."),
                  ("Nobody near me", "Yeah right, nothing's nearby in my small town.")],
    "signed_up": [("Asked for a phone number", "It wants my number before I've seen one profile."),
                  ("Location always on", "Why does it need my location all the time?"),
                  ("Too many steps", "Six screens to sign up. I gave up.")],
    "first": [("Nobody nearby yet", "Nearest person is 41 miles away."),
              ("Five swipes is too few", "Five swipes a day and none fit me.")],
    "active": [("Chats went nowhere", "Matched twice, nobody answered."),
               ("Found someone", "Met someone. Deleted it, happily."),
               ("Too many notifications", "Five pings a day. Uninstalled.")],
    "paid": [("Price before a first date", "Ten bucks a week before I've even had a date? No."),
             ("Free is enough", "I can still message my matches for free.")],
}
KINDS = [("small_town_first_timer", "Small-town first-timer", 0.18), ("college_on_a_budget", "College student on a budget", 0.22),
         ("new_in_town", "New in town", 0.16), ("busy_professional", "Busy professional", 0.18),
         ("serious_about_dating", "Serious about dating", 0.12), ("burned_by_other_apps", "Burned by other apps", 0.14)]
FUNNEL = [("saw", "Saw an ad"), ("installed", "Installed"), ("signed_up", "Signed up"), ("first", "Got a match"),
          ("active", "Using on day 90"), ("paid", "Paid")]


def reached_step(p, key):
    return {"saw": p["reached"], "installed": p["installed"], "signed_up": p["signed_up"],
            "first": p["matched"], "paid": p["paid"],
            "active": p["signed_up"] if p["signed_up"] is not None and p["quit"] is None else None}[key] is not None


def main():
    rep = json.loads((ROOT / "web/public/replays/engine.json").read_text())
    brief = yaml.safe_load((ROOT / "plans/kindred.brief.yaml").read_text())
    r = random.Random(7)
    rep["version"] = 2
    m = rep["meta"]
    m["placeholder"] = True
    m["brief"] = brief
    m["note"] = "Simulated, calibrated to public benchmarks. Not observed."
    m["funnel"] = [{"key": k, "label": l} for k, l in FUNNEL]
    m["ads"] = [{**a, "screen": "ad"} for a in brief["ads"]]     # ad_2 and ad_3 screens are not rendered yet
    m["kinds"] = [{"id": i, "name": n, "share": s} for i, n, s in KINDS]
    for k, plan in rep["plans"].items():
        plan["changes"] = brief["setup"]["experiments"][k]["changes"]
        people = rep["people"][k]
        m["agents"] = max(m.get("agents", 0), len(people))
        cells = {i: {a["id"]: [0, 0] for a in brief["ads"]} for i, _, _ in KINDS}
        for p in people:
            p["kind"] = r.choices([i for i, _, _ in KINDS], [s for _, _, s in KINDS])[0]
            p["ad_id"] = r.choice(["ad_1", "ad_2", "ad_3"]) if p["story"]["ad"] == "ad" else None
            if p["ad_id"]:
                c = cells[p["kind"]][p["ad_id"]]
                c[0] += 1
                c[1] += p["installed"] is not None
            p["signed_up"] = None
            p["story"]["quit_reason"] = None
            if p["installed"] is None:
                continue
            if p["matched"] is not None or p["paid"] is not None or r.random() < 0.6:
                p["signed_up"] = round(p["installed"] + 0.05, 2)
                p["story"]["diary"].insert(1, [int(p["installed"]) + 1, "Signed up with Apple.", "One tap, fine."])
            else:
                p["quit"] = round(p["installed"] + 0.1, 2)
                p["matched"] = p["paid"] = None
                p["story"]["diary"].insert(1, [int(p["installed"]) + 1, "Left at sign-up.", REASONS["signed_up"][0][1]])
            if p["quit"] is not None and p["signed_up"] is not None:
                p["story"]["quit_reason"] = r.choice(REASONS["active"])[1]
        keys = [k for k, _ in FUNNEL]
        for p in people:
            missed = next((b for b in keys if not reached_step(p, b)), None)
            if missed and missed != "saw":
                p["story"]["stop"] = {"to": missed, "words": r.choice(REASONS[missed])[1]}
        report = []
        for (a, _), (b, _) in zip(FUNNEL, FUNNEL[1:]):
            gone = [p["id"] for p in people if reached_step(p, a) and not reached_step(p, b)]
            themes, rest = [], list(gone)
            for name, quote in REASONS[b]:
                n = len(rest) * 2 // 5
                if n:
                    themes.append({"name": name, "count": n, "quote": quote, "ids": rest[:n]})
                    rest = rest[n:]
            report.append({"from": a, "to": b, "left": len(gone), "themes": themes})
        plan["report"] = report
        plan["ads"] = {"line": "The trust ad won over the people who distrust dating apps.", "cells": cells}
        plan["range"] = {key: [0, 0] for key, _ in FUNNEL}
    out = ROOT / "web/public/replays/fixture_v2.json"
    out.write_text(json.dumps(rep, separators=(",", ":")))
    print(out, m["agents"], "people")


if __name__ == "__main__":
    main()
