"""Exercise 13: Middleware, CORS, exception handlers and lifespan.

Tasks
1. add_request_id: middleware that reuses inbound `X-Request-ID` or generates a uuid4 hex,
   and sets it on the response header `X-Request-ID`.
2. not_found_handler: exception handler returning a JSON 404 body.
3. configure_cors: add CORSMiddleware for a list of allowed origins.
4. lifespan: set `app.state.ready` to True on startup and False on shutdown.

Run: uv run pytest t04_fastapi_backend -k middleware_cors
"""

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


class NotFoundError(Exception):
    pass


async def add_request_id(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Use the inbound X-Request-ID header if present, otherwise uuid.uuid4().hex.

    Store it on `request.state.request_id` and put it on the response as X-Request-ID.
    """
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Return status 404 with JSON {"error": "not_found", "detail": str(exc)}."""
    return JSONResponse(status_code=404, content={"error": "not_found", "detail": str(exc)})


def configure_cors(app: FastAPI, origins: list[str]) -> None:
    """Add CORSMiddleware to `app` allowing exactly `origins`, methods GET and POST,
    and the Content-Type / Authorization headers. No credentials.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
        allow_credentials=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Set `app.state.ready = True` at startup and False at shutdown."""
    app.state.ready = True
    yield
    app.state.ready = False


def create_app(origins: list[str] | None = None) -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.middleware("http")(add_request_id)
    app.add_exception_handler(NotFoundError, not_found_handler)  # type: ignore[arg-type]
    if origins:
        configure_cors(app, origins)

    @app.get("/items/{item_id}")
    def get_item(item_id: int) -> dict[str, int]:
        if item_id > 100:
            raise NotFoundError(f"item {item_id} not found")
        return {"id": item_id}

    @app.get("/state")
    def state(request: Request) -> dict[str, object]:
        return {"ready": getattr(request.app.state, "ready", None)}

    return app
