import json
import logging

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("opentelemetry.sdk")
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from _loader import load

ex = load("t04_fastapi_backend", "ex_17_observability_opentelemetry")


def format_record(msg: str, *args: object, level: int = logging.INFO) -> dict:
    record = logging.LogRecord("ex17", level, __file__, 1, msg, args, None)
    return json.loads(ex.JsonFormatter().format(record))  # call format() directly


def test_json_formatter_includes_request_id():
    token = ex.request_id_var.set("req-1")
    try:
        data = format_record("disk %s%% full", 91, level=logging.WARNING)
    finally:
        ex.request_id_var.reset(token)
    assert data == {
        "level": "WARNING",
        "logger": "ex17",
        "message": "disk 91% full",
        "request_id": "req-1",
    }


def test_json_formatter_default_request_id():
    assert format_record("hello")["request_id"] == "-"


def test_request_id_middleware_reuses_and_generates():
    client = TestClient(ex.create_app())
    r = client.get("/whoami", headers={"X-Request-ID": "abc"})
    assert r.json() == {"request_id": "abc"} and r.headers["X-Request-ID"] == "abc"

    r = client.get("/whoami")
    generated = r.headers["X-Request-ID"]
    assert len(generated) == 8 and r.json() == {"request_id": generated}
    assert ex.request_id_var.get() == "-"  # context restored after the request


def test_readiness_all_ok_and_empty():
    assert ex.readiness({}) == (200, {"status": "ready", "checks": {}})
    status, body = ex.readiness({"db": lambda: True, "cache": lambda: True})
    assert status == 200 and body["checks"] == {"db": True, "cache": True}


def test_readiness_failure_and_exception():
    def boom() -> bool:
        raise ConnectionError("redis down")

    status, body = ex.readiness({"db": lambda: True, "cache": boom})
    assert status == 503
    assert body == {"status": "not_ready", "checks": {"db": True, "cache": False}}


def test_readyz_endpoint_returns_503():
    client = TestClient(ex.create_app({"db": lambda: False}))
    r = client.get("/readyz")
    assert r.status_code == 503 and r.json()["status"] == "not_ready"
    assert client.get("/healthz").status_code == 200  # liveness ignores dependencies


def test_make_provider_and_record_span():
    exporter = InMemorySpanExporter()
    provider = ex.make_provider(exporter)
    ex.record_span(provider, "charge_card", {"order.id": 7, "amount": 12.5})
    (span,) = exporter.get_finished_spans()
    assert span.name == "charge_card"
    assert dict(span.attributes) == {"order.id": 7, "amount": 12.5}
