"""Rehearse both launch plans: calibrate, run Monte Carlo, write the replay.

    .venv/bin/python -m engine.run                       # plans/kindred.yaml, 30 runs
    .venv/bin/python -m engine.run --runs 5 --days 30    # quick check

Writes web/public/replays/<name>.json (open the site with ?replay=<name>) and
runs/<name>.sqlite. Decisions come from the committed Glimmer table, one answer per person in the
pool (engine/world/glimmer.py); --provider spark uses the per-type Spark table, stub the stand-in.

plans/<app>.brief.yaml (same stem as the plan file), when it exists, is the app's brief
(docs/brief-format.md): it turns on the v2 funnel (ads, sign-up, why people stop) and sets how many
simulated people each experiment reaches. Live runs pass cfg["brief"] themselves.
"""

import argparse
import json
import statistics
import time
from pathlib import Path

import yaml

from engine.world.calibrate import fit_shifts
from engine.world.decide import TYPES, DecisionCache, StubProvider
from engine.world.glimmer import GlimmerProvider
from engine.world.output import replay, write_sqlite
from engine.world.sim import Simulation, ad_cells, funnel, measures, totals
from engine.world.spark import SparkProvider
from engine import packs
from engine.world import channels, report, wonder

ROOT = Path(__file__).resolve().parent.parent
CALIBRATION_SEEDS = tuple(range(1000, 1006))
CALIBRATION_MIN_DAYS = 60   # the 30-day conversion target needs people who installed at least 30 days before the end


def load_plan(path):
    """A plan file, with its brief (plans/<stem>.brief.yaml) in cfg["brief"] when there is one."""
    path = Path(path)
    cfg = yaml.safe_load(path.read_text())
    brief = path.with_name(path.stem + ".brief.yaml")
    if brief.exists():
        cfg["brief"] = yaml.safe_load(brief.read_text())
    return cfg


def apply_people(cfg):
    """brief.setup.people simulated people reach the experiment that reaches the most (paid channels);
    the other reaches fewer, at the same number of real people per simulated person (H4)."""
    n = ((cfg.get("brief") or {}).get("setup") or {}).get("people")
    if not n:
        return
    real = max(channels.expected_reach(cfg, p, cfg["days"]) for p in cfg["plans"].values())
    if real > 0:
        cfg["people_per_dot"] = round(real / n, 3)


def calibrate(cfg, cache, days):
    cal = cfg["calibration"]
    pack = packs.of(cfg)
    days = max(days, CALIBRATION_MIN_DAYS)     # H5: the level does not depend on how long the run is
    targets = {k: v for k, v in cal["targets"].items() if k != "signup" or cfg.get("brief")}

    seeds = range(CALIBRATION_SEEDS[0], CALIBRATION_SEEDS[0] + cal.get("seeds", len(CALIBRATION_SEEDS)))
    # "both": the benchmark holds for the two launches together, so neither plan's choice sets the level
    ref = list(cfg["plans"]) if cal["reference_plan"] == "both" else [cal["reference_plan"]]

    def measure(shifts):
        seen = [measures(Simulation(cfg, k, cache, shifts, s, days).run(), days, pack)
                for s in seeds for k in ref]
        return {k: statistics.mean(m[k] for m in seen if m[k] is not None) for k in targets}

    return fit_shifts(measure, targets, iters=20)


def verdict(cfg, runs):
    plans = cfg["plans"]
    pack = packs.of(cfg)
    goal = pack["goal_key"]
    paying = {k: [r[k][goal] for r in runs] for k in plans}
    b_wins = sum(r["b"][goal] > r["a"][goal] for r in runs)
    winner = "b" if b_wins * 2 > len(runs) else "a"
    wins = b_wins if winner == "b" else len(runs) - b_wins
    med = {k: statistics.median(v) for k, v in paying.items()}
    return {
        "winner": winner,
        "headline": f"{plans[winner]['name']} wins.",
        "reason": f"{plans[winner]['name']} ends with more {pack['labels']['goal']} in {wins} of {len(runs)} runs "
                  f"(median {med['b']:,.0f} vs {med['a']:,.0f}).",
    }


def wonder_reason(cfg, runs, rep):
    """Wonder writes why the winner won, from the medians and what people in the replay said."""
    plans = cfg["plans"]
    said = {}
    for k, ppl in rep["people"].items():
        dating = packs.of(cfg)["id"] == "dating"
        done = "paid" if dating else "completed a " + packs.of(cfg)["labels"]["goal"].split()[-1].rstrip("s")
        words = {"deleted the app": [], done: [], "did not install": []}
        for p in ppl:
            for _, what, quote in p["story"]["diary"]:
                if not quote:
                    continue
                if "Deleted" in what:
                    words["deleted the app"].append(quote)
                elif ("Paid" in what) if dating else (p["paid"] is not None):
                    words[done].append(quote)
                elif p["installed"] is None:
                    words["did not install"].append(quote)
        said[plans[k]["name"]] = {w: q[:12] for w, q in words.items()}
    medians = {plans[k]["name"]: {m: round(statistics.median(r[k][m] for r in runs if r[k][m] is not None), 3)
                                  for m in runs[0][k]} for k in plans}
    winner = plans[rep["verdict"]["winner"]]["name"]
    facts = {"winner": winner, "medians": medians, "what_people_said": said}
    reason = wonder.verdict_reason(cfg, facts)
    if any(c.isdigit() for c in reason):
        raise SystemExit(f"Wonder used a number in the verdict: {reason!r}")
    return reason


