"""Exercise 12: the glue between FastAPI, Lambda (API Gateway HTTP API v2) and Cloud Run.

Tests wrap a small FastAPI app with `Mangum(app, lifespan="off")` and call it with the events
you build.

Tasks
1. make_apigw_v2_event: build a payload-v2 event Mangum accepts.
2. parse_apigw_response: decode a Lambda proxy response.
3. cloud_run_port: read $PORT with validation.
4. uvicorn_args: the container command for Cloud Run.
5. ColdStartTracker: tell cold starts from warm invocations.

Run: uv run pytest t05_cloud_engineering -k mangum
"""

import base64
import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode


def make_apigw_v2_event(
    method: str,
    path: str,
    query: dict[str, str] | None = None,
    body: str | dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return an API Gateway HTTP API (payload format 2.0) event with:

    - "version": "2.0", "routeKey": "$default", "rawPath": path
    - "rawQueryString": urlencode(query or {}); "queryStringParameters": query (only if query)
    - "headers": the given headers with lower-cased names
    - "body": the string body; a dict body is JSON-encoded and gets a "content-type":
      "application/json" header unless one is already set. Omit "body" when body is None.
    - "isBase64Encoded": False
    - "requestContext": {"http": {"method": method.upper(), "path": path, "protocol":
      "HTTP/1.1", "sourceIp": "127.0.0.1", "userAgent": "local-test"}, "stage": "$default",
      "requestId": "req-1", "accountId": "123456789012", "apiId": "api-id",
      "domainName": "api-id.execute-api.us-east-1.amazonaws.com", "domainPrefix": "api-id",
      "routeKey": "$default", "time": "01/Jan/2026:00:00:00 +0000", "timeEpoch": 1767225600000}
    """
    hdrs = {k.lower(): v for k, v in (headers or {}).items()}
    if isinstance(body, dict):
        body = json.dumps(body)
        hdrs.setdefault("content-type", "application/json")
    event: dict[str, Any] = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": path,
        "rawQueryString": urlencode(query or {}),
        "headers": hdrs,
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "api-id",
            "domainName": "api-id.execute-api.us-east-1.amazonaws.com",
            "domainPrefix": "api-id",
            "http": {
                "method": method.upper(),
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "local-test",
            },
            "requestId": "req-1",
            "routeKey": "$default",
            "stage": "$default",
            "time": "01/Jan/2026:00:00:00 +0000",
            "timeEpoch": 1767225600000,
        },
        "isBase64Encoded": False,
    }
    if query:
        event["queryStringParameters"] = dict(query)
    if body is not None:
        event["body"] = body
    return event


def parse_apigw_response(resp: Mapping[str, Any]) -> tuple[int, Any]:
    """Return (statusCode, body).

    If resp["isBase64Encoded"] is true, base64-decode the body first. Then try json.loads;
    if the text is not JSON return it as a str. A missing/None body means "" (returned as "").
    """
    raw = resp.get("body") or ""
    if resp.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode()
    try:
        return resp["statusCode"], json.loads(raw)
    except json.JSONDecodeError:
        return resp["statusCode"], raw


def cloud_run_port(env: Mapping[str, str]) -> int:
    """Return int(env["PORT"]), defaulting to 8080 when PORT is absent.

    Raise ValueError if it is not an integer or not within 1..65535.
    """
    raw = env.get("PORT", "8080")
    try:
        port = int(raw)
    except ValueError:
        raise ValueError(f"PORT must be an integer, got {raw!r}") from None
    if not 1 <= port <= 65535:
        raise ValueError(f"PORT out of range: {port}")
    return port


def uvicorn_args(app_path: str, env: Mapping[str, str]) -> list[str]:
    """Return ["uvicorn", app_path, "--host", "0.0.0.0", "--port", "<port>"] using cloud_run_port."""
    return ["uvicorn", app_path, "--host", "0.0.0.0", "--port", str(cloud_run_port(env))]


class ColdStartTracker:
    """check() returns True on the very first call and False on every later call."""

    def __init__(self) -> None:
        self._seen = False

    def check(self) -> bool:
        first, self._seen = not self._seen, True
        return first
