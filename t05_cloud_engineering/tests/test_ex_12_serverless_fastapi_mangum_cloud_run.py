import base64
import json
from types import SimpleNamespace

import pytest

pytest.importorskip("mangum")
from fastapi import FastAPI  # noqa: E402
from mangum import Mangum  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from _loader import load  # noqa: E402

ex = load("t05_cloud_engineering", "ex_12_serverless_fastapi_mangum_cloud_run")

CTX = SimpleNamespace(aws_request_id="test", function_name="api")


class Item(BaseModel):
    name: str


@pytest.fixture
def handler():
    app = FastAPI()

    @app.get("/hello")
    def hello(name: str = "world") -> dict[str, str]:
        return {"message": f"hello {name}"}

    @app.post("/items")
    def create(item: Item) -> dict[str, str]:
        return {"created": item.name}

    return Mangum(app, lifespan="off")


def test_event_shape():
    event = ex.make_apigw_v2_event("get", "/hello", {"name": "Ada Lovelace"}, headers={"X-Id": "1"})
    assert event["version"] == "2.0" and event["routeKey"] == "$default"
    assert event["rawPath"] == "/hello"
    assert event["rawQueryString"] == "name=Ada+Lovelace"
    assert event["queryStringParameters"] == {"name": "Ada Lovelace"}
    assert event["headers"] == {"x-id": "1"}
    assert event["requestContext"]["http"]["method"] == "GET"
    assert event["isBase64Encoded"] is False
    assert "body" not in event


def test_event_without_query_omits_parameters():
    event = ex.make_apigw_v2_event("GET", "/x")
    assert event["rawQueryString"] == ""
    assert "queryStringParameters" not in event


def test_dict_body_is_json_with_content_type():
    event = ex.make_apigw_v2_event("POST", "/items", body={"name": "a"})
    assert json.loads(event["body"]) == {"name": "a"}
    assert event["headers"]["content-type"] == "application/json"
    custom = ex.make_apigw_v2_event(
        "POST", "/items", body={"a": 1}, headers={"Content-Type": "application/vnd.x+json"}
    )
    assert custom["headers"]["content-type"] == "application/vnd.x+json"


def test_event_invokes_fastapi_through_mangum(handler):
    event = ex.make_apigw_v2_event("GET", "/hello", {"name": "Ada"})
    status, body = ex.parse_apigw_response(handler(event, CTX))
    assert (status, body) == (200, {"message": "hello Ada"})
    status, body = ex.parse_apigw_response(handler(ex.make_apigw_v2_event("GET", "/hello"), CTX))
    assert body == {"message": "hello world"}


def test_post_body_roundtrip_and_404(handler):
    event = ex.make_apigw_v2_event("POST", "/items", body={"name": "book"})
    assert ex.parse_apigw_response(handler(event, CTX)) == (200, {"created": "book"})
    status, _ = ex.parse_apigw_response(handler(ex.make_apigw_v2_event("GET", "/nope"), CTX))
    assert status == 404


def test_parse_apigw_response_variants():
    assert ex.parse_apigw_response({"statusCode": 200, "body": '{"a": 1}'}) == (200, {"a": 1})
    assert ex.parse_apigw_response({"statusCode": 200, "body": "plain"}) == (200, "plain")
    assert ex.parse_apigw_response({"statusCode": 204}) == (204, "")
    encoded = base64.b64encode(b'{"ok": true}').decode()
    resp = {"statusCode": 200, "body": encoded, "isBase64Encoded": True}
    assert ex.parse_apigw_response(resp) == (200, {"ok": True})


def test_cloud_run_port():
    assert ex.cloud_run_port({}) == 8080
    assert ex.cloud_run_port({"PORT": "9090"}) == 9090
    for bad in ("abc", "0", "70000", ""):
        with pytest.raises(ValueError):
            ex.cloud_run_port({"PORT": bad})


def test_uvicorn_args():
    assert ex.uvicorn_args("app:app", {"PORT": "8123"}) == [
        "uvicorn",
        "app:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8123",
    ]
    assert ex.uvicorn_args("m:a", {})[-1] == "8080"


def test_cold_start_tracker():
    tracker = ex.ColdStartTracker()
    assert [tracker.check() for _ in range(3)] == [True, False, False]
    assert ex.ColdStartTracker().check() is True  # a fresh environment is cold again