def rehearse(cfg, cache, n_runs=30, use_wonder=True, log=print):
    """Calibrate, run both plans n_runs times, and build the replay. Returns (replay, summary)."""
    days = cfg["days"]
    pack = packs.of(cfg)
    apply_people(cfg)
    shifts, seen = calibrate(cfg, cache, days)
    log("calibration shifts:", {k: round(v, 2) for k, v in shifts.items()})
    log("reference plan vs targets:", {k: f"{seen[k]:.3f} / {v}" for k, v in cfg["calibration"]["targets"].items()
                                        if k in seen})

    runs, first, funnels, cells = [], None, [], []
    kinds = [t["id"] for t in getattr(cache.provider, "types", TYPES)]
    for seed in range(n_runs):
        res = {k: Simulation(cfg, k, cache, shifts, seed, days).run() for k in cfg["plans"]}
        runs.append({k: totals(r, days, cfg["people_per_dot"], pack) for k, r in res.items()})
        funnels.append({k: funnel(r, days, pack) for k, r in res.items()})
        cells.append({k: ad_cells(r, days, kinds, packs.experiment_ads(cfg.get("brief"), k)) for k, r in res.items()})
        first = first or res
    v = verdict(cfg, runs)
    # The replay shows the first run the winner won, so its numbers never contradict the verdict.
    goal, w = pack["goal_key"], v["winner"]
    shown = next((i for i, r in enumerate(runs) if r[w][goal] > r["b" if w == "a" else "a"][goal]), 0)
    if shown:
        first = {k: Simulation(cfg, k, cache, shifts, shown, days).run() for k in cfg["plans"]}
    rep = replay(cfg, first, v, cache.provider, funnels, cells)
    if use_wonder:
        w = v["winner"]
        goal = pack["goal_key"]
        wins = sum(r[w][goal] > r["b" if w == "a" else "a"][goal] for r in runs)
        v["reason"] = f"{wonder_reason(cfg, runs, rep)} {cfg['plans'][w]['name']} won {wins} of {len(runs)} runs."
        rep["verdict"] = v
    rep["meta"]["runs"] = n_runs
    report.build(rep, cfg, use_wonder=use_wonder, log=log)   # v2: plans[k].report, plans[k].ads.line
    summary = {"verdict": v, "shifts": shifts, "calibration_seen": seen, "runs": runs, "funnels": funnels, "shown": shown,
               "cache": {"calls": cache.calls, "hits": cache.hits}, "provider": cache.provider.name}
    return rep, summary, first


def provider_for(cfg, name="glimmer"):
    """Who answers the decisions of a demo plan file."""
    from engine.world import typed
    if packs.of(cfg)["id"] != "dating":       # Glimmer's pool is the dating demo's; other markets use kinds of people
        return _fresh_only(typed.TypedProvider(cfg, *typed.paths(cfg)))
    if name == "stub":
        return StubProvider()
    if name == "spark":
        if cfg.pop("brief", None):            # the placeholder types have no v2 answers
            print("--provider spark: the brief is left out (the placeholder types only answer v1 questions)")
        return SparkProvider()
    # Glimmer answers what it was trained on; Spark per Wonder kind answers the v2 questions
    others = typed.TypedProvider(cfg, wonder.PEOPLE, typed.paths(cfg)[1]) if cfg.get("brief") else None
    if others:
        from engine.world.glimmer import trained_on
        _fresh_only(others, [k for k in others.keys() if not trained_on(k[0], k[3])])
    return GlimmerProvider(others=others)


def _fresh_only(p, keys=None):
    """Refuse a table whose answers were asked with other words than today's questions."""
    stale = [k for k in (keys if keys is not None else p.keys()) if not p._fresh(k)]
    if stale:
        raise SystemExit(f"{len(stale)} decisions in {p.path.name} were asked with other words (e.g. {stale[0]}); "
                         f"run `python -m engine.world.typed <plan file>` first")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plans", default="plans/kindred.yaml")
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--days", type=int)
    ap.add_argument("--name", default="engine")
    ap.add_argument("--no-wonder", action="store_true", help="keep the plain win-count verdict (no Wonder call)")
    ap.add_argument("--provider", choices=["glimmer", "spark", "stub"], default="glimmer",
                    help="dating only: glimmer reads data/decisions/kindred_glimmer.json; spark reads kindred_spark.json "
                         "and asks Spark only for missing keys. Other markets use their kinds-of-people table")
    args = ap.parse_args()

    cfg = load_plan(ROOT / args.plans)
    if args.days:
        cfg["days"] = args.days
    cache = DecisionCache(provider_for(cfg, args.provider))
    t0 = time.time()
    use_wonder = not args.no_wonder and (args.provider == "glimmer" or packs.of(cfg)["id"] != "dating")
    rep, summary, first = rehearse(cfg, cache, args.runs, use_wonder)

    out = ROOT / "web" / "public" / "replays" / f"{args.name}.json"
    out.write_text(json.dumps(rep, separators=(",", ":")))
    db = ROOT / "runs" / f"{args.name}.sqlite"
    db.parent.mkdir(exist_ok=True)
    write_sqlite(db, first, summary)

    runs, v = summary["runs"], summary["verdict"]
    for k in cfg["plans"]:
        med = {m: statistics.median(r[k][m] for r in runs if r[k][m] is not None) for m in runs[0][k]}
        print(k, {m: (round(x, 3) if m == "quit_week1" else round(x)) for m, x in med.items()})
    print("verdict:", v["headline"], v["reason"])
    print(f"cache: {cache.calls} provider calls, {cache.hits} reused · {time.time() - t0:.1f}s")
    print(f"wrote {out.relative_to(ROOT)} and {db.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
