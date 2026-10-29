"""첫 스파이크: Spark 가 앱 화면 이미지 + 페르소나를 보고 구조화된 판단을 내리는가.

    python3 engine/spike/spark_decide.py            # 전체 (약 48회 호출, 몇 센트)
    python3 engine/spike/spark_decide.py --quick    # 모델·설정별 1회씩

확인할 것
1. json_schema 로 묶은 답이 항상 형식대로 오는가 (확률 합 ≈ 1)
2. 화면 내용이 판단을 바꾸는가: 41마일 + 결제 벽(계획 A) vs 2마일 + 매치 + 무료(계획 B)
3. 같은 질문을 반복하면 얼마나 흔들리는가
4. 호출 1회 비용·지연, reasoning_effort 를 낮추면 얼마나 줄고 판단이 달라지는가
결과는 engine/spike/results/ 에 JSON 으로 남긴다. 키 값은 저장·출력하지 않는다.
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

# 100만 토큰당 달러 (04_사실확인.md). 추론 토큰은 출력으로 과금된다고 가정.
PRICE = {"muse-spark-1.3": (1.25, 4.25), "muse-spark-1.3-contributor": (0.10, 0.20)}

MAYA = (
    "You are Maya, 24, a dental assistant in Columbus, Ohio. You moved there a year ago and know few people. "
    "Money is tight: you pay for Spotify and nothing else. You get bored of apps fast. "
    "You saw a TikTok ad for Kindred, a new dating app, and installed it 3 days ago."
)
# 지금까지 겪은 일 (실제 엔진에서는 시뮬레이션 기억에서 온다). 화면과 어긋나지 않게.
HISTORY_A = " You have swiped through every profile it showed you. Everyone is far away and you have no matches."
HISTORY_B = " The first two days were quiet. Today you got your first match."

# (이름, 화면, 페르소나, 그 화면에서 할 수 있는 행동, 질문)
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
        "max_tokens": 6000,  # 기본 추론 설정은 1,500 토큰을 넘게 생각한다
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
    except Exception as e:  # 형식이 깨진 경우도 그대로 기록
        row["error"] = f"parse: {e}: {str(data['choices'][0]['message'].get('content'))[:200]}"
    return row


def main():
    env = load_env()
    quick = "--quick" in sys.argv
    repeats = 1 if quick else 4
    jobs = [(m, e, c) for m in PRICE for e in (None, "minimal") for c in CASES for _ in range(repeats)]
    print(f"{len(jobs)}회 호출…")
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(lambda j: run_one(env, *j), jobs))

    out = HERE / "results" / f"spark_decide_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False))

    bad = [r for r in rows if "error" in r]
    print(f"\n성공 {len(rows) - len(bad)}/{len(rows)}  → {out.relative_to(HERE.parent.parent)}")
    for r in bad:
        print("  실패:", r["case"], r["model"], r["effort"], r["status"], r["error"][:160])

    key = {"ad": "install", "plan_a_paywall": "delete_app", "plan_b_nearby": "delete_app"}
    print(f"\n{'case':16} {'model':14} {'effort':8} {'핵심 확률(평균 [최소–최대])':28} {'초':>5} {'입력':>6} {'출력':>5} {'$/회':>9}")
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

    print("\n답 예시 (모델·설정별 첫 번째):")
    seen = set()
    for r in rows:
        k = (r["case"], r["model"], r["effort"])
        if "answer" in r and k not in seen:
            seen.add(k)
            a = r["answer"]
            print(f"  [{r['case']} · {'contrib' if 'contributor' in r['model'] else 'std'} · {r['effort']}] "
                  f"noticed={a['noticed']!r} · {a['probabilities']} · \"{a['reason']}\"")
    print(f"\n총 비용 ${sum(r.get('usd', 0) for r in rows):.4f}")


if __name__ == "__main__":
    main()
