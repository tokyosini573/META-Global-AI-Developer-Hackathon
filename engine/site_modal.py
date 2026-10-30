"""The public site on Modal: the built web app and the live interview API (engine/serve.py) on one URL.

    cd web && npm run build && cd ..
    .venv/bin/modal deploy engine/site_modal.py     # https://<workspace>--rehearsal.modal.run

The Meta API key comes from the Modal secret `rehearsal-meta` (META_API_KEY), which the owner creates
once with `modal secret create`; it is never in the repo or the image. One container serves everyone,
so the per-visitor and daily caps in serve.py hold for the whole site.
"""

import os

import modal

BASE_URL = "https://api.meta.ai/v1"

app = modal.App("rehearsal")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("fastapi[standard]==0.115.12")
    .add_local_python_source("engine")
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

    from engine.serve import MAX_AUDIO, Limits, handle

    env = {"MODEL_API_BASE_URL": BASE_URL, "MODEL_API_KEY": os.environ["META_API_KEY"]}
    limits = Limits()
    web = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @web.post("/api/{name}")
    async def api(name: str, request: Request):
        if int(request.headers.get("content-length", 0)) > MAX_AUDIO:
            return JSONResponse({"error": "too large"}, status_code=413)
        raw = await request.body()
        ip = (request.headers.get("x-forwarded-for") or request.client.host).split(",")[0].strip()
        status, data = await run_in_threadpool(handle, env, limits, f"/api/{name}", ip, raw)
        return JSONResponse(data, status_code=status)

    web.mount("/", StaticFiles(directory="/root/web/dist", html=True))
    return web
