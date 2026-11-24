# AWS Lambda with Python
"""
Lambda runs a function in response to an event; AWS provisions, scales and bills per
invocation (and per GB-second of runtime). You ship code, not servers.

The handler
    def handler(event: dict, context) -> dict | None
- `event`: JSON-decoded payload; its SHAPE depends on the trigger (API Gateway, SQS, S3,
  EventBridge, a direct `invoke`...). Look up the sample event of your trigger.
- `context`: runtime info: `aws_request_id`, `function_name`, `memory_limit_in_mb`,
  `get_remaining_time_in_millis()`.
- The return value goes back to the caller (HTTP response for API Gateway; ignored for
  async triggers). Raise to signal failure (the platform retries async/stream sources).
- Configure the entry point as `module.function`, e.g. `app.handler`.

Lifecycle and cold starts
- COLD START: a new execution environment downloads the code, starts the runtime and runs
  your module-level code (INIT). Later invocations reuse the warm environment and only run
  the handler. Cold starts add ~100 ms to seconds depending on package size and imports.
- Do expensive setup at MODULE level (boto3 clients, config, DB pools) so warm calls reuse
  it; keep it lazy if some paths do not need it. Never keep per-request data in globals.
- Reduce cold starts: small packages, fewer imports, more memory (more CPU too), ARM
  (Graviton), SnapStart/provisioned concurrency for latency-critical paths.

Event examples shown below: API Gateway HTTP API v2, SQS batch (partial batch failures via
`batchItemFailures`), S3 notification (keys are URL-encoded!).

Packaging
- ZIP (<= 50 MB zipped / 250 MB unzipped): your code (+ dependencies built for Linux).
- LAYER: shared dependencies in a separate zip attached to many functions.
- CONTAINER IMAGE (<= 10 GB): build like m_09, push to ECR; best for big deps (numpy, ML).
- The `boto3` SDK is already in the Python runtime; pin your own only if you need a version.

Testing: a handler is just a function. Call it locally with a sample event and a fake
context (below). moto can create Lambda functions, but INVOKING them needs Docker, so this
lesson invokes handlers directly. Use `sam local invoke` / LocalStack for full emulation.

Common mistakes
- Creating the boto3 client INSIDE the handler (slow on every call) or reading secrets on
  every invocation (cache them, see m_13).
- Handler timeout (default 3 s) shorter than the work; or no timeout guard on slow calls.
- Treating all SQS records as failed because one failed: report `batchItemFailures`.
- Forgetting S3 event keys are URL-encoded (`my+file%281%29.txt`).
- Non-idempotent handlers: async events and SQS are retried (m_04).
- Writing outside `/tmp` (read-only filesystem; `/tmp` is 512 MB by default).

Production notes
- One role per function with least privilege (m_01); set a realistic timeout and memory.
- Structured JSON logs with the request id (m_14); alarm on Errors, Throttles, Duration.
- Set reserved concurrency to protect downstream databases from a burst.
- Put a DLQ / on-failure destination on async functions.

Cost notes
- Billed per request (~ $0.20 / 1M) plus GB-seconds; 1M requests + 400,000 GB-s are free
  each month. More memory = more CPU: the cheapest setting is often NOT the smallest.
- Provisioned concurrency bills even when idle. Idle Lambdas are free: great for spiky load,
  expensive for sustained 24/7 high throughput (compare with Fargate, m_12).
"""

import io
import json
import time
import zipfile
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote_plus

# --- INIT phase: runs once per cold start ---
_INIT_STARTED = time.perf_counter()
_COLD_START = True  # flipped to False after the first invocation in this environment
INIT_SECONDS = time.perf_counter() - _INIT_STARTED


@dataclass
class FakeContext:
    """Stand-in for the Lambda context object, enough for local calls and tests."""

    function_name: str = "demo-function"
    aws_request_id: str = "00000000-0000-0000-0000-000000000000"
    memory_limit_in_mb: int = 128
    remaining_ms: int = 3000

    def get_remaining_time_in_millis(self) -> int:
        return self.remaining_ms


# Example 1: API Gateway HTTP API (payload v2) handler
def api_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    global _COLD_START
    cold, _COLD_START = _COLD_START, False
    path = event.get("rawPath", "/")
    if path == "/hello":
        name = (event.get("queryStringParameters") or {}).get("name", "world")
        status, payload = 200, {"message": f"hello {name}", "cold_start": cold}
    else:
        status, payload = 404, {"error": "not found"}
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload),
    }


# Example 2: SQS batch handler with partial batch failure reporting
def sqs_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    failures = []
    for record in event["Records"]:
        try:
            job = json.loads(record["body"])
            print("processing job", job["id"])
        except json.JSONDecodeError, KeyError:
            failures.append({"itemIdentifier": record["messageId"]})  # only THIS one retries
    return {"batchItemFailures": failures}


# Example 3: S3 notification: keys arrive URL-encoded
def parse_s3_event(event: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (r["s3"]["bucket"]["name"], unquote_plus(r["s3"]["object"]["key"]))
        for r in event["Records"]
    ]


# Example 4: packaging: a deployment zip built in memory
def build_zip(files: dict[str, str | bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


# Example 5: deadline awareness
def has_time_left(context: Any, needed_ms: int = 500) -> bool:
    return context.get_remaining_time_in_millis() > needed_ms


SAMPLE_API_EVENT = {
    "version": "2.0",
    "routeKey": "GET /hello",
    "rawPath": "/hello",
    "rawQueryString": "name=Ada",
    "queryStringParameters": {"name": "Ada"},
    "requestContext": {"http": {"method": "GET", "path": "/hello"}},
    "isBase64Encoded": False,
}


if __name__ == "__main__":
    ctx = FakeContext()
    print("init took < 1s:", INIT_SECONDS < 1)
    first = api_handler(SAMPLE_API_EVENT, ctx)
    second = api_handler(SAMPLE_API_EVENT, ctx)
    print("1st call:", first["body"])
    print("2nd call:", second["body"])
    print("404:", api_handler({"rawPath": "/nope"}, ctx)["statusCode"])

    sqs_event = {
        "Records": [
            {"messageId": "m1", "body": '{"id": 1}'},
            {"messageId": "m2", "body": "not json"},
        ]
    }
    print("sqs:", sqs_handler(sqs_event, ctx))

    s3_event = {
        "Records": [
            {"s3": {"bucket": {"name": "uploads"}, "object": {"key": "my+file%281%29.txt"}}}
        ]
    }
    print("s3:", parse_s3_event(s3_event))

    blob = build_zip({"app.py": "def handler(event, context):\n    return 'ok'\n"})
    print(
        "zip bytes > 0:", len(blob) > 0, "| members:", zipfile.ZipFile(io.BytesIO(blob)).namelist()
    )
    print("time left:", has_time_left(ctx), has_time_left(FakeContext(remaining_ms=100)))
