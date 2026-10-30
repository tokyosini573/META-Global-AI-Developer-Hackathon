"""The site's small API: the live interview (engine/interview.py). Local development server.

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

from engine.check_api import load_env
from engine.interview import answer, transcribe

PORT = 8787
LIMIT = 30           # calls per visitor per hour
DAILY = 2000         # calls per day for everyone
MAX_AUDIO = 4_000_000

ENV = load_env()
seen = defaultdict(deque)
today = {"day": time.strftime("%Y-%m-%d"), "n": 0}


def allowed(ip):
    now = time.time()
    q = seen[ip]
    while q and now - q[0] > 3600:
        q.popleft()
    day = time.strftime("%Y-%m-%d")
    if today["day"] != day:
        today.update(day=day, n=0)
    if len(q) >= LIMIT or today["n"] >= DAILY:
        return False
    q.append(now)
    today["n"] += 1
    return True


class Handler(BaseHTTPRequestHandler):
    def send(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        size = int(self.headers.get("Content-Length", 0))
        if size > MAX_AUDIO:
            return self.send(413, {"error": "too large"})
        if not allowed(self.client_address[0]):
            return self.send(429, {"error": "Too many questions for now. Try again later."})
        raw = self.rfile.read(size)
        try:
            if self.path == "/api/transcribe":
                return self.send(200, {"text": transcribe(ENV, raw)})
            if self.path == "/api/interview":
                q = json.loads(raw)
                return self.send(200, {"answer": answer(ENV, q["replay"], q["plan"], int(q["id"]), q["question"])})
            return self.send(404, {"error": "not found"})
        except (KeyError, ValueError, StopIteration, FileNotFoundError):
            return self.send(400, {"error": "bad request"})
        except (RuntimeError, OSError) as e:
            print("upstream:", e)
            return self.send(502, {"error": "The model did not answer. Try again."})


if __name__ == "__main__":
    print(f"interview API on http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
