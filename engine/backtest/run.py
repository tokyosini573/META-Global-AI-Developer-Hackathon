"""Backtest on the held-out cases: predict first, score second.

    .venv/bin/python -m engine.backtest.run predict v2   # writes backtest/predictions_v2.json (never reads answers)
    .venv/bin/python -m engine.backtest.run score        # compares with backtest/answers.yaml -> backtest/report.md

Each marker is a directional question ("is b ahead of a on active users at month 12?").
The world's probability is the share of Monte Carlo runs where it holds. Two baselines:
"always success" (every launch grows and makes money) and "Bass only" (diffusion grows,
the bigger reach wins, nothing about money). "No view" says 0.5 everywhere: any model with a
Brier score above its 0.250 is worse than not guessing.

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
PRED = {"v1": ROOT / "backtest" / "predictions.json", "v2": ROOT / "backtest" / "predictions_v2.json",
        "v2 generic": ROOT / "backtest" / "predictions_v2_generic.json"}
# seeds, sample rule values, decisions from generic descriptions (anonymization test)
METHODS = {"v1": (range(20), False, False), "v2": (range(40), True, False), "v2 generic": (range(40), True, True)}
NEW_FROM = 5   # case_5 onward were added after method v2 was fixed
ANSWERS = ROOT / "backtest" / "answers.yaml"
REPORT = ROOT / "backtest" / "report.md"
LIMITS = [
    "33 markers on 9 cases, 20 of them on the 5 cases held out for method v2: still a small sample; read the "
    "scores as a check of the method, not a measured accuracy.",
    "Spark named 8 of the 9 companies from their name-removed descriptions, including less-known ones. With "
    "generic descriptions it still named 4 (often the best-known app of the category). The anonymization test "
    "suggests memory moves the predictions little (mean change 0.07, 2 of 33 directions flipped), but the "
    "unrecognized subset is small.",
    "Method v2 (rule values drawn from the frozen ranges, market-size term) was chosen after the v1 scores of "
    "cases 1-4 were known; cases 1-4 under v2 are not evidence for it.",
    "The world under-predicts growth in the middle of a company's life: 6 of the 9 v2 misses are growth it did "
    "not see (case_3 m1-m2, case_4 m2, case_5 m3, case_7 m1-m2). It did well on the held-out cases partly "
    "because 9 of their 20 markers were declines, which it tends to expect.",
    "Markers are directional only, and several rest on company claims or proxies (downloads or sign-ups for "
    "active users, drivers for riders); answers.yaml marks the weak ones.",
    "The engine has no competitors and no price changes over time: case_6 lost its market when two large rivals "
    "returned, case_5 competed with them throughout, and case_8 dropped its fee after about 2.5 months.",
    "Two decline markers (case_1 m3, case_3 m3) were added before any v1 prediction, because every in-window "
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
    seeds, sampled, generic = METHODS[method]
    cases = load_cases()
    dec = BacktestDecisions(cases, generic)
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
    return {"always_success": always, "bass_only": bass, "no_view": 0.5}


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


def _anonymization(rows):
    """Do the predictions change when Spark is given only generic descriptions?"""
    pairs = [(cid, mid, ps["world v2"], ps["world v2 generic"]) for cid, mid, _, _, ps in rows
             if ps.get("world v2") is not None and ps.get("world v2 generic") is not None]
    if not pairs:
        return []
    flips = [(c, m, a, b) for c, m, a, b in pairs if (a > 0.5) != (b > 0.5)]
    lines = ["## Anonymization test", "",
             "The v2 run was repeated with every Spark decision made from a generic description built only from "
             "the case's structured fields (the two sides, country, one city or nationwide): no era, no product "
             "features, no city names, no history. If the predictions hold, they come from the mechanics and the "
             "inputs rather than from what Spark remembers about the company. This is a sensitivity check run "
             "after the answers were known; the answers play no part in it.", "",
             f"- Markers compared: {len(pairs)}",
             f"- Mean change in probability: {statistics.mean(abs(a - b) for _, _, a, b in pairs):.2f}",
             f"- Direction flipped: {len(flips)}"
             + (" (" + ", ".join(f"{c} {m} {a:.2f} -> {b:.2f}" for c, m, a, b in flips) + ")" if flips else ""), ""]
    rec_file = ROOT / "backtest" / "recognition_generic.json"
    if rec_file.exists():
        lines += ["Recognition with the generic descriptions:", "",
                  "| Case | Guess | Confidence | Recognized |", "|---|---|---|---|"]
        rec = json.loads(rec_file.read_text())
        for cid, g in rec.items():
            lines.append(f"| {cid} | {g.get('guess')} | {g.get('confidence')} | {'yes' if g.get('recognized') else 'no'} |")
        lines += ["", "Generic run, scored only on the cases Spark could not name from the generic description:", ""]
        lines += _summary(rows, ["world v2 generic", "always_success", "bass_only", "no_view"],
                          lambda c: c in rec and not rec[c].get("recognized"))
    return lines


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
    keys = [*(f"world {k}" for k in ["v2", "v2 generic", "v1"] if k in pred), "always_success", "bass_only", "no_view"]
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
    lines += _anonymization(rows)
    lines += ["## Limits", "", *[f"- {x}" for x in LIMITS]]
    REPORT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[lines.index("## All cases"):lines.index("## All cases") + 8]))
    print(f"wrote {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "predict"
    {"predict": predict, "score": score}[cmd](" ".join(sys.argv[2:]) or "v2") if cmd == "predict" else score()
