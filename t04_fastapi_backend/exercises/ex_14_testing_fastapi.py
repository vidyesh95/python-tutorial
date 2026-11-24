"""Exercise 14: Testing FastAPI apps.

The app below is finished. You write the TEST HELPERS people use around it.

Tasks
1. make_client: build a TestClient for an app (lifespan NOT needed).
2. override_dependency: install a dependency override and return a `reset` callable
   that removes ONLY that override.
3. frozen_client: a TestClient whose `get_clock` dependency always returns `moment`.
4. async_get_json: GET a path with httpx.AsyncClient + ASGITransport and return the JSON.
5. concurrent_statuses: GET many paths concurrently (asyncio.gather) and return status codes
   in the same order as the paths.

Run: uv run pytest t04_fastapi_backend -k testing_fastapi
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


def get_clock() -> datetime:
    return datetime.now(UTC)


app = FastAPI()


@app.get("/now")
def now(clock: Annotated[datetime, Depends(get_clock)]) -> dict[str, str]:
    return {"now": clock.isoformat()}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def make_client(app: FastAPI) -> TestClient:
    """Return TestClient(app)."""
    raise NotImplementedError


def override_dependency(
    app: FastAPI, dependency: Callable[..., Any], replacement: Callable[..., Any]
) -> Callable[[], None]:
    """Set app.dependency_overrides[dependency] = replacement.

    Return a zero-argument `reset()` that removes that single override (and leaves any
    other overrides alone). Calling reset() twice must not raise.
    """
    raise NotImplementedError


def frozen_client(app: FastAPI, moment: datetime) -> TestClient:
    """Return a client for which `get_clock` returns `moment`. Reuse your helpers."""
    raise NotImplementedError


async def async_get_json(app: FastAPI, path: str) -> Any:
    """GET `path` using httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
    base_url="http://test") and return response.json().
    """
    raise NotImplementedError


async def concurrent_statuses(app: FastAPI, paths: list[str]) -> list[int]:
    """GET every path concurrently with one AsyncClient; return status codes in order."""
    raise NotImplementedError
