"""First spike: does Spark make structured decisions from an app screen image + a persona?

    python3 engine/spike/spark_decide.py            # full run (about 48 calls, a few cents)
    python3 engine/spike/spark_decide.py --quick    # one call per model and setting

What it checks
1. Do json_schema-constrained answers always come back well-formed (probabilities sum to ~1)?
2. Does the screen change the decision: 41 miles + paywall (Plan A) vs 2 miles + a match + free (Plan B)?
3. How much do repeated answers vary?
4. Cost and latency per call; how much lowering reasoning_effort saves and whether decisions change.
Results are written as JSON to engine/spike/results/. The key is never stored or printed.
"""
import base64
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from check_api import call, load_env  # noqa: E402

# USD per 1M tokens (input, output). Reasoning tokens are assumed to bill as output.
PRICE = {"muse-spark-1.3": (1.25, 4.25), "muse-spark-1.3-contributor": (0.10, 0.20)}

MAYA = (
    "You are Maya, 24, a dental assistant in Columbus, Ohio. You moved there a year ago and know few people. "
    "Money is tight: you pay for Spotify and nothing else. You get bored of apps fast. "
    "You saw a TikTok ad for Kindred, a new dating app, and installed it 3 days ago."
)
# What happened so far (the real engine takes this from simulated memory). Must agree with the screen.
HISTORY_A = " You have swiped through every profile it showed you. Everyone is far away and you have no matches."
HISTORY_B = " The first two days were quiet. Today you got your first match."

# (name, screen, persona, actions possible on that screen, question)
CASES = [
    ("ad", "ad.png", MAYA.split(" You saw")[0], ["install", "scroll_past"],
     "You are scrolling TikTok at 11pm and this ad appears. What do you do?"),
    ("plan_a_paywall", "paywall.png", MAYA + HISTORY_A, ["pay", "come_back_tomorrow", "delete_app"],
     "This is what Kindred shows you right now. What do you do?"),
    ("plan_b_nearby", "nearby.png", MAYA + HISTORY_B, ["pay", "come_back_tomorrow", "delete_app"],
     "This is what Kindred shows you right now. What do you do?"),
]
SYSTEM = (
    "You simulate one specific real person looking at their phone. Stay in character. "
    "Real people are impatient, careful with money and quit apps easily; do not be more patient or rational than they would be. "
    "Base your answer on what is actually visible on the screen. "
    "Profile photos are hidden in this simulation as gray placeholders; do not judge people by them."
)


def schema(actions):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["noticed", "probabilities", "reason"],
        "properties": {
            "noticed": {"type": "string", "description": "The one thing on the screen that matters most to you, quoted or described in a few words."},
            "probabilities": {
                "type": "object",
                "additionalProperties": False,
                "required": actions,
                "properties": {a: {"type": "number", "minimum": 0, "maximum": 1} for a in actions},
                "description": "How likely you are to do each action. Must sum to 1.",
            },
            "reason": {"type": "string", "description": "One short sentence in your own voice, under 15 words."},
        },
    }


def image_url(name):
    return "data:image/png;base64," + base64.b64encode((HERE / "screens" / name).read_bytes()).decode()


def run_one(env, model, effort, case):
    name, screen, persona, actions, question = case
    body = {
        "model": model,
        "max_tokens": 6000,  # the default reasoning setting thinks for more than 1,500 tokens
        "messages": [
            {"role": "system", "content": SYSTEM + "\n\n" + persona},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": image_url(screen)}},
                {"type": "text", "text": question},
            ]},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": "decision", "strict": True, "schema": schema(actions)}},
    }
    if effort:
        body["reasoning_effort"] = effort
    status, data, sec = call(env, "POST", "/chat/completions", body)
    row = {"case": name, "model": model, "effort": effort or "default", "status": status, "seconds": round(sec, 2)}
    if status != 200:
        row["error"] = str(data)[:300]
        return row
    u = data.get("usage", {})
    row["in"], row["out"] = u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
    row["reasoning"] = u.get("completion_tokens_details", {}).get("reasoning_tokens")
    pin, pout = PRICE[model]
    row["usd"] = (row["in"] * pin + row["out"] * pout) / 1e6
    row["finish"] = data["choices"][0].get("finish_reason")
    try:
        row["answer"] = json.loads(data["choices"][0]["message"]["content"])
        row["prob_sum"] = round(sum(row["answer"]["probabilities"].values()), 3)
    except Exception as e:  # keep malformed answers in the record too
        row["error"] = f"parse: {e}: {str(data['choices'][0]['message'].get('content'))[:200]}"
    return row


def main():
    env = load_env()
    quick = "--quick" in sys.argv
    repeats = 1 if quick else 4
    jobs = [(m, e, c) for m in PRICE for e in (None, "minimal") for c in CASES for _ in range(repeats)]
    print(f"{len(jobs)} calls...")
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(lambda j: run_one(env, *j), jobs))

    out = HERE / "results" / f"spark_decide_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False))

    bad = [r for r in rows if "error" in r]
    print(f"\nok {len(rows) - len(bad)}/{len(rows)}  -> {out.relative_to(HERE.parent.parent)}")
    for r in bad:
        print("  failed:", r["case"], r["model"], r["effort"], r["status"], r["error"][:160])

    key = {"ad": "install", "plan_a_paywall": "delete_app", "plan_b_nearby": "delete_app"}
    print(f"\n{'case':16} {'model':14} {'effort':8} {'key prob (mean [min-max])':28} {'sec':>5} {'in':>6} {'out':>5} {'$/call':>9}")
    for model in PRICE:
        for effort in ("default", "minimal"):
            for c in CASES:
                rs = [r for r in rows if r["model"] == model and r["effort"] == effort and r["case"] == c[0] and "answer" in r]
                if not rs:
                    continue
                ps = [r["answer"]["probabilities"][key[c[0]]] for r in rs]
                label = f"{key[c[0]]} {statistics.mean(ps):.2f} [{min(ps):.2f}–{max(ps):.2f}]"
                short = "contributor" if "contributor" in model else "standard"
                print(f"{c[0]:16} {short:14} {effort:8} {label:28} {statistics.mean(r['seconds'] for r in rs):5.1f} "
                      f"{statistics.mean(r['in'] for r in rs):6.0f} {statistics.mean(r['out'] for r in rs):5.0f} "
                      f"{statistics.mean(r['usd'] for r in rs):9.5f}")

    print("\nExample answers (first per model and setting):")
    seen = set()
    for r in rows:
        k = (r["case"], r["model"], r["effort"])
        if "answer" in r and k not in seen:
            seen.add(k)
            a = r["answer"]
            print(f"  [{r['case']} · {'contrib' if 'contributor' in r['model'] else 'std'} · {r['effort']}] "
                  f"noticed={a['noticed']!r} · {a['probabilities']} · \"{a['reason']}\"")
    print(f"\ntotal cost ${sum(r.get('usd', 0) for r in rows):.4f}")


if __name__ == "__main__":
    main()
