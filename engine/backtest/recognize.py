"""Recognition check: can Spark name the real app from a name-removed case description?

    .venv/bin/python -m engine.backtest.recognize   # writes backtest/recognition.json

If it can, a right prediction on that case may come from memory rather than the
mechanics, and the report says so.
"""

import json

import yaml

from engine.check_api import call, load_env

from .run import ANSWERS, ROOT, load_cases

OUT = ROOT / "backtest" / "recognition.json"
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["guess", "confidence"],
          "properties": {"guess": {"type": "string", "description": "The real company or app name, or 'unknown'."},
                         "confidence": {"type": "number", "minimum": 0, "maximum": 1}}}


def main():
    env = load_env()
    names = {cid: a.get("_name", "") for cid, a in yaml.safe_load(ANSWERS.read_text()).items()}
    out = {}
    for cid, case in load_cases().items():
        sides = case["sides"]
        text = (f"{case['description'].strip()}\nThe two sides are {sides['demand']['label']} and "
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
    OUT.write_text(json.dumps(out, indent=1))
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
