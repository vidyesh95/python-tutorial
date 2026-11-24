import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from _loader import load

ex = load("t04_fastapi_backend", "ex_02_first_fastapi_app")
client = TestClient(ex.app)


def test_read_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"message": "Hello, FastAPI"}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_get_item():
    r = client.get("/items/2")
    assert r.status_code == 200
    assert r.json() == {"id": 2, "name": "mouse"}


def test_get_item_not_found():
    r = client.get("/items/99")
    assert r.status_code == 404
    assert r.json() == {"detail": "Item not found"}


def test_get_item_bad_id_is_422():
    # Validation happens before the handler runs (works even before you implement it).
    assert client.get("/items/abc").status_code == 422


def test_count_items_async():
    assert client.get("/items/count").json() == {"count": 3}
