import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from _loader import load

ex = load("t04_fastapi_backend", "ex_06_routers_project_structure")


@pytest.fixture
def client():
    return TestClient(ex.create_app())


def test_make_router_standalone_shape():
    router = ex.make_router("things", {1: "a"})
    assert router.prefix == "/things"
    assert router.tags == ["things"]


def test_resource_routes(client):
    assert client.get("/api/v1/books").json() == ["Dune", "Emma"]
    assert client.get("/api/v1/books/2").json() == "Emma"
    assert client.get("/api/v1/authors").json() == ["Herbert", "Austen", "Le Guin"]
    r = client.get("/api/v1/authors/9")
    assert r.status_code == 404
    assert r.json() == {"detail": "authors not found"}


def test_routers_do_not_share_data(client):
    # A classic closure bug: both routers end up serving the last dict.
    assert client.get("/api/v1/books/3").status_code == 404
    assert client.get("/api/v1/authors/3").json() == "Le Guin"


def test_admin_router_dependency(client):
    assert client.get("/api/v1/admin/stats").status_code == 403
    r = client.get("/api/v1/admin/stats", headers={"X-Admin": "yes"})
    assert r.json() == {"books": 2, "authors": 3}


def test_health_at_root(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/v1/health").status_code == 404


def test_create_app_is_a_factory():
    assert ex.create_app() is not ex.create_app()


def test_routes_by_tag():
    tags = ex.routes_by_tag(ex.create_app())
    assert list(tags) == ["admin", "authors", "books", "untagged"]
    assert tags["books"] == ["/api/v1/books", "/api/v1/books/{item_id}"]
    assert tags["admin"] == ["/api/v1/admin/stats"]
    assert tags["untagged"] == ["/health"]
