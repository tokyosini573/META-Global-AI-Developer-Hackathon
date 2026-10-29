"""Backtest on the held-out cases: predict first, score second.

    .venv/bin/python -m engine.backtest.run predict v2   # writes backtest/predictions_v2.json (never reads answers)
    .venv/bin/python -m engine.backtest.run score        # compares with backtest/answers.yaml -> backtest/report.md

Each marker is a directional question ("is b ahead of a on active users at month 12?").
The world's probability is the share of Monte Carlo runs where it holds. Two baselines:
"always success" (every launch grows and makes money) and "Bass only" (diffusion grows,
the bigger reach wins, nothing about money).

Method v1 used the rule points in world.RULES with 20 seeds (cases 1-4, kept as recorded).
Method v2 draws the rule values and a reach factor per run from the frozen ranges, with 40
seeds (backtest/protocol_v2.md). v2 was chosen after seeing the v1 scores, so only cases added
after that choice (NEW_FROM onward) count as held out for it.
"""

import json
import statistics
import sys
from pathlib import Path

import yaml

from .decide import BacktestDecisions
from .world import World, decision_keys, sample_params

ROOT = Path(__file__).resolve().parent.parent.parent
CASES = ROOT / "backtest" / "cases"
PRED = {"v1": ROOT / "backtest" / "predictions.json", "v2": ROOT / "backtest" / "predictions_v2.json"}
METHODS = {"v1": (range(20), False), "v2": (range(40), True)}   # seeds, sample rule values
NEW_FROM = 5   # case_5 onward were added after method v2 was fixed
ANSWERS = ROOT / "backtest" / "answers.yaml"
REPORT = ROOT / "backtest" / "report.md"
LIMITS = [
    "13 markers on 4 cases: far too few to claim accuracy; read this as a smoke test of the method.",
    "Spark recognized every case from its description, so its decisions may lean on what it remembers.",
    "Markers are directional only, and several rest on company claims or proxies (downloads for active users).",
    "Two decline markers (case_1 m3, case_3 m3) were added before any prediction, because every in-window "
    "marker was a growth marker and an always-success baseline would have scored perfectly.",
    "case_4 m3 is fixed by the inputs (one variant charges a fee, the other is free), so it barely tests the world.",
    "case_2's variant a (the old app kept as is) never happened; the comparison is a counterfactual.",
    "Backtest worlds are not calibrated to benchmarks; markers compare a world with itself, not absolute levels.",
]


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


def predict(method="v2"):
    seeds, sampled = METHODS[method]
    cases = load_cases()
    dec = BacktestDecisions(cases)
    asked = dec.prefill([k for c in cases.values() for k in decision_keys(c)])
    print(f"decision table: {len(dec.entries)} keys ({asked} new)")
    out = {}
    for cid, case in cases.items():
        hits = {m["id"]: [] for m in case["markers"]}
        values = {m["id"]: [] for m in case["markers"]}
        for seed in seeds:
            params = sample_params(seed) if sampled else None
            worlds = {vk: World(case, vk, dec, seed, params).run() for vk in case["variants"]}
            for m in case["markers"]:
                left = worlds[m["compare"]["variant"]].metric(m["metric"], m["at_month"])
                right = _side_value(worlds, m["compare"]["than"], m["metric"], m["at_month"])
                hits[m["id"]].append(left > right)
                values[m["id"]].append([left, right])
        out[cid] = {m["id"]: {"question": m["question"], "p": sum(hits[m["id"]]) / len(seeds),
                              "median_left": statistics.median(v[0] for v in values[m["id"]]),
                              "median_right": statistics.median(v[1] for v in values[m["id"]])}
                    for m in case["markers"]}
        for mid, r in out[cid].items():
            print(f"{cid} {mid} p={r['p']:.2f}  {r['question']}")
    PRED[method].write_text(json.dumps(out, indent=1))
    print(f"wrote {PRED[method].relative_to(ROOT)}")


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


def _case_no(cid):
    return int(cid.split("_")[1])


def _summary(rows, keys, keep):
    lines = ["| Model | Direction right | Brier score (lower is better) |", "|---|---|---|"]
    for k in keys:
        got = [(ps[k], y) for cid, _, _, y, ps in rows if keep(cid) and ps.get(k) is not None]
        if not got:
            continue
        right = sum((p > 0.5) == (y == 1.0) for p, y in got if p != 0.5)
        brier = statistics.mean((p - y) ** 2 for p, y in got)
        lines.append(f"| {k} | {right} of {len(got)} | {brier:.3f} |")
    return lines + [""]


def score():
    cases = load_cases()
    pred = {k: json.loads(f.read_text()) for k, f in PRED.items() if f.exists()}
    answers = yaml.safe_load(ANSWERS.read_text())
    rec_file = ROOT / "backtest" / "recognition.json"
    rec = json.loads(rec_file.read_text()) if rec_file.exists() else {}
    rows = []
    for cid, case in cases.items():
        for m in case["markers"]:
            y = 1.0 if answers[cid][m["id"]]["answer"] else 0.0
            ps = {f"world {k}": pred[k][cid][m["id"]]["p"] if cid in pred[k] else None for k in pred}
            ps.update(baselines(case, m))
            rows.append((cid, m["id"], m["question"], y, ps))
    keys = [*(f"world {k}" for k in reversed(list(pred))), "always_success", "bass_only"]
    lines = ["# Backtest report", "",
             "Predictions were committed before the answers were added: `predictions.json` (method v1, "
             "cases 1-4) and `predictions_v2.json` (method v2, all cases). Method v2 draws the rule values "
             "and a reach factor per run from the frozen ranges; it was chosen after the v1 scores were "
             "known, so only cases 5 onward are held out for it (`protocol_v2.md`).", "",
             "| Case | Marker | Question | Real | " + " | ".join(keys) + " |",
             "|---|---|---|---|" + "---|" * len(keys)]
    for cid, mid, q, y, ps in rows:
        cells = " | ".join("" if ps.get(k) is None else f"{ps[k]:.2f}" for k in keys)
        lines.append(f"| {cid} | {mid} | {q} | {'yes' if y else 'no'} | {cells} |")
    lines += ["", f"## Held out for method v2: cases {NEW_FROM} onward", ""]
    lines += _summary(rows, keys, lambda c: _case_no(c) >= NEW_FROM)
    if rec:
        lines += ["## Cases Spark did not recognize", ""]
        lines += _summary(rows, keys, lambda c: c in rec and not rec[c].get("recognized"))
    lines += [f"## Cases 1-{NEW_FROM - 1} (method v1 was scored on these first)", ""]
    lines += _summary(rows, keys, lambda c: _case_no(c) < NEW_FROM)
    lines += ["## All cases", ""]
    lines += _summary(rows, keys, lambda c: True)
    lines += ["Direction counts a probability of exactly 0.5 as wrong: the baselines have no view on "
              "variant-vs-variant markers.", ""]
    if rec:
        lines += ["## Recognition check", "",
                  "Spark was shown each name-removed description and asked which real company it describes.", "",
                  "| Case | Guess | Confidence | Recognized |", "|---|---|---|---|"]
        for cid, g in rec.items():
            lines.append(f"| {cid} | {g.get('guess')} | {g.get('confidence')} | {'yes' if g.get('recognized') else 'no'} |")
        lines.append("")
    lines += ["## Limits", "", *[f"- {x}" for x in LIMITS]]
    REPORT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[lines.index("## All cases"):lines.index("## All cases") + 8]))
    print(f"wrote {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "predict"
    {"predict": predict, "score": score}[cmd](*sys.argv[2:])
