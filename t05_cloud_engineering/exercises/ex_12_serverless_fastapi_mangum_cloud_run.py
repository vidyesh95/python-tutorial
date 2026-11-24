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

import base64  # noqa: F401  (handy for task 2)
import json  # noqa: F401  (handy for tasks 1 and 2)
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode  # noqa: F401  (handy for task 1)


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
    raise NotImplementedError


def parse_apigw_response(resp: Mapping[str, Any]) -> tuple[int, Any]:
    """Return (statusCode, body).

    If resp["isBase64Encoded"] is true, base64-decode the body first. Then try json.loads;
    if the text is not JSON return it as a str. A missing/None body means "" (returned as "").
    """
    raise NotImplementedError


def cloud_run_port(env: Mapping[str, str]) -> int:
    """Return int(env["PORT"]), defaulting to 8080 when PORT is absent.

    Raise ValueError if it is not an integer or not within 1..65535.
    """
    raise NotImplementedError


def uvicorn_args(app_path: str, env: Mapping[str, str]) -> list[str]:
    """Return ["uvicorn", app_path, "--host", "0.0.0.0", "--port", "<port>"] using cloud_run_port."""
    raise NotImplementedError


class ColdStartTracker:
    """check() returns True on the very first call and False on every later call."""

    def check(self) -> bool:
        raise NotImplementedError
