"""Backtest on the held-out cases: predict first, score second.

    .venv/bin/python -m engine.backtest.run predict   # writes backtest/predictions.json (never reads answers)
    .venv/bin/python -m engine.backtest.run score     # compares with backtest/answers.yaml -> backtest/report.md

Each marker is a directional question ("is b ahead of a on active users at month 12?").
The world's probability is the share of Monte Carlo runs where it holds. Two baselines:
"always success" (every launch grows and makes money) and "Bass only" (diffusion grows,
the bigger reach wins, nothing about money).
"""

import json
import statistics
import sys
from pathlib import Path

import yaml

from .decide import BacktestDecisions
from .world import World, decision_keys

ROOT = Path(__file__).resolve().parent.parent.parent
CASES = ROOT / "backtest" / "cases"
PRED = ROOT / "backtest" / "predictions.json"
ANSWERS = ROOT / "backtest" / "answers.yaml"
REPORT = ROOT / "backtest" / "report.md"
SEEDS = range(20)


def load_cases():
    cases = {}
    for f in sorted(CASES.glob("*.yaml")):
        c = yaml.safe_load(f.read_text())
        cases[c["id"]] = c
    return cases


def _side_value(worlds, spec, metric, month):
    w = worlds[spec["variant"]]
    if "value" in spec:
        return spec["value"]
    return w.metric(metric, spec.get("at_month", month))


def predict():
    cases = load_cases()
    dec = BacktestDecisions(cases)
    asked = dec.prefill([k for c in cases.values() for k in decision_keys(c)])
    print(f"decision table: {len(dec.entries)} keys ({asked} new)")
    out = {}
    for cid, case in cases.items():
        hits = {m["id"]: [] for m in case["markers"]}
        values = {m["id"]: [] for m in case["markers"]}
        for seed in SEEDS:
            worlds = {vk: World(case, vk, dec, seed).run() for vk in case["variants"]}
            for m in case["markers"]:
                left = worlds[m["compare"]["variant"]].metric(m["metric"], m["at_month"])
                right = _side_value(worlds, m["compare"]["than"], m["metric"], m["at_month"])
                hits[m["id"]].append(left > right)
                values[m["id"]].append([left, right])
        out[cid] = {m["id"]: {"question": m["question"], "p": sum(hits[m["id"]]) / len(SEEDS),
                              "median_left": statistics.median(v[0] for v in values[m["id"]]),
                              "median_right": statistics.median(v[1] for v in values[m["id"]])}
                    for m in case["markers"]}
        for mid, r in out[cid].items():
            print(f"{cid} {mid} p={r['p']:.2f}  {r['question']}")
    PRED.write_text(json.dumps(out, indent=1))
    print(f"wrote {PRED.relative_to(ROOT)}")


def baselines(case, marker):
    than = marker["compare"]["than"]
    if "value" in than or than.get("variant") == marker["compare"]["variant"]:
        always = 1.0                      # grows over time, makes money
        bass = 1.0 if "value" not in than else 0.5
    else:
        always = 0.5                      # says nothing about which variant
        ra = case["variants"][marker["compare"]["variant"]]["reach_per_month"]
        rb = case["variants"][than["variant"]]["reach_per_month"]
        bass = 1.0 if ra > rb else 0.0 if ra < rb else 0.5
    return {"always_success": always, "bass_only": bass}


def score():
    cases = load_cases()
    pred = json.loads(PRED.read_text())
    answers = yaml.safe_load(ANSWERS.read_text())
    rows, scores = [], {"world": [], "always_success": [], "bass_only": []}
    for cid, case in cases.items():
        for m in case["markers"]:
            y = 1.0 if answers[cid][m["id"]]["answer"] else 0.0
            ps = {"world": pred[cid][m["id"]]["p"], **baselines(case, m)}
            for k, p in ps.items():
                scores[k].append(((p - y) ** 2, (p > 0.5) == (y == 1.0) if p != 0.5 else False))
            rows.append((cid, m["id"], m["question"], y, ps))
    lines = ["# Backtest report", "",
             "Predictions were written to `predictions.json` before `answers.yaml` was read.", "",
             "| Case | Marker | Question | Real | World | Always success | Bass only |",
             "|---|---|---|---|---|---|---|"]
    for cid, mid, q, y, ps in rows:
        lines.append(f"| {cid} | {mid} | {q} | {'yes' if y else 'no'} | {ps['world']:.2f} | "
                     f"{ps['always_success']:.2f} | {ps['bass_only']:.2f} |")
    lines += ["", "| Model | Direction right | Brier score (lower is better) |", "|---|---|---|"]
    for k, v in scores.items():
        lines.append(f"| {k} | {sum(x[1] for x in v)} of {len(v)} | {statistics.mean(x[0] for x in v):.3f} |")
    REPORT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-4:]))
    print(f"wrote {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    {"predict": predict, "score": score}[sys.argv[1] if len(sys.argv) > 1 else "predict"]()
