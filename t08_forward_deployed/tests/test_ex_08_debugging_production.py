import io
import json
import logging
import math
import sys
import uuid

import pytest

from _loader import load

ex = load("t08_forward_deployed", "ex_08_debugging_production")


def render(msg, *args, extra=None, exc_info=None):
    """Format one LogRecord directly (logging itself swallows formatter errors)."""
    logger = logging.getLogger(f"test.{uuid.uuid4().hex}")
    record = logger.makeRecord(
        logger.name, logging.INFO, __file__, 1, msg, args, exc_info, extra=extra
    )
    return ex.JsonFormatter().format(record), logger


def test_json_formatter_basic_fields_and_correlation():
    token = ex.correlation_id.set("req-1")
    try:
        raw, logger = render("hello %s", "world", extra={"customer": 7})
    finally:
        ex.correlation_id.reset(token)
    first = json.loads(raw)
    assert first["level"] == "INFO" and first["message"] == "hello world"
    assert first["correlation_id"] == "req-1" and first["customer"] == 7
    assert first["logger"] == logger.name
    assert json.loads(render("no id")[0])["correlation_id"] is None


def test_json_formatter_redacts_sensitive_extras():
    raw, _ = render(
        "call",
        extra={
            "api_key": "sk_live_x",
            "Authorization": "Bearer abc",
            "user_password": "p",
            "ok": 1,
        },
    )
    entry = json.loads(raw)
    assert "sk_live_x" not in raw and "Bearer abc" not in raw
    assert entry["api_key"] == entry["Authorization"] == entry["user_password"] == "[REDACTED]"
    assert entry["ok"] == 1


def test_json_formatter_exception_and_unserializable():
    try:
        _ = 1 / 0
    except ZeroDivisionError:
        raw, _logger = render("boom", extra={"obj": object()}, exc_info=sys.exc_info())
    entry = json.loads(raw)
    assert "ZeroDivisionError" in entry["exc"] and "\n" not in raw
    assert isinstance(entry["obj"], str)


def test_json_formatter_works_through_a_real_handler():
    render("sanity")  # surface formatter errors that a real handler would swallow
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(ex.JsonFormatter())
    logger = logging.getLogger(f"test.{uuid.uuid4().hex}")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.warning("via handler", extra={"customer": 1})
    assert json.loads(stream.getvalue())["message"] == "via handler"


def test_group_by_correlation():
    lines = [
        json.dumps({"correlation_id": "a", "message": "1"}),
        "garbage",
        json.dumps({"correlation_id": "b", "message": "2"}),
        json.dumps({"message": "orphan"}),
        json.dumps({"correlation_id": "a", "message": "3"}),
        json.dumps([1, 2]),
        "",
        json.dumps({"correlation_id": None, "message": "null id"}),
    ]
    groups = ex.group_by_correlation(lines)
    assert list(groups) == ["a", "b", "-"]
    assert [e["message"] for e in groups["a"]] == ["1", "3"]
    assert [e["message"] for e in groups["-"]] == ["orphan", "null id"]


SIMPLE_TB = """Traceback (most recent call last):
  File "/srv/app/main.py", line 10, in handler
    run(x)
  File "/srv/app/sync.py", line 42, in run
    fetch(x)
  File "/usr/lib/python3.15/site-packages/httpx/_client.py", line 900, in get
    raise ConnectError()
httpx.ConnectError: boom
"""

CHAINED_TB = """Traceback (most recent call last):
  File "/srv/app/db.py", line 5, in query
    cursor.execute(sql)
sqlite3.OperationalError: locked

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/srv/app/main.py", line 10, in handler
    save(x)
  File "/usr/lib/python3.15/site-packages/lib.py", line 3, in save
    raise RuntimeError("save failed") from exc
RuntimeError: save failed
"""


def test_last_app_frame_picks_deepest_app_frame():
    assert ex.last_app_frame(SIMPLE_TB, "/srv/app/") == ("/srv/app/sync.py", 42, "run")


def test_last_app_frame_uses_final_block_of_chained_traceback():
    assert ex.last_app_frame(CHAINED_TB, "/srv/app/") == ("/srv/app/main.py", 10, "handler")


def test_last_app_frame_none_when_missing():
    assert ex.last_app_frame(SIMPLE_TB, "/other/") is None
    assert ex.last_app_frame("", "/srv/app/") is None


@pytest.mark.parametrize("n", [1, 2, 7, 32, 100])
def test_first_bad_finds_boundary_with_few_calls(n):
    for culprit in {0, n // 2, n - 1}:
        calls = []

        def is_bad(i, culprit=culprit, calls=calls):
            calls.append(i)
            return i >= culprit

        assert ex.first_bad(list(range(n)), is_bad) == culprit
        assert len(calls) <= math.ceil(math.log2(n)) + 1


def test_first_bad_none_and_empty():
    assert ex.first_bad([1, 2, 3], lambda x: False) is None
    assert ex.first_bad([], lambda x: True) is None


def test_rollout_enabled_edges_and_stability():
    assert not any(ex.rollout_enabled("f", f"u{i}", 0) for i in range(200))
    assert all(ex.rollout_enabled("f", f"u{i}", 100) for i in range(200))
    assert ex.rollout_enabled("f", "alice", 37) == ex.rollout_enabled("f", "alice", 37)


def test_rollout_enabled_is_proportional_and_monotonic():
    users = [f"user{i}" for i in range(2000)]
    on25 = {u for u in users if ex.rollout_enabled("new-sync", u, 25)}
    on50 = {u for u in users if ex.rollout_enabled("new-sync", u, 50)}
    assert 400 <= len(on25) <= 600  # ~25% of 2000
    assert on25 <= on50  # raising the percentage never removes a user
    other = {u for u in users if ex.rollout_enabled("other-flag", u, 25)}
    assert other != on25  # buckets differ per flag
