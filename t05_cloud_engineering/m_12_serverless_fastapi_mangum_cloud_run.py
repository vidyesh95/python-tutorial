# Serverless FastAPI: Mangum and Cloud Run
"""
The same FastAPI app (t04) can run "serverless" on two different contracts.

1) AWS Lambda + API Gateway + Mangum
- Lambda does not speak HTTP; API Gateway turns each HTTP request into a JSON EVENT and
  expects a JSON response. FastAPI speaks ASGI. MANGUM is the adapter between them:
      handler = Mangum(app, lifespan="off")      # `handler(event, context)` is the Lambda entry
- Mangum detects the event flavour (API Gateway REST v1, HTTP API v2, ALB, Function URL),
  builds an ASGI request, runs your app, and converts the response back. This lesson calls
  the handler directly with a hand-built API Gateway HTTP API (v2) event: no AWS needed.
- Lifespan: Lambda environments freeze between calls, so startup/shutdown hooks are awkward.
  `lifespan="off"` skips them (create clients at module level instead, m_05); "auto" runs
  startup per cold start.
- Deploy as a ZIP (needs Linux-built dependencies) or, simpler for FastAPI, a container image
  (Mangum or the AWS Lambda Web Adapter). Put a `$default` route on an HTTP API.

2) Google Cloud Run: the CONTAINER CONTRACT (no adapter, it is a normal web server)
- Your container must listen on `0.0.0.0:$PORT` (Cloud Run sets PORT, default 8080), start
  within the startup timeout, and handle SIGTERM (10 s grace) for graceful shutdown.
- Stateless: any instance can be killed; the filesystem is in-memory and ephemeral.
- Scales 0..N instances on request concurrency (default 80 per instance), billed only while
  handling requests (or always-on CPU if configured).
- Deploy: `gcloud run deploy api --source . --region us-central1 --no-allow-unauthenticated`.
  The service account attached to the revision is the app's identity (m_06).
- The t04 Dockerfile hard-codes port 8000; for Cloud Run use `--port "${PORT:-8080}"`.
  AWS has the same idea in App Runner and ECS Fargate (a container behind a load balancer).

Cold starts and trade-offs
- Lambda: cold start = new environment + imports + app creation (FastAPI + pydantic import
  is slow: often 0.5-2 s). Cloud Run: container start + app startup, similar.
- Mitigate: small images/packages, lazy imports, min instances / provisioned concurrency
  (costs money), more CPU, startup CPU boost.
- Choose: Lambda = spiky/low traffic, event-driven glue, scale-to-zero, 15 min max, 29 s API
  Gateway limit. Containers (Cloud Run/Fargate) = steady traffic, WebSockets/streaming, longer
  requests, any runtime, easier local parity.

Common mistakes
- Binding to 127.0.0.1 or a fixed port on Cloud Run (the instance never becomes ready).
- Expecting startup/shutdown hooks to behave as on a long-lived server under Lambda.
- Forgetting API Gateway stage prefixes (`/prod/...`): set `api_gateway_base_path`.
- Large request/response bodies: Lambda payloads are limited to 6 MB; return S3 presigned URLs.
- Storing state in memory or on local disk; instances are disposable.
- Leaving the service public by accident (`--allow-unauthenticated`, or a Function URL with
  auth type NONE).

Production notes
- Use structured logs to stdout (m_14); both platforms ship them to CloudWatch/Cloud Logging.
- Put secrets in Secrets Manager / Secret Manager (m_13), never in environment literals.
- Set timeouts, concurrency limits and max instances to protect your database connections;
  put RDS Proxy / pgbouncer in front of Postgres when scaling out.
- Health endpoints from t04: `/healthz` (liveness), `/readyz` (readiness).

Cost notes
- Lambda: per request + GB-seconds, with a generous free tier. Cloud Run: per vCPU-second
  and GiB-second while serving, with a free tier. Both cost ~$0 when idle (min instances 0).
- At sustained high traffic an always-on container is usually cheaper than per-request pricing.
- API Gateway HTTP API (~$1 per million requests) is far cheaper than the REST API flavour.
"""

import base64
import json
from collections.abc import Mapping
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI
from mangum import Mangum
from pydantic import BaseModel

app = FastAPI(title="Serverless demo")


class Echo(BaseModel):
    text: str


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/hello")
def hello(name: str = "world") -> dict[str, str]:
    return {"message": f"hello {name}"}


@app.post("/echo")
def echo(body: Echo) -> dict[str, str]:
    return {"echo": body.text.upper()}


# The Lambda entry point: configure the function handler as
# "t05_cloud_engineering.m_12_serverless_fastapi_mangum_cloud_run.handler".
handler = Mangum(app, lifespan="off")


# Example 1: build an API Gateway HTTP API (payload v2) event
def make_apigw_v2_event(
    method: str,
    path: str,
    query: dict[str, str] | None = None,
    body: str | dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
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


# Example 2: read the Lambda response the way API Gateway would
def parse_apigw_response(resp: Mapping[str, Any]) -> tuple[int, Any]:
    raw = resp.get("body") or ""
    if resp.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode()
    try:
        return resp["statusCode"], json.loads(raw)
    except json.JSONDecodeError:
        return resp["statusCode"], raw


# Example 3: Cloud Run container contract
def cloud_run_port(env: Mapping[str, str]) -> int:
    raw = env.get("PORT", "8080")
    try:
        port = int(raw)
    except ValueError:
        raise ValueError(f"PORT must be an integer, got {raw!r}") from None
    if not 1 <= port <= 65535:
        raise ValueError(f"PORT out of range: {port}")
    return port


def uvicorn_args(app_path: str, env: Mapping[str, str]) -> list[str]:
    """Exec-form command: 0.0.0.0 so the platform can reach it, port from $PORT."""
    return ["uvicorn", app_path, "--host", "0.0.0.0", "--port", str(cloud_run_port(env))]


# Example 4: cold start tracking (module state lives as long as the environment/instance)
class ColdStartTracker:
    def __init__(self) -> None:
        self._seen = False

    def check(self) -> bool:
        """True on the first call in this environment, False afterwards."""
        first, self._seen = not self._seen, True
        return first


if __name__ == "__main__":
    context = SimpleNamespace(aws_request_id="local", function_name="api")
    for method, path, query, body in [
        ("GET", "/healthz", None, None),
        ("GET", "/hello", {"name": "Ada"}, None),
        ("POST", "/echo", None, {"text": "serverless"}),
        ("GET", "/nope", None, None),
    ]:
        event = make_apigw_v2_event(method, path, query, body)
        status, payload = parse_apigw_response(handler(event, context))
        print(f"{method:<4} {path:<9} -> {status} {payload}")

    print("Cloud Run port (default):", cloud_run_port({}))
    print("Cloud Run command:", uvicorn_args("app:app", {"PORT": "9090"}))
    tracker = ColdStartTracker()
    print("cold start flags:", [tracker.check() for _ in range(3)])
