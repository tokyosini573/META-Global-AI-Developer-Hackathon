"""Meta Model API 키가 살아 있는지 한 번 확인한다. 키 값은 절대 출력하지 않는다.

    python3 engine/check_api.py

1) 모델 목록 (키가 맞는지)  2) 아주 짧은 호출 1번 (크레딧으로 실제 답이 오는지, 토큰·시간)
"""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    env = {}
    path = ROOT / ".env"
    if not path.exists():
        raise SystemExit(".env 가 없습니다. .env.example 을 .env 로 복사하세요.")
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def call(env, method, path, body=None):
    req = urllib.request.Request(
        env["MODEL_API_BASE_URL"].rstrip("/") + path,
        method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {env['MODEL_API_KEY']}", "Content-Type": "application/json"},
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read()), time.time() - start
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:500], time.time() - start


def main():
    env = load_env()
    key = env.get("MODEL_API_KEY", "")
    if not key:
        raise SystemExit("MODEL_API_KEY 가 비어 있습니다. .env 에 키를 붙여 넣으세요.")
    print(f"키: {len(key)}자 (값은 출력하지 않음)")

    status, data, _ = call(env, "GET", "/models")
    print(f"\n[1] 모델 목록 → HTTP {status}")
    if status != 200:
        print(data)
        raise SystemExit("키가 거절됐습니다. 401/403 이면 키 문제, 그 외는 아래 메시지를 확인하세요.")
    for m in data.get("data", []):
        print("  -", m.get("id"))

    model = env.get("MODEL_API_MODEL", "muse-spark-1.3")
    status, data, sec = call(env, "POST", "/chat/completions", {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with the single word: ready"}],
        "max_tokens": 512,  # 답하기 전에 추론 토큰을 먼저 쓰므로 넉넉하게
    })
    print(f"\n[2] {model} 짧은 호출 → HTTP {status}, {sec:.1f}초")
    if status != 200:
        print(data)
        raise SystemExit("호출 실패. 402 면 크레딧/결제, 429 면 한도 문제입니다.")
    print("  답:", (data["choices"][0]["message"]["content"] or "(빈 답)").strip())
    print("  토큰:", data.get("usage"))
    print("\n키와 크레딧 모두 정상입니다.")


if __name__ == "__main__":
    main()
