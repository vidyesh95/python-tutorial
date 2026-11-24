import httpx
import pytest

pytest.importorskip("fastapi")
from _loader import load

ex = load("t04_fastapi_backend", "ex_01_http_rest_basics")


@pytest.mark.parametrize(
    ("code", "name"),
    [
        (101, "informational"),
        (200, "success"),
        (204, "success"),
        (302, "redirect"),
        (404, "client_error"),
        (503, "server_error"),
    ],
)
def test_status_class(code, name):
    assert ex.status_class(code) == name


def test_status_class_invalid():
    with pytest.raises(ValueError):
        ex.status_class(99)
    with pytest.raises(ValueError):
        ex.status_class(600)


def test_method_properties():
    assert ex.method_properties("get") == {"safe": True, "idempotent": True}
    assert ex.method_properties("PUT") == {"safe": False, "idempotent": True}
    assert ex.method_properties("DELETE") == {"safe": False, "idempotent": True}
    assert ex.method_properties("POST") == {"safe": False, "idempotent": False}
    with pytest.raises(ValueError):
        ex.method_properties("FETCH")


def test_build_url():
    assert ex.build_url("books") == "/books"
    assert ex.build_url("books", 42) == "/books/42"
    assert ex.build_url("books", 42, limit=5) == "/books/42?limit=5"
    assert ex.build_url("books", q=None, page=2) == "/books?page=2"
    assert ex.build_url("books", q="a b") in {"/books?q=a+b", "/books?q=a%20b"}


def test_parse_bearer():
    assert ex.parse_bearer("Bearer abc.def") == "abc.def"
    assert ex.parse_bearer("bearer xyz") == "xyz"
    assert ex.parse_bearer("Basic abc") is None
    assert ex.parse_bearer("Bearer") is None
    assert ex.parse_bearer("Bearer   ") is None
    assert ex.parse_bearer(None) is None


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test")


def test_fetch_json_ok():
    with _client(lambda r: httpx.Response(200, json={"id": 1})) as c:
        assert ex.fetch_json(c, "/books/1") == {"id": 1}


def test_fetch_json_error_detail():
    with _client(lambda r: httpx.Response(404, json={"detail": "Book not found"})) as c:
        with pytest.raises(ex.ApiError) as info:
            ex.fetch_json(c, "/books/9")
    assert info.value.status_code == 404
    assert info.value.detail == "Book not found"


def test_fetch_json_error_plain_text():
    with _client(lambda r: httpx.Response(502, text="Bad Gateway")) as c:
        with pytest.raises(ex.ApiError) as info:
            ex.fetch_json(c, "/x")
    assert info.value.status_code == 502
    assert info.value.detail == "Bad Gateway"
