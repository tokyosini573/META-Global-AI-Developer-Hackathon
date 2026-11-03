"""The site's small API: the live interview (engine/interview.py). Local development server; the
public site serves the same handler from Modal (engine/site_modal.py).

    .venv/bin/python -m engine.serve        # http://localhost:8787, the Vite dev server proxies /api here

POST /api/transcribe  body: 16-bit mono WAV           -> {"text": ...}
POST /api/interview   {"replay", "plan", "id", "question"} -> {"answer": ...}
/api/live...          the admin's live rehearsal runs (engine/live.py), with the X-Admin-Key header

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
MAX_UPLOAD = 20_000_000    # a live run's screens


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


def parse_multipart(content_type, raw):
    """{field name: bytes} from a multipart/form-data body."""
    from email.parser import BytesParser
    from email.policy import HTTP
    msg = BytesParser(policy=HTTP).parsebytes(b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + raw)
    return {part.get_param("name", header="content-disposition"): part.get_payload(decode=True)
            for part in msg.iter_parts()}


def handle_live(env, method, path, admin_key, content_type, raw):
    """(status, content type, body bytes) for the live-run API."""
    from engine import live
    js = lambda status, data: (status, "application/json", json.dumps(data).encode())   # noqa: E731
    parts = path.strip("/").split("/")[2:]          # after api/live
    try:
        if method == "GET" and len(parts) == 2 and parts[0] == "example":
            return js(200, live.example_spec(parts[1]))
        if method == "GET" and len(parts) == 3 and parts[1] == "screen":
            return 200, "image/png", live.screen(parts[0], parts[2])
        if not live.authorized(env, admin_key):
            return js(403, {"error": "Live runs are for the admin."})
        if method == "POST" and not parts:
            fields = parse_multipart(content_type, raw)
            spec = json.loads(fields.pop("spec"))
            return js(200, {"id": live.start(spec, fields, env)})
        if method == "GET" and len(parts) == 1:
            return js(200, live.status(parts[0]))
        if method == "GET" and len(parts) == 2 and parts[1] == "replay":
            return 200, "application/json", live.replay(parts[0])
        return js(404, {"error": "not found"})
    except PermissionError as e:
        return js(429, {"error": str(e)})
    except (KeyError, FileNotFoundError):
        return js(404, {"error": "not found"})
    except (ValueError, AssertionError) as e:
        return js(400, {"error": str(e) or "bad request"})


def main():
    from engine.check_api import load_env
    env, limits = load_env(), Limits()

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, ctype, body):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def live(self, method):
            size = int(self.headers.get("Content-Length", 0))
            if size > MAX_UPLOAD:
                return self.reply(413, "application/json", b'{"error": "too large"}')
            self.reply(*handle_live(env, method, self.path, self.headers.get("X-Admin-Key", ""),
                                    self.headers.get("Content-Type", ""), self.rfile.read(size) if size else b""))

        def do_GET(self):
            if self.path.startswith("/api/live"):
                return self.live("GET")
            self.reply(404, "application/json", b'{"error": "not found"}')

        def do_POST(self):
            if self.path.startswith("/api/live"):
                return self.live("POST")
            size = int(self.headers.get("Content-Length", 0))
            if size > MAX_AUDIO:
                status, data = 413, {"error": "too large"}
            else:
                status, data = handle(env, limits, self.path, self.client_address[0], self.rfile.read(size))
            self.reply(status, "application/json", json.dumps(data).encode())

    print(f"interview API on http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
