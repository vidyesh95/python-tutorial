import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from _loader import load

ex = load("t04_fastapi_backend", "ex_04_pydantic_models_validation")
client = TestClient(ex.app)

GOOD = {"email": "  Ada@Example.COM ", "name": "Ada", "age": 36, "password": "analytic1"}


@pytest.fixture(autouse=True)
def _clean_db():
    ex.USERS.clear()
    yield
    ex.USERS.clear()


def test_normalize_email():
    assert ex.normalize_email("  Ada@Example.COM ") == "ada@example.com"
    with pytest.raises(ValueError):
        ex.normalize_email("no-at-sign")


def test_check_password():
    assert ex.check_password("longenough1") == "longenough1"
    with pytest.raises(ValueError):
        ex.check_password("short1")
    with pytest.raises(ValueError):
        ex.check_password("nodigitshere")


def test_create_user_hides_secrets_and_normalizes():
    r = client.post("/users", json=GOOD)
    assert r.status_code == 201
    body = r.json()
    assert body == {"id": 1, "email": "ada@example.com", "name": "Ada", "age": 36}
    assert ex.USERS[1]["password_hash"] == "hashed:analytic1"


def test_create_user_validation_errors_are_422():
    assert client.post("/users", json={**GOOD, "email": "bad"}).status_code == 422
    assert client.post("/users", json={**GOOD, "password": "short"}).status_code == 422
    assert client.post("/users", json={**GOOD, "name": ""}).status_code == 422
    assert client.post("/users", json={**GOOD, "age": 200}).status_code == 422


def test_duplicate_email_conflict():
    assert client.post("/users", json=GOOD).status_code == 201
    r = client.post("/users", json={**GOOD, "email": "ADA@example.com"})
    assert r.status_code == 409


def test_ids_increment():
    client.post("/users", json=GOOD)
    r = client.post("/users", json={**GOOD, "email": "b@example.com"})
    assert r.json()["id"] == 2


def test_get_user():
    client.post("/users", json=GOOD)
    r = client.get("/users/1")
    assert r.status_code == 200
    assert "password_hash" not in r.json()
    r = client.get("/users/42")
    assert r.status_code == 404
    assert r.json() == {"detail": "User not found"}


def test_patch_only_sent_fields():
    client.post("/users", json=GOOD)
    r = client.patch("/users/1", json={"age": 37})
    assert r.json()["age"] == 37
    assert r.json()["name"] == "Ada"  # untouched
    r = client.patch("/users/1", json={"age": None})  # explicit null IS a sent field
    assert r.json()["age"] is None
    assert r.json()["name"] == "Ada"
    assert client.patch("/users/9", json={"name": "x"}).status_code == 404
