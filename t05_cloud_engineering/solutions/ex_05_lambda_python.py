"""Exercise 05: Lambda handlers, event parsing and packaging (no AWS calls needed).

Tasks
1. api_handler: API Gateway HTTP API (payload v2) handler.
2. sqs_handler: SQS batch handler with partial batch failures.
3. parse_s3_event: (bucket, key) pairs from an S3 notification.
4. build_zip: build a deployment zip in memory.
5. has_time_left: deadline awareness using the context.

Run: uv run pytest t05_cloud_engineering -k lambda_python
"""

import io
import json
import zipfile
from typing import Any
from urllib.parse import unquote_plus


def _response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload),
    }


def api_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route on event["rawPath"].

    - "/hello": 200, body JSON {"message": f"hello {name}"} where name comes from
      event["queryStringParameters"] (may be missing or None) and defaults to "world".
    - "/health": 200, body {"status": "ok"}
    - anything else: 404, body {"error": "not found"}

    Always return {"statusCode": int, "headers": {"content-type": "application/json"},
    "body": <JSON string>}.
    """
    path = event.get("rawPath", "/")
    if path == "/hello":
        name = (event.get("queryStringParameters") or {}).get("name", "world")
        return _response(200, {"message": f"hello {name}"})
    if path == "/health":
        return _response(200, {"status": "ok"})
    return _response(404, {"error": "not found"})


def sqs_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Process event["Records"]. A record is valid if its "body" is a JSON object with an "id" key.

    Return {"batchItemFailures": [{"itemIdentifier": messageId}, ...]} listing ONLY the
    invalid records (empty list when all are valid). Never raise for a bad record.
    """
    failures = []
    for record in event["Records"]:
        try:
            body = json.loads(record["body"])
            valid = isinstance(body, dict) and "id" in body
        except json.JSONDecodeError:
            valid = False
        if not valid:
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}


def parse_s3_event(event: dict[str, Any]) -> list[tuple[str, str]]:
    """Return [(bucket_name, object_key), ...] for each record.

    Keys in S3 events are URL-encoded ('+' means space): decode them.
    """
    return [
        (r["s3"]["bucket"]["name"], unquote_plus(r["s3"]["object"]["key"]))
        for r in event["Records"]
    ]


def build_zip(files: dict[str, str | bytes]) -> bytes:
    """Return the bytes of a ZIP_DEFLATED archive containing `files` (name -> content)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def has_time_left(context: Any, needed_ms: int = 500) -> bool:
    """True if context.get_remaining_time_in_millis() is strictly greater than needed_ms."""
    return context.get_remaining_time_in_millis() > needed_ms
