# Your First FastAPI App
"""
FastAPI is an ASGI web framework built on Starlette (HTTP) and Pydantic (validation).
You write plain Python functions; type hints become request parsing, validation, and docs.

The pieces:
- `app = FastAPI(...)`: the application object (an ASGI callable a server like uvicorn runs).
- `@app.get("/path")` etc.: a PATH OPERATION decorator = method + path -> your function.
- The function's return value is serialized to JSON automatically (dict, list, models...).
- `status_code=` sets the success code; `HTTPException` produces error responses.
- `def` handlers run in a thread pool; `async def` handlers run on the event loop.
  Use `async def` only when everything inside is awaited (async DB driver, httpx.AsyncClient).
  A blocking call inside `async def` freezes the whole server.
- Free docs: Swagger UI at /docs, ReDoc at /redoc, the OpenAPI schema at /openapi.json.

Serve it live:  uv run fastapi dev t04_fastapi_backend/m_02_first_fastapi_app.py
                (dev = auto-reload, binds 127.0.0.1:8000; then open /docs)
                uv run fastapi run ...   (production-style: no reload)
Run the offline demo: uv run python -m t04_fastapi_backend.m_02_first_fastapi_app

Test without a server: `fastapi.testclient.TestClient(app)` calls the app in-process and
gives you an httpx-style response (`.status_code`, `.json()`, `.headers`).
"""

import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

# Example: the application object, with metadata that shows up in /docs
app = FastAPI(
    title="First App",
    version="0.1.0",
    description="Smallest useful FastAPI service.",
)


# Example: the simplest endpoint
@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, FastAPI"}


# Example: path parameter, typed -> "/users/7" gives int 7; "/users/abc" gives 422
USERS = {1: "ada", 2: "grace"}


@app.get("/users/{user_id}", tags=["users"], summary="Fetch one user")
def read_user(user_id: int) -> dict[str, int | str]:
    """The docstring becomes the endpoint description in /docs."""
    if user_id not in USERS:
        raise HTTPException(status_code=404, detail="User not found")  # error -> JSON body
    return {"id": user_id, "name": USERS[user_id]}


# Example: async endpoint - fine because we only `await` non-blocking things
@app.get("/slow")
async def slow() -> dict[str, str]:
    await asyncio.sleep(0.01)  # stands in for an async DB/HTTP call
    return {"status": "done"}


# Example: a different method and status code
@app.post("/ping", status_code=202)
def ping() -> dict[str, bool]:
    return {"accepted": True}


"""
Common mistakes:
- `time.sleep()` or a blocking DB/HTTP call inside `async def` (stalls every request).
  Either make the handler plain `def`, or use an async library.
- Forgetting the return annotation/type hints: you lose validation and docs quality.
- Defining two handlers for the same method+path: the first one silently wins.
- Running `python file.py` and expecting a server: you need `fastapi dev` or uvicorn.
- Raising `Exception` for expected errors (-> 500). Use HTTPException(status_code=...).

Production notes:
- Run with `fastapi run` / `uvicorn module:app --host 0.0.0.0` behind a reverse proxy;
  scale with multiple worker processes (`--workers N`), not with `--reload`.
- Disable or protect /docs in public deployments if the API is private
  (`FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`).
- Add a cheap `/health` endpoint for load balancer and Kubernetes probes.
- Set `title`/`version` - they surface in generated client SDKs.
"""

if __name__ == "__main__":
    client = TestClient(app)
    print(client.get("/").json())
    print(client.get("/users/1").json())
    r = client.get("/users/99")
    print(r.status_code, r.json())  # 404 {'detail': 'User not found'}
    r = client.get("/users/abc")
    print(r.status_code, r.json()["detail"][0]["type"])  # 422 int_parsing
    print(client.get("/slow").json())
    print(client.post("/ping").status_code)  # 202
    print(client.get("/openapi.json").json()["info"])  # auto-generated schema
    print(sorted(client.get("/openapi.json").json()["paths"]))
