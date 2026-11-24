import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from _loader import load

ex = load("t04_fastapi_backend", "ex_05_dependency_injection")
client = TestClient(ex.app)


@pytest.fixture(autouse=True)
def _reset():
    ex.EVENTS.clear()
    ex.app.dependency_overrides.clear()
    yield
    ex.app.dependency_overrides.clear()


def test_pagination_defaults_and_values():
    r = client.get("/items")
    assert r.json()["page"] == {"skip": 0, "limit": 10}
    assert r.json()["items"] == list(range(1, 11))
    r = client.get("/items", params={"skip": 5, "limit": 3})
    assert r.json()["items"] == [6, 7, 8]


@pytest.mark.parametrize("params", [{"skip": -1}, {"limit": 0}, {"limit": 51}])
def test_pagination_validation(params):
    assert client.get("/items", params=params).status_code == 422


def test_get_db_generator_closes():
    gen = ex.get_db()
    db = next(gen)
    assert isinstance(db, ex.FakeDB) and not db.closed
    with pytest.raises(StopIteration):
        next(gen)
    assert db.closed


def test_get_db_closes_even_on_error():
    gen = ex.get_db()
    db = next(gen)
    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("boom"))
    assert db.closed


def test_get_db_used_by_route():
    r = client.get("/db-check")
    assert r.json() == {"closed_during_request": False}
    assert ex.EVENTS == ["db closed"]


def test_api_key():
    assert client.get("/admin").status_code == 401
    r = client.get("/admin", headers={"X-API-Key": "wrong"})
    assert r.status_code == 401
    assert r.json() == {"detail": "Invalid API key"}
    r = client.get("/admin", headers={"X-API-Key": ex.API_KEY})
    assert r.status_code == 200 and r.json() == {"secret": "42"}


def test_user_filter_class_dependency():
    assert client.get("/users").json() == ["Ada", "Adam", "Grace"]
    assert client.get("/users", params={"q": "ADA"}).json() == ["Ada", "Adam"]
    assert client.get("/users", params={"active_only": "true"}).json() == ["Ada", "Grace"]
    assert client.get("/users", params={"q": "ada", "active_only": 1}).json() == ["Ada"]


def test_greet_uses_overridable_dependency():
    assert client.get("/greet").json() == {"message": "Hello, world!"}
    ex.app.dependency_overrides[ex.get_current_user] = lambda: {"name": "Test"}
    assert client.get("/greet").json() == {"message": "Hello, Test!"}
