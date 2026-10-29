"""Recognition check: can Spark name the real app from a name-removed case description?

    .venv/bin/python -m engine.backtest.recognize           # writes backtest/recognition.json
    .venv/bin/python -m engine.backtest.recognize generic   # same with the generic descriptions

If it can, a right prediction on that case may come from memory rather than the
mechanics, and the report says so.
"""

import json
import sys

import yaml

from engine.check_api import call, load_env

from .decide import generic_description
from .run import ANSWERS, ROOT, load_cases

OUT = ROOT / "backtest" / "recognition.json"
OUT_GENERIC = ROOT / "backtest" / "recognition_generic.json"
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["guess", "confidence"],
          "properties": {"guess": {"type": "string", "description": "The real company or app name, or 'unknown'."},
                         "confidence": {"type": "number", "minimum": 0, "maximum": 1}}}


def main(generic=False):
    out_file = OUT_GENERIC if generic else OUT
    env = load_env()
    names = {cid: a.get("_name", "") for cid, a in yaml.safe_load(ANSWERS.read_text()).items()}
    out = json.loads(out_file.read_text()) if out_file.exists() else {}   # keep earlier checks as recorded
    for cid, case in load_cases().items():
        if cid in out:
            continue
        sides = case["sides"]
        about = generic_description(case, next(iter(case["variants"]))) if generic else case["description"].strip()
        text = (f"{about}\nThe two sides are {sides['demand']['label']} and "
                f"{sides['supply']['label']}.\nWhich real company or app does this describe?")
        status, data, _ = call(env, "POST", "/chat/completions", {
            "model": "muse-spark-1.3-contributor", "reasoning_effort": "medium", "max_tokens": 4000,
            "messages": [{"role": "user", "content": text}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "guess", "strict": True,
                                                                       "schema": SCHEMA}}})
        guess = json.loads(data["choices"][0]["message"]["content"]) if status == 200 else {"error": status}
        real = names.get(cid, "")
        guess["recognized"] = bool(real) and real.split()[0].lower() in str(guess.get("guess", "")).lower()
        out[cid] = guess
        print(cid, guess)
    out_file.write_text(json.dumps(out, indent=1))
    print(f"wrote {out_file.relative_to(ROOT)}")


if __name__ == "__main__":
    main(generic="generic" in sys.argv[1:])
