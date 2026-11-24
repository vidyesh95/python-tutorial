import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from _loader import load

ex = load("t04_fastapi_backend", "ex_03_path_query_body_params")
client = TestClient(ex.app)


def test_search_defaults():
    r = client.get("/search", params={"q": "py"})
    assert r.status_code == 200
    assert r.json() == {"q": "py", "limit": 10, "tags": []}


def test_search_tags_are_query_list():
    r = client.get("/search", params={"q": "py", "tags": ["a", "b"], "limit": 5})
    assert r.json() == {"q": "py", "limit": 5, "tags": ["a", "b"]}


@pytest.mark.parametrize("params", [{"q": "p"}, {"q": "x" * 21}, {"q": "ok", "limit": 0}])
def test_search_validation(params):
    assert client.get("/search", params={**params}).status_code == 422
    assert client.get("/search", params={"q": "ok", "limit": 51}).status_code == 422


def test_search_requires_q():
    assert client.get("/search").status_code == 422


def test_get_order():
    assert client.get("/orders/7").json() == {"order_id": 7}
    assert client.get("/orders/0").status_code == 422


def test_create_item_query_and_body():
    r = client.post("/items", params={"quantity": 3}, json={"name": "pen", "price": 2.0})
    assert r.status_code == 200
    assert r.json() == {"name": "pen", "total": 6.0}
    r = client.post("/items", json={"name": "pen", "price": 2.0})
    assert r.json()["total"] == 2.0
    assert (
        client.post("/items", params={"quantity": 0}, json={"name": "p", "price": 1}).status_code
        == 422
    )


def test_whoami_header():
    assert client.get("/whoami").json() == {"user": "anonymous"}
    assert client.get("/whoami", headers={"X-User": "ada"}).json() == {"user": "ada"}
    # A query param named x_user must NOT be accepted as a replacement for the header.
    assert client.get("/whoami", params={"x_user": "mallory"}).json() == {"user": "anonymous"}


def test_replace_item():
    r = client.put("/items/4", json={"name": "cup", "price": 3.5})
    assert r.json() == {"item_id": 4, "name": "cup", "price": 3.5}
