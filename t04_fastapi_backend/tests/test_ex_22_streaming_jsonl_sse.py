import json

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from _loader import load

ex = load("t04_fastapi_backend", "ex_22_streaming_jsonl_sse")


def frames(body: str) -> list[dict[str, str]]:
    """Independent mini SSE reader so endpoint tests do not depend on ex.parse_sse."""
    result = []
    for block in body.strip("\n").split("\n\n"):
        frame = {}
        for line in block.split("\n"):
            key, _, value = line.partition(": ")
            frame[key or "comment"] = value
        result.append(frame)
    return result


@pytest.fixture
def client():
    with TestClient(ex.create_app()) as c:
        yield c


def test_stream_items_is_jsonl(client):
    with client.stream("GET", "/items/stream") as response:
        assert response.headers["content-type"].startswith("application/jsonl")
        lines = list(response.iter_lines())
    # one JSON object per line, not one JSON array
    assert [json.loads(line) for line in lines] == [i.model_dump() for i in ex.ITEMS]


def test_stream_items_limit(client):
    lines = client.get("/items/stream", params={"limit": 2}).text.splitlines()
    assert [json.loads(line)["name"] for line in lines] == ["Plumbus", "Portal Gun"]


def test_stream_job_event_order_and_ids(client):
    with client.stream("GET", "/jobs/events", params={"total": 3}) as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache"
        parsed = frames(response.read().decode())
    assert [f["event"] for f in parsed] == ["progress", "progress", "progress", "done"]
    assert [f.get("id") for f in parsed] == ["1", "2", "3", None]
    assert json.loads(parsed[1]["data"]) == {"step": 2, "total": 3}
    assert parsed[-1]["data"] == "[DONE]"  # raw_data: not JSON-encoded (no quotes)


def test_stream_job_resumes_after_last_event_id(client):
    response = client.get("/jobs/events", params={"total": 4}, headers={"Last-Event-ID": "2"})
    parsed = frames(response.text)
    assert [f.get("id") for f in parsed] == ["3", "4", None]
    assert parsed[-1]["event"] == "done"


def test_stream_job_fully_caught_up_only_sends_done(client):
    response = client.get("/jobs/events", headers={"Last-Event-ID": "3"})
    assert [f["event"] for f in frames(response.text)] == ["done"]


def test_stream_chat_tokens_over_post(client):
    response = client.post("/chat/stream", json={"text": "hello streaming world"})
    assert response.headers["content-type"].startswith("text/event-stream")
    parsed = frames(response.text)
    assert [f["event"] for f in parsed] == ["token", "token", "token", "done"]
    # `data` is JSON-encoded, so the word arrives quoted
    assert [json.loads(f["data"]) for f in parsed[:3]] == ["hello", "streaming", "world"]
    assert parsed[-1]["data"] == "[DONE]"


def test_parse_sse_fields():
    body = 'event: a\ndata: {"x": 1}\nid: 5\nretry: 3000\n\n: ping\n\ndata: "hi"\n\n'
    assert ex.parse_sse(body) == [
        {"event": "a", "data": '{"x": 1}', "id": "5", "retry": "3000"},
        {"comment": "ping"},
        {"data": '"hi"'},
    ]


def test_parse_sse_multiline_data_and_empty_body():
    assert ex.parse_sse("data: one\ndata: two\n\n") == [{"data": "one\ntwo"}]
    assert ex.parse_sse("") == []


def test_parse_sse_roundtrips_real_stream(client):
    response = client.get("/jobs/events", params={"total": 2})
    assert ex.parse_sse(response.text) == frames(response.text)
