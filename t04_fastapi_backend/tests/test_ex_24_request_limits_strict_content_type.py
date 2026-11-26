import pytest

pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from _loader import load

ex = load("t04_fastapi_backend", "ex_24_request_limits_strict_content_type")

NO_CT = {"content-type": ""}  # httpx: send no Content-Type header at all
RAW = b'{"name": "pen"}'


def test_json_within_limit_succeeds():
    client = TestClient(ex.create_app(max_json_bytes=200))
    r = client.post("/items", json={"name": "pen"})
    assert r.status_code == 200
    assert r.json() == {"name": "pen"}


def test_json_over_limit_returns_413():
    client = TestClient(ex.create_app(max_json_bytes=200))
    assert client.post("/items", json={"name": "x" * 500}).status_code == 413


def test_limit_counts_bytes_read_even_when_chunked():
    client = TestClient(ex.create_app(max_json_bytes=200))
    chunks = iter([b'{"name": "', b"x" * 500, b'"}'])  # no Content-Length
    r = client.post("/items", content=chunks, headers={"content-type": "application/json"})
    assert r.status_code == 413


def test_uploads_router_limit_overrides_smaller_app_limit():
    client = TestClient(ex.create_app(max_json_bytes=200, max_upload_bytes=5000))
    ok = client.post("/uploads/", files={"file": ("a.bin", b"x" * 2000)})
    assert ok.status_code == 200
    assert ok.json() == {"filename": "a.bin", "size": 2000}
    assert client.post("/uploads/", files={"file": ("a.bin", b"x" * 6000)}).status_code == 413
    # the small app-wide limit still guards the JSON route
    assert client.post("/items", json={"name": "x" * 500}).status_code == 413


def test_uploads_router_standalone():
    app = FastAPI()
    app.include_router(ex.build_uploads_router(1000))
    client = TestClient(app)
    assert client.post("/uploads/", files={"file": ("n.txt", b"x" * 300)}).status_code == 200
    assert client.post("/uploads/", files={"file": ("n.txt", b"x" * 3000)}).status_code == 413


def test_form_within_limits_succeeds():
    client = TestClient(ex.create_app(max_fields=2, max_part_size=20))
    r = client.post("/notes", data={"title": "hi", "body": "yo"})
    assert r.status_code == 200
    assert r.json() == {"title": "hi", "body": "yo"}


def test_too_many_form_fields_returns_400():
    client = TestClient(ex.create_app(max_fields=2, max_part_size=20))
    r = client.post("/notes", data={"title": "hi", "body": "yo", "extra": "z"})
    assert r.status_code == 400


def test_oversized_form_field_returns_400():
    app = FastAPI()
    app.include_router(ex.build_notes_router(max_fields=5, max_part_size=10))
    client = TestClient(app)
    assert client.post("/notes", data={"title": "ok"}).status_code == 200
    assert client.post("/notes", data={"title": "t" * 50}).status_code == 400


def test_strict_rejects_missing_and_text_plain_content_type():
    client = TestClient(ex.create_app(strict=True))
    ok = client.post("/items", content=RAW, headers={"content-type": "application/json"})
    assert ok.status_code == 200
    assert (
        client.post(
            "/items", content=RAW, headers={"content-type": "application/vnd.api+json"}
        ).status_code
        == 200
    )
    assert client.post("/items", content=RAW, headers=NO_CT).status_code == 422
    assert (
        client.post("/items", content=RAW, headers={"content-type": "text/plain"}).status_code
        == 422
    )


def test_non_strict_app_accepts_missing_content_type_only():
    client = TestClient(ex.create_app(strict=False))
    r = client.post("/items", content=RAW, headers=NO_CT)
    assert r.status_code == 200
    assert r.json() == {"name": "pen"}
    assert (
        client.post("/items", content=RAW, headers={"content-type": "text/plain"}).status_code
        == 422
    )


def test_legacy_router_accepts_missing_content_type_even_when_app_is_strict():
    client = TestClient(ex.create_app(strict=True))
    assert client.post("/legacy/items", content=RAW, headers=NO_CT).status_code == 200
    assert (
        client.post(
            "/legacy/items", content=RAW, headers={"content-type": "text/plain"}
        ).status_code
        == 422
    )
    assert client.post("/items", content=RAW, headers=NO_CT).status_code == 422
