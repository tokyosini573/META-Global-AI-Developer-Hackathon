"""Check once that the Meta Model API key works. Never prints the key.

    python3 engine/check_api.py

1) list models (is the key valid)  2) one tiny call (does credit return a real answer; tokens and time)
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
        raise SystemExit("No .env found. Copy .env.example to .env.")
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def call(env, method, path, body=None, timeout=60):
    req = urllib.request.Request(
        env["MODEL_API_BASE_URL"].rstrip("/") + path,
        method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {env['MODEL_API_KEY']}", "Content-Type": "application/json"},
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read()), time.time() - start
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:500], time.time() - start


def main():
    env = load_env()
    key = env.get("MODEL_API_KEY", "")
    if not key:
        raise SystemExit("MODEL_API_KEY is empty. Paste your key into .env.")
    print(f"key: {len(key)} chars (value not printed)")

    status, data, _ = call(env, "GET", "/models")
    print(f"\n[1] model list -> HTTP {status}")
    if status != 200:
        print(data)
        raise SystemExit("Key rejected. 401/403 means a key problem; otherwise see the message above.")
    for m in data.get("data", []):
        print("  -", m.get("id"))

    model = env.get("MODEL_API_MODEL", "muse-spark-1.3")
    status, data, sec = call(env, "POST", "/chat/completions", {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with the single word: ready"}],
        "max_tokens": 512,  # reasoning tokens come before the answer, so leave room
    })
    print(f"\n[2] {model} short call -> HTTP {status}, {sec:.1f}s")
    if status != 200:
        print(data)
        raise SystemExit("Call failed. 402 means credit/billing, 429 means rate limit.")
    print("  answer:", (data["choices"][0]["message"]["content"] or "(empty)").strip())
    print("  tokens:", data.get("usage"))
    print("\nKey and credit both work.")


if __name__ == "__main__":
    main()
