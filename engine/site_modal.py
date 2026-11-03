"""The public site on Modal: the built web app and the live interview API (engine/serve.py) on one URL.

    cd web && npm run build && cd ..
    .venv/bin/modal deploy engine/site_modal.py     # https://<workspace>--rehearsal.modal.run

The Meta API key comes from the Modal secret `rehearsal-meta` (META_API_KEY), which the owner creates
once with `modal secret create`; it is never in the repo or the image. The same secret may hold
ADMIN_KEY, which turns on live rehearsal runs for the admin (engine/live.py: the brief and screens the
Setup page posts to /api/live). One container serves everyone, so the per-visitor and daily caps in
serve.py and live.py hold for the whole site, and a live run's files stay in its /tmp/live folder.
"""

import os

import modal

BASE_URL = "https://api.meta.ai/v1"

app = modal.App("rehearsal")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("fastapi[standard]==0.115.12", "numpy>=2.0", "pyyaml>=6.0")
    .env({"LIVE_DIR": "/tmp/live"})
    .add_local_python_source("engine")
    .add_local_dir("plans", "/root/plans")                              # market values for live runs
    .add_local_dir("web/public/replays", "/root/web/public/replays")   # the interview reads records from here
    .add_local_dir("web/dist", "/root/web/dist")
)


@app.function(image=image, secrets=[modal.Secret.from_name("rehearsal-meta")],
              min_containers=1, max_containers=1, timeout=120)
@modal.concurrent(max_inputs=32)
@modal.asgi_app(label="rehearsal")
def site():
    from fastapi import FastAPI, Request
    from fastapi.concurrency import run_in_threadpool
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles

    from fastapi.responses import Response

    from engine.serve import MAX_AUDIO, MAX_UPLOAD, Limits, handle, handle_live

    env = {"MODEL_API_BASE_URL": BASE_URL, "MODEL_API_KEY": os.environ["META_API_KEY"],
           "ADMIN_KEY": os.environ.get("ADMIN_KEY", "")}
    os.environ.setdefault("MODEL_API_KEY", env["MODEL_API_KEY"])     # for Wonder and Spark inside a live run
    limits = Limits()
    web = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @web.api_route("/api/live{rest:path}", methods=["GET", "POST"])
    async def live(rest: str, request: Request):
        if int(request.headers.get("content-length", 0)) > MAX_UPLOAD:
            return JSONResponse({"error": "too large"}, status_code=413)
        raw = await request.body()
        status, ctype, body = await run_in_threadpool(handle_live, env, request.method, "/api/live" + rest,
                                                      request.headers.get("x-admin-key", ""),
                                                      request.headers.get("content-type", ""), raw)
        return Response(body, status_code=status, media_type=ctype)

    @web.post("/api/{name}")
    async def api(name: str, request: Request):
        if int(request.headers.get("content-length", 0)) > MAX_AUDIO:
            return JSONResponse({"error": "too large"}, status_code=413)
        raw = await request.body()
        ip = (request.headers.get("x-forwarded-for") or request.client.host).split(",")[0].strip()
        status, data = await run_in_threadpool(handle, env, limits, f"/api/{name}", ip, raw)
        return JSONResponse(data, status_code=status)

    @web.middleware("http")
    async def cache(request: Request, call_next):
        # Mounted files carry a 1970 Last-Modified, so browsers would keep an old index.html for years
        # and ask for a script the next deploy removed. Only the hashed build files may be kept.
        response = await call_next(request)
        if request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-cache"
        return response

    web.mount("/", StaticFiles(directory="/root/web/dist", html=True))
    return web
