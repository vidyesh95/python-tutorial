# Middleware, CORS, Exception Handlers and Lifespan
"""
Middleware wraps EVERY request: code runs before the route, then again on the way out.

    @app.middleware("http")
    async def add_header(request: Request, call_next):
        # ... before the route ...
        response = await call_next(request)
        # ... after the route ...
        return response

Good uses: request IDs, timing, logging, security headers, CORS, compression, auth gates.

Ordering: the LAST middleware you add is the OUTERMOST (it sees the request first). Add
CORSMiddleware last so even error responses and preflights get CORS headers.

CORS: browsers block a page on origin A from reading responses from origin B unless B sends
`Access-Control-Allow-Origin`. The browser first sends a PREFLIGHT `OPTIONS` request (with
`Origin` + `Access-Control-Request-Method`) for non-simple requests. CORSMiddleware answers it.
CORS protects browsers only; curl and servers ignore it. It is NOT authentication.

Exception handlers turn exceptions into consistent JSON error bodies:
    @app.exception_handler(DomainError)
    async def handle(request, exc): return JSONResponse({...}, status_code=409)

Lifespan runs setup once at startup and teardown at shutdown (DB pools, HTTP clients, caches):
    @asynccontextmanager
    async def lifespan(app): ...setup...; yield; ...teardown...

Run live:  uv run fastapi dev t04_fastapi_backend/m_13_middleware_cors.py

Common mistakes
- `allow_origins=["*"]` together with `allow_credentials=True` (browsers reject it; and
  it is unsafe). List explicit origins when cookies/Authorization are involved.
- Adding CORS before other middleware so error responses lack CORS headers.
- `BaseHTTPMiddleware`-style `@app.middleware("http")` reading the whole body: it can break
  streaming and WebSockets. For heavy use write a pure ASGI middleware.
- Doing blocking work in middleware; it runs on the event loop for every request.
- Module-level global clients with no teardown instead of a lifespan.

Production notes
- Take the request ID from an upstream header (e.g. `X-Request-ID`) so a trace spans services;
  generate one only if missing. Echo it in the response and in logs (see m_17).
- Also consider GZipMiddleware (compress big JSON) and TrustedHostMiddleware (Host header
  allow-list). Terminate TLS and redirect HTTP at the proxy.
- Keep allowed origins in settings per environment (see m_19).
"""

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient


class DomainError(Exception):
    """A business-rule violation we want to report as a clean 409."""


# Example: lifespan (startup/shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.ready = True  # e.g. open DB pool, create httpx.AsyncClient
    yield
    app.state.ready = False  # e.g. close them


app = FastAPI(title="Middleware", lifespan=lifespan)


# Example: custom middleware, request-id + timing
@app.middleware("http")
async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id  # routes/handlers can read it
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-ms"] = f"{(time.perf_counter() - start) * 1000:.2f}"
    return response


# Example: exception handler -> consistent error body
@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"error": "conflict", "detail": str(exc), "request_id": request.state.request_id},
    )


# Example: CORS (added LAST so it is outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],  # explicit list, never "*" with credentials
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Request-ID"],  # so browser JS can read it
    max_age=600,
)


@app.get("/ping")
def ping(request: Request) -> dict[str, object]:
    return {"pong": True, "ready": request.app.state.ready, "id": request.state.request_id}


@app.post("/orders/{order_id}/cancel")
def cancel(order_id: int) -> None:
    raise DomainError(f"order {order_id} already shipped")


if __name__ == "__main__":
    # `with` runs lifespan startup/shutdown
    with TestClient(app) as client:
        r = client.get("/ping", headers={"X-Request-ID": "trace-123"})
        print(r.json(), r.headers["X-Request-ID"], "time header:", "X-Process-Time-ms" in r.headers)
        print("generated id:", len(client.get("/ping").headers["X-Request-ID"]), "chars")

        r = client.post("/orders/7/cancel")
        print(r.status_code, r.json()["detail"])

        # CORS preflight from an allowed origin, then from a stranger
        pre = {
            "Origin": "https://app.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        }
        r = client.options("/orders/7/cancel", headers=pre)
        print("preflight:", r.status_code, r.headers.get("access-control-allow-origin"))
        r = client.options("/orders/7/cancel", headers={**pre, "Origin": "https://evil.test"})
        print("evil origin:", r.status_code, r.headers.get("access-control-allow-origin"))
    print("ready after shutdown:", app.state.ready)
