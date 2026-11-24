import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from _loader import load

ex = load("t04_fastapi_backend", "ex_13_middleware_cors")

ORIGIN = "https://app.example.com"


def test_request_id_generated():
    client = TestClient(ex.create_app())
    rid = client.get("/items/1").headers["X-Request-ID"]
    assert len(rid) == 32 and rid != client.get("/items/1").headers["X-Request-ID"]


def test_request_id_reused_from_inbound_header():
    client = TestClient(ex.create_app())
    r = client.get("/items/1", headers={"X-Request-ID": "trace-9"})
    assert r.headers["X-Request-ID"] == "trace-9"


def test_not_found_handler_returns_json_404():
    client = TestClient(ex.create_app())
    r = client.get("/items/999")
    assert r.status_code == 404
    assert r.json() == {"error": "not_found", "detail": "item 999 not found"}


def test_cors_preflight_allows_listed_origin_only():
    client = TestClient(ex.create_app([ORIGIN]))
    pre = {"Origin": ORIGIN, "Access-Control-Request-Method": "POST"}
    ok = client.options("/items/1", headers=pre)
    assert ok.status_code == 200
    assert ok.headers["access-control-allow-origin"] == ORIGIN
    assert "POST" in ok.headers["access-control-allow-methods"]

    bad = client.options("/items/1", headers={**pre, "Origin": "https://evil.test"})
    assert "access-control-allow-origin" not in bad.headers


def test_cors_header_on_simple_request():
    client = TestClient(ex.create_app([ORIGIN]))
    r = client.get("/items/1", headers={"Origin": ORIGIN})
    assert r.headers["access-control-allow-origin"] == ORIGIN
    assert "access-control-allow-credentials" not in r.headers


def test_lifespan_sets_ready_flag():
    app = ex.create_app()
    with TestClient(app) as client:
        assert client.get("/state").json() == {"ready": True}
    assert app.state.ready is False
