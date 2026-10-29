"""Score Glimmer against Spark on the held-out test people.

    .venv/bin/modal volume get --force glimmer-runs /r1/eval.json data/distill/r1_eval.json
    .venv/bin/python -m engine.distill.score r1        # -> data/distill/r1_report.md

Spark's first answer is the reference. Compared with it:
- Spark asked again (how much Spark disagrees with itself: the best a student can hope for),
- the demo's type table (one Spark answer per person type, what the engine uses today),
- Glimmer before and after training.
"""

import json
import statistics
import sys
from pathlib import Path

from engine.world.spark import TABLE, _key_str

DATA = Path(__file__).resolve().parent.parent.parent / "data" / "distill"


def norm(p, options):
    if not p:
        return None
    v = {o: max(0.0, float(p.get(o, 0))) for o in options}
    t = sum(v.values())
    return {o: x / t for o, x in v.items()} if t else None


def compare(ref, got, options):
    """(same top choice, mean absolute difference over options) or None if no valid answer."""
    if got is None:
        return None
    top = max(options, key=lambda o: ref[o]) == max(options, key=lambda o: got[o])
    return top, statistics.mean(abs(ref[o] - got[o]) for o in options)


def table_answer(rec, table):
    if rec["kind"] == "install":
        key = _key_str(("install", rec["type"], rec["bucket"], "-"))
    else:
        key = _key_str(("paywall", rec["type"], "paywall", tuple(rec["bucket"].split("|"))))
    return table[key]["probs"]


def main(run):
    test = [json.loads(x) for x in (DATA / "test.jsonl").read_text().splitlines()]
    ev = json.loads((DATA / f"{run}_eval.json").read_text())
    table = json.loads(TABLE.read_text())["entries"]
    got = {name: {o["id"]: o["probs"] for o in ev[name]} for name in ("base", "tuned")}
    rows = {"Spark asked again": [], "Type table (engine today)": [], "Glimmer before training": [],
            "Glimmer after training": []}
    kinds = {}
    for rec in test:
        opts = rec["options"]
        ref = norm(rec["spark"][0], opts)
        cands = {"Spark asked again": norm(rec["spark"][1], opts) if len(rec["spark"]) > 1 else "skip",
                 "Type table (engine today)": norm(table_answer(rec, table), opts),
                 "Glimmer before training": norm(got["base"].get(rec["id"]), opts),
                 "Glimmer after training": norm(got["tuned"].get(rec["id"]), opts)}
        for name, p in cands.items():
            if p == "skip":
                continue
            r = compare(ref, p, opts)
            rows[name].append(r)
            kinds.setdefault((name, rec["kind"]), []).append(r)

    def line(name, rs):
        ok = [r for r in rs if r is not None]
        if not rs:
            return f"| {name} | 0 | | | |"
        return (f"| {name} | {len(rs)} | {len(ok) / len(rs):.0%} | {sum(r[0] for r in ok) / max(1, len(ok)):.0%} | "
                f"{statistics.mean(r[1] for r in ok):.3f} |" if ok else f"| {name} | {len(rs)} | 0% | | |")

    head = ["| Compared with Spark's answer | People | Valid JSON | Same top choice | Mean abs. difference |",
            "|---|---|---|---|---|"]
    lines = [f"# Glimmer distillation: run {run}", "",
             f"Held-out test people: {len(test)} (never seen in training). Reference: Spark's first answer.", ""]
    lines += head + [line(n, rs) for n, rs in rows.items()] + [""]
    for kind in ("install", "paywall"):
        lines += [f"## {kind.capitalize()} decisions", ""] + head
        lines += [line(n, kinds.get((n, kind), [])) for n in rows] + [""]
    sp = ev.get("speed", {})
    if sp:
        lines += ["## Speed (one H100, 4-bit, batches of 16)", "", "| Model | Seconds per decision |", "|---|---|"]
        for name, s in sp.items():
            lines.append(f"| Glimmer {'after' if name == 'tuned' else 'before'} training | "
                         f"{s['seconds'] / max(1, len(ev[name])):.2f} |")
        lines.append("")
    out = DATA / f"{run}_report.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "r1")
