# Testing FastAPI Apps
"""
Three tools cover almost everything:

1. `TestClient(app)` (sync, built on httpx). Call `client.get(...)` like `requests`. It runs
   the ASGI app in-process: no server, no ports. Use `with TestClient(app) as client:` when
   you need lifespan startup/shutdown to run. Server exceptions are re-raised in the test.
2. `app.dependency_overrides[dep] = replacement`. Swap a database session, clock, current
   user, or external API client for a fake. ALWAYS clear it afterwards.
3. `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")` for async
   tests (needed when the test itself must `await` things, e.g. an async DB or Redis).

Pytest patterns (this is how you would write them in tests/):

    @pytest.fixture
    def client():
        with TestClient(app) as c:        # setup + teardown in one place
            yield c

    @pytest.fixture
    def fake_user():
        app.dependency_overrides[get_current_user] = lambda: User(id=1, name="test")
        yield
        app.dependency_overrides.clear()  # no leakage into the next test

    @pytest.mark.parametrize("item_id, status", [(1, 200), (99, 404)])
    def test_get_item(client, item_id, status):
        assert client.get(f"/items/{item_id}").status_code == status

    @pytest.mark.asyncio                   # pytest-asyncio; or just call asyncio.run(...)
    async def test_async():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            assert (await c.get("/health")).status_code == 200

Database tests: override `get_session` with a session bound to in-memory SQLite (or a
rolled-back transaction on test Postgres) so each test starts clean (see m_07/m_09).

This module is not a test file; its `__main__` runs the same kinds of checks directly.
Run live:  uv run fastapi dev t04_fastapi_backend/m_14_testing_fastapi.py
Real tests: uv run pytest t04_fastapi_backend

Common mistakes
- Leaving `dependency_overrides` set, so tests pass or fail depending on order.
- Testing against shared real state (dev database, real Redis, the network).
- Asserting only the status code. Check body, headers, and side effects too.
- Forgetting `with TestClient(app)`, so lifespan never ran and `app.state` is empty.
- `@pytest.mark.asyncio` on tests without pytest-asyncio installed/configured (they silently
  do not run or are skipped).

Production notes
- Test pyramid: many fast unit tests for pure logic, a solid layer of API tests like these,
  few end-to-end tests against real services (Docker compose in CI).
- Fail CI under a coverage floor (`pytest --cov --cov-fail-under=80`).
- Prefer fakes (fakeredis, in-memory SQLite) to heavy mocks; test behaviour, not internals.
"""

import asyncio
from collections.abc import Callable
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

app = FastAPI(title="Testing demo")

ITEMS = {1: "keyboard", 2: "mouse"}


# Dependencies are the seams that make an app testable
def get_items() -> dict[int, str]:
    return ITEMS


def get_current_user(x_user: Annotated[str | None, Header()] = None) -> str:
    if x_user is None:
        raise HTTPException(status_code=401, detail="missing X-User")
    return x_user


ItemsDep = Annotated[dict[int, str], Depends(get_items)]
UserDep = Annotated[str, Depends(get_current_user)]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/items/{item_id}")
def read_item(item_id: int, items: ItemsDep) -> dict[str, object]:
    if item_id not in items:
        raise HTTPException(status_code=404, detail="item not found")
    return {"id": item_id, "name": items[item_id]}


@app.get("/me")
def me(user: UserDep) -> dict[str, str]:
    return {"user": user}


# A tiny check runner so the demo reads like a test report
def check(name: str, condition: bool) -> None:
    print(f"{'PASS' if condition else 'FAIL'}  {name}")
    assert condition, name


def demo_testclient() -> None:
    client = TestClient(app)
    check("GET /items/1 -> 200", client.get("/items/1").json() == {"id": 1, "name": "keyboard"})
    check("GET /items/99 -> 404", client.get("/items/99").status_code == 404)
    check("GET /items/abc -> 422 (validation)", client.get("/items/abc").status_code == 422)
    check("GET /me without header -> 401", client.get("/me").status_code == 401)
    check(
        "GET /me with header", client.get("/me", headers={"X-User": "ada"}).json()["user"] == "ada"
    )


def demo_overrides() -> None:
    fake_items = {7: "fake-item"}
    app.dependency_overrides[get_items] = lambda: fake_items
    app.dependency_overrides[get_current_user] = lambda: "test-user"
    try:  # in pytest this is a fixture with yield + clear()
        client = TestClient(app)
        check("override items", client.get("/items/7").json()["name"] == "fake-item")
        check("override user (no header needed)", client.get("/me").json() == {"user": "test-user"})
    finally:
        app.dependency_overrides.clear()
    check("override cleared", TestClient(app).get("/items/7").status_code == 404)


async def demo_async() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        responses = await asyncio.gather(client.get("/health"), client.get("/items/2"))
    check("AsyncClient health", responses[0].json() == {"status": "ok"})
    check("AsyncClient item", responses[1].json()["name"] == "mouse")


def demo_async_client() -> None:
    asyncio.run(demo_async())  # in pytest-asyncio you would `await` it in an async test


def run_checks(*checks: Callable[[], None]) -> None:
    for fn in checks:
        print(f"-- {fn.__name__}")
        fn()


if __name__ == "__main__":
    run_checks(demo_testclient, demo_overrides, demo_async_client)
    print("all checks passed")
