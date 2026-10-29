"""Rehearse both launch plans: calibrate, run Monte Carlo, write the replay.

    .venv/bin/python -m engine.run                       # plans/kindred.yaml, 30 runs
    .venv/bin/python -m engine.run --runs 5 --days 30    # quick check

Writes web/public/replays/<name>.json (open the site with ?replay=<name>) and
runs/<name>.sqlite. Decisions come from the committed Glimmer table, one answer per person in the
pool (engine/world/glimmer.py); --provider spark uses the per-type Spark table, stub the stand-in.
"""

import argparse
import json
import statistics
import time
from pathlib import Path

import yaml

from engine.world.calibrate import fit_shifts
from engine.world.decide import DecisionCache, StubProvider
from engine.world.glimmer import GlimmerProvider
from engine.world.output import replay, write_sqlite
from engine.world.sim import Simulation, measures, totals
from engine.world.spark import SparkProvider

ROOT = Path(__file__).resolve().parent.parent
CALIBRATION_SEEDS = tuple(range(1000, 1006))


def calibrate(cfg, cache, days):
    cal = cfg["calibration"]

    def measure(shifts):
        seen = [measures(Simulation(cfg, cal["reference_plan"], cache, shifts, s, days).run(), days)
                for s in CALIBRATION_SEEDS]
        return {k: statistics.mean(m[k] for m in seen if m[k] is not None) for k in cal["targets"]}

    return fit_shifts(measure, cal["targets"])


def verdict(cfg, runs):
    plans = cfg["plans"]
    paying = {k: [r[k]["paying"] for r in runs] for k in plans}
    b_wins = sum(r["b"]["paying"] > r["a"]["paying"] for r in runs)
    winner = "b" if b_wins * 2 > len(runs) else "a"
    wins = b_wins if winner == "b" else len(runs) - b_wins
    med = {k: statistics.median(v) for k, v in paying.items()}
    return {
        "winner": winner,
        "headline": f"{plans[winner]['name']} wins.",
        "reason": f"{plans[winner]['name']} ends with more paying users in {wins} of {len(runs)} runs "
                  f"(median {med['b']:,.0f} vs {med['a']:,.0f}).",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plans", default="plans/kindred.yaml")
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--days", type=int)
    ap.add_argument("--name", default="engine")
    ap.add_argument("--provider", choices=["glimmer", "spark", "stub"], default="glimmer",
                    help="glimmer reads data/decisions/kindred_glimmer.json; spark reads kindred_spark.json "
                         "and asks Spark only for missing keys")
    args = ap.parse_args()

    cfg = yaml.safe_load((ROOT / args.plans).read_text())
    if args.days:
        cfg["days"] = args.days
    days = cfg["days"]
    cache = DecisionCache({"glimmer": GlimmerProvider, "spark": SparkProvider, "stub": StubProvider}[args.provider]())
    t0 = time.time()

    shifts, seen = calibrate(cfg, cache, days)
    print("calibration shifts:", {k: round(v, 2) for k, v in shifts.items()})
    print("reference plan vs targets:",
          {k: f"{seen[k]:.3f} / {v}" for k, v in cfg["calibration"]["targets"].items()})

    runs, first = [], None
    for seed in range(args.runs):
        res = {k: Simulation(cfg, k, cache, shifts, seed, days).run() for k in cfg["plans"]}
        runs.append({k: totals(r, days, cfg["people_per_dot"]) for k, r in res.items()})
        first = first or res
    v = verdict(cfg, runs)

    out = ROOT / "web" / "public" / "replays" / f"{args.name}.json"
    out.write_text(json.dumps(replay(cfg, first, v, cache.provider.name), separators=(",", ":")))
    db = ROOT / "runs" / f"{args.name}.sqlite"
    db.parent.mkdir(exist_ok=True)
    summary = {"verdict": v, "shifts": shifts, "calibration_seen": seen, "runs": runs,
               "cache": {"calls": cache.calls, "hits": cache.hits}, "provider": cache.provider.name}
    write_sqlite(db, first, summary)

    for k in cfg["plans"]:
        med = {m: statistics.median(r[k][m] for r in runs if r[k][m] is not None) for m in runs[0][k]}
        print(k, {m: (round(x, 3) if m == "quit_week1" else round(x)) for m, x in med.items()})
    print("verdict:", v["headline"], v["reason"])
    print(f"cache: {cache.calls} provider calls, {cache.hits} reused · {time.time() - t0:.1f}s")
    print(f"wrote {out.relative_to(ROOT)} and {db.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
