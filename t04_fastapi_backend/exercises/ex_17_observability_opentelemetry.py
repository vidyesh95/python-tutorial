"""Exercise 17: Observability (structured logs, request id, health checks, OTel spans).

Tasks
1. JsonFormatter: render a log record as one JSON line, including the current request id.
2. request_id_middleware: set `request_id_var` for the request and echo it in a header.
3. readiness: run dependency checks and build a (status_code, body) result.
4. make_provider: a TracerProvider that sends finished spans to the given exporter.
5. record_span: create a span with attributes through a provider.

Run: uv run pytest t04_fastapi_backend -k observability
"""

import contextvars
import json  # noqa: F401  (handy for task 1)
import logging
import uuid  # noqa: F401  (handy for task 2)
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter  # noqa: F401

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        """Return json.dumps of {"level", "logger", "message", "request_id"}:
        record.levelname, record.name, record.getMessage(), request_id_var.get().
        """
        raise NotImplementedError


async def request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Take X-Request-ID from the request or generate uuid.uuid4().hex[:8].

    Set `request_id_var` while the request is handled (restore it afterwards with the
    token returned by .set()) and add the X-Request-ID response header.
    """
    raise NotImplementedError


def readiness(checks: dict[str, Callable[[], bool]]) -> tuple[int, dict[str, Any]]:
    """Run every check. A check that raises counts as failed (False).

    Return (200, {"status": "ready", "checks": {name: bool}}) if all passed, otherwise
    (503, {"status": "not_ready", "checks": {...}}). No checks at all means ready.
    """
    raise NotImplementedError


def make_provider(exporter: SpanExporter) -> TracerProvider:
    """Return a TracerProvider with a SimpleSpanProcessor(exporter) attached."""
    raise NotImplementedError


def record_span(provider: TracerProvider, name: str, attributes: dict[str, Any]) -> None:
    """Using provider.get_tracer(__name__), open a span called `name` with
    start_as_current_span and set every attribute on it.
    """
    raise NotImplementedError


def create_app(checks: dict[str, Callable[[], bool]] | None = None) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(request_id_middleware)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/readyz")
    def readyz() -> JSONResponse:
        status, body = readiness(checks or {})
        return JSONResponse(body, status_code=status)

    @app.get("/whoami")
    def whoami() -> dict[str, str]:
        return {"request_id": request_id_var.get()}

    return app
