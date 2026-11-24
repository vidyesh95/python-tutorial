import asyncio
from datetime import UTC, datetime

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from _loader import load

ex = load("t04_fastapi_backend", "ex_14_testing_fastapi")


@pytest.fixture(autouse=True)
def no_leaked_overrides():
    yield
    ex.app.dependency_overrides.clear()


def test_make_client_returns_working_testclient():
    client = ex.make_client(ex.app)
    assert isinstance(client, TestClient)
    assert client.get("/health").json() == {"status": "ok"}


def test_override_dependency_and_reset():
    fixed = datetime(2030, 1, 2, 3, 4, 5, tzinfo=UTC)
    reset = ex.override_dependency(ex.app, ex.get_clock, lambda: fixed)
    client = TestClient(ex.app)
    assert client.get("/now").json() == {"now": fixed.isoformat()}
    reset()
    assert ex.get_clock not in ex.app.dependency_overrides
    assert client.get("/now").json()["now"] != fixed.isoformat()
    reset()  # idempotent


def test_reset_only_removes_its_own_override():
    def other() -> None: ...

    ex.app.dependency_overrides[other] = other
    reset = ex.override_dependency(ex.app, ex.get_clock, lambda: datetime.now(UTC))
    reset()
    assert other in ex.app.dependency_overrides


def test_frozen_client():
    moment = datetime(2024, 2, 29, 12, 0, tzinfo=UTC)
    client = ex.frozen_client(ex.app, moment)
    assert client.get("/now").json() == {"now": "2024-02-29T12:00:00+00:00"}


def test_async_get_json():
    assert asyncio.run(ex.async_get_json(ex.app, "/health")) == {"status": "ok"}


def test_concurrent_statuses_preserve_order():
    paths = ["/health", "/nope", "/now", "/health"]
    assert asyncio.run(ex.concurrent_statuses(ex.app, paths)) == [200, 404, 200, 200]
