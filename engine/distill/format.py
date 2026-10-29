"""Turn Spark's answers into chat examples for Glimmer and upload them to Modal.

    .venv/bin/python -m engine.distill.format          # writes data/distill/{train,val,test}.jsonl
    .venv/bin/python -m engine.distill.format --upload # and copies them plus the screens to the runs volume

Glimmer sees the same system prompt, persona and screen image as Spark. Spark's JSON schema
is enforced by the API; Glimmer gets it as one line of instructions instead. The target is the
final JSON only, sent straight to the user channel: the API returns no Spark reasoning, and the
simulation wants a short, fast answer.
"""

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path

from engine.world import screens
from engine.world.spark import SYSTEM

DATA = Path(__file__).resolve().parent.parent.parent / "data" / "distill"


def instruction(options):
    probs = ", ".join(f'"{o}": <0-1>' for o in options)
    return ('Answer with JSON only, in this shape: {"noticed": "<the one thing on the screen that matters most '
            f'to you>", "probabilities": {{{probs}}}, "reason": "<one short sentence in your own voice, under 15 '
            'words>"}. The probabilities must sum to 1.')


def target(answer, options):
    probs = {o: max(0.0, float(answer["probabilities"][o])) for o in options}
    total = sum(probs.values()) or 1.0
    probs = {o: round(v / total, 2) for o, v in probs.items()}
    return json.dumps({"noticed": answer["noticed"], "probabilities": probs, "reason": answer["reason"]},
                      ensure_ascii=False)


def chat(ex, answer=None):
    messages = [
        {"role": "system", "content": SYSTEM + "\n\n" + ex["persona"] + "\n\nReasoning strength: low."},
        {"role": "user", "content": [{"type": "image"},
                                     {"type": "text", "text": ex["question"] + "\n\n" + instruction(ex["options"])}]},
    ]
    if answer is not None:
        messages.append({"role": "assistant", "recipient": "user", "content": target(answer, ex["options"])})
    return messages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upload", action="store_true")
    args = ap.parse_args()
    rows = [json.loads(x) for x in (DATA / "examples.jsonl").read_text().splitlines()]
    by_id = defaultdict(dict)
    for r in rows:
        by_id[r["id"]][r["repeat"]] = r
    out = {"train": [], "val": [], "test": []}
    for xid, reps in sorted(by_id.items()):
        ex = reps.get(0) or reps[1]
        rec = {"id": xid, "image": ex["screen"] + ".png", "options": ex["options"], "kind": ex["kind"],
               "type": ex["type"], "bucket": ex["bucket"],
               "spark": [reps[k]["spark"]["probabilities"] for k in sorted(reps)]}
        if ex["split"] == "test":
            rec["messages"] = chat(ex)                       # prompt only; answers kept for scoring
        else:
            rec["messages"] = chat(ex, ex["spark"])
        out[ex["split"]].append(rec)
    for split, recs in out.items():
        (DATA / f"{split}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs))
        print(split, len(recs))
    if args.upload:
        # relative paths: the modal CLI rejects the absolute path of this folder (non-ASCII characters)
        root = DATA.parent.parent
        modal = ".venv/bin/modal"
        files = [(DATA / f"{split}.jsonl", f"/data/{split}.jsonl") for split in out]
        files += [(png, f"/data/screens/{png.name}") for png in sorted(screens.OUT.glob("*.png"))]
        for src, dst in files:
            subprocess.run([modal, "volume", "put", "--force", "glimmer-runs", str(src.relative_to(root)), dst],
                           check=True, cwd=root, capture_output=True)
        print("uploaded to glimmer-runs:/data")


if __name__ == "__main__":
    main()
