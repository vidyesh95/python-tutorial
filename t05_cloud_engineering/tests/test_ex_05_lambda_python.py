import io
import json
import zipfile
from types import SimpleNamespace

from _loader import load

ex = load("t05_cloud_engineering", "ex_05_lambda_python")

CTX = SimpleNamespace(get_remaining_time_in_millis=lambda: 1000)


def body(resp: dict) -> dict:
    return json.loads(resp["body"])


def test_api_handler_hello_with_and_without_name():
    event = {"rawPath": "/hello", "queryStringParameters": {"name": "Ada"}}
    resp = ex.api_handler(event, CTX)
    assert resp["statusCode"] == 200
    assert resp["headers"]["content-type"] == "application/json"
    assert body(resp) == {"message": "hello Ada"}
    assert body(ex.api_handler({"rawPath": "/hello"}, CTX)) == {"message": "hello world"}
    none_qs = {"rawPath": "/hello", "queryStringParameters": None}
    assert body(ex.api_handler(none_qs, CTX)) == {"message": "hello world"}


def test_api_handler_health_and_404():
    resp = ex.api_handler({"rawPath": "/health"}, CTX)
    assert resp["statusCode"] == 200 and body(resp) == {"status": "ok"}
    resp = ex.api_handler({"rawPath": "/missing"}, CTX)
    assert resp["statusCode"] == 404 and body(resp) == {"error": "not found"}


def test_sqs_handler_reports_only_bad_records():
    event = {
        "Records": [
            {"messageId": "a", "body": '{"id": 1}'},
            {"messageId": "b", "body": "not json"},
            {"messageId": "c", "body": '{"other": 1}'},
            {"messageId": "d", "body": "[1, 2]"},
            {"messageId": "e", "body": '{"id": 2}'},
        ]
    }
    result = ex.sqs_handler(event, CTX)
    assert result == {
        "batchItemFailures": [
            {"itemIdentifier": "b"},
            {"itemIdentifier": "c"},
            {"itemIdentifier": "d"},
        ]
    }


def test_sqs_handler_all_good():
    event = {"Records": [{"messageId": "a", "body": '{"id": 1}'}]}
    assert ex.sqs_handler(event, CTX) == {"batchItemFailures": []}


def test_parse_s3_event_decodes_keys():
    event = {
        "Records": [
            {"s3": {"bucket": {"name": "up"}, "object": {"key": "my+file%281%29.txt"}}},
            {"s3": {"bucket": {"name": "up2"}, "object": {"key": "a/b.csv"}}},
        ]
    }
    assert ex.parse_s3_event(event) == [("up", "my file(1).txt"), ("up2", "a/b.csv")]


def test_build_zip_roundtrip():
    blob = ex.build_zip({"app.py": "print('hi')", "data/x.bin": b"\x00\x01"})
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        assert sorted(zf.namelist()) == ["app.py", "data/x.bin"]
        assert zf.read("app.py") == b"print('hi')"
        assert zf.read("data/x.bin") == b"\x00\x01"
        assert all(i.compress_type == zipfile.ZIP_DEFLATED for i in zf.infolist())


def test_has_time_left():
    assert ex.has_time_left(CTX) is True  # 1000 > 500
    assert ex.has_time_left(CTX, 1000) is False  # strictly greater
    assert ex.has_time_left(SimpleNamespace(get_remaining_time_in_millis=lambda: 100)) is False
