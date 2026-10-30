"""The site's small API: the live interview (engine/interview.py). Local development server; the
public site serves the same handler from Modal (engine/site_modal.py).

    .venv/bin/python -m engine.serve        # http://localhost:8787, the Vite dev server proxies /api here

POST /api/transcribe  body: 16-bit mono WAV           -> {"text": ...}
POST /api/interview   {"replay", "plan", "id", "question"} -> {"answer": ...}

Each visitor (by IP) gets LIMIT calls an hour and the whole server DAILY a day, so a public demo
cannot drain the API credit.
"""

import json
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from engine.interview import answer, transcribe

PORT = 8787
LIMIT = 30           # calls per visitor per hour
DAILY = 2000         # calls per day for everyone
MAX_AUDIO = 4_000_000


class Limits:
    def __init__(self):
        self.seen = defaultdict(deque)
        self.today = {"day": time.strftime("%Y-%m-%d"), "n": 0}

    def allowed(self, ip):
        now = time.time()
        q = self.seen[ip]
        while q and now - q[0] > 3600:
            q.popleft()
        day = time.strftime("%Y-%m-%d")
        if self.today["day"] != day:
            self.today.update(day=day, n=0)
        if len(q) >= LIMIT or self.today["n"] >= DAILY:
            return False
        q.append(now)
        self.today["n"] += 1
        return True


def handle(env, limits, path, ip, raw):
    """(status, JSON body) for one API request."""
    if path not in ("/api/transcribe", "/api/interview"):
        return 404, {"error": "not found"}
    if len(raw) > MAX_AUDIO:
        return 413, {"error": "too large"}
    if not limits.allowed(ip):
        return 429, {"error": "Too many questions for now. Try again later."}
    try:
        if path == "/api/transcribe":
            return 200, {"text": transcribe(env, raw)}
        q = json.loads(raw)
        return 200, {"answer": answer(env, q["replay"], q["plan"], int(q["id"]), q["question"])}
    except (KeyError, ValueError, StopIteration, FileNotFoundError):
        return 400, {"error": "bad request"}
    except (RuntimeError, OSError) as e:
        print("upstream:", e)
        return 502, {"error": "The model did not answer. Try again."}


def main():
    from engine.check_api import load_env
    env, limits = load_env(), Limits()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            size = int(self.headers.get("Content-Length", 0))
            if size > MAX_AUDIO:
                status, data = 413, {"error": "too large"}
            else:
                status, data = handle(env, limits, self.path, self.client_address[0], self.rfile.read(size))
            body = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    print(f"interview API on http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
