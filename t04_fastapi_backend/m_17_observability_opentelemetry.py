# Observability with OpenTelemetry
"""
Observability = being able to ask "what is my service doing and why is it slow/broken?"
from the outside. Three signals:

- LOGS    discrete events. Emit STRUCTURED (JSON) logs with a request id, so they can be
          searched and joined with traces. One JSON object per line, to stdout.
- TRACES  the path of one request: a tree of SPANS (name, start/end, attributes, status).
          A trace id propagates across services (W3C `traceparent` header).
- METRICS numbers over time: request count, latency histogram, error rate, queue depth.
          Cheap to store, good for dashboards and alerts. Watch the "RED" signals:
          Rate, Errors, Duration.

OpenTelemetry (OTel) is the vendor-neutral standard API/SDK for all three. Your code makes
spans/metrics; an EXPORTER ships them (OTLP to a collector -> Jaeger, Tempo, Grafana,
Datadog...). Here we use an in-memory exporter so the lesson runs offline; in production:
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://collector:4318/v1/traces"))
(`ConsoleSpanExporter()` prints spans to the terminal: handy while learning.)

`FastAPIInstrumentor.instrument_app(app, tracer_provider=...)` auto-creates a SERVER span per
request (named like "GET /items/{item_id}") with http.* attributes. You add child spans for
the interesting inner work with `tracer.start_as_current_span("name")`.

Health endpoints for orchestrators (Kubernetes, Docker, load balancers):
- `/healthz` LIVENESS: "the process is up". Cheap, no dependency checks. Failing => restart.
- `/readyz`  READINESS: "I can serve traffic" (DB/Redis reachable). Failing => stop routing
  to me, but do not restart.

Run live:  uv run fastapi dev t04_fastapi_backend/m_17_observability_opentelemetry.py

Common mistakes
- Plain-text logs with no request id: impossible to follow one request across lines.
- Logging secrets, tokens, passwords, or full request bodies (PII).
- Putting dependency checks in liveness: a DB blip restarts every pod at once.
- High-cardinality metric labels (user id, raw URL path): metrics storage explodes. Use the
  route template ("/items/{item_id}"), status class, and method.
- Sampling nothing, or 100% of a busy service (cost). Use head sampling (e.g. 5-10%) or
  tail sampling in the collector; always keep errors.
- Calling `trace.set_tracer_provider` more than once (it only works once per process).

Production notes
- Set `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`, and `OTEL_TRACES_SAMPLER` via env.
- Zero-code alternative: `opentelemetry-instrument uvicorn app:app` (auto-instrumentation).
- Put the trace id in your JSON logs so a log line links to its trace.
- Alert on symptoms users feel (latency SLO, error rate), not on every cause.
"""

import contextvars
import json
import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


# Example: structured JSON logging that includes the request id
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


logger = logging.getLogger("m_17")
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(JsonFormatter())
logger.addHandler(_handler)
logger.setLevel(logging.INFO)
logger.propagate = False  # avoid duplicate lines via the root logger

# Example: tracing and metrics providers backed by in-memory exporters
span_exporter = InMemorySpanExporter()
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
tracer = tracer_provider.get_tracer("m_17")

metric_reader = InMemoryMetricReader()
meter = MeterProvider(metric_readers=[metric_reader]).get_meter("m_17")
requests_counter = meter.create_counter("app.requests", unit="1", description="Handled requests")

app = FastAPI(title="Observability")
FastAPIInstrumentor.instrument_app(
    app, tracer_provider=tracer_provider
)  # one SERVER span per request


@app.middleware("http")
async def request_logging(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:8]
    token = request_id_var.set(rid)  # visible to every log line during this request
    start = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        route = getattr(request.scope.get("route"), "path", "unmatched")  # template, not raw URL
        requests_counter.add(1, {"route": route, "status": response.status_code})
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %s in %.1fms", request.method, route, response.status_code, elapsed_ms
        )
        return response
    finally:
        request_id_var.reset(token)


def check_database() -> bool:
    return True  # imagine `SELECT 1`


DEPENDENCIES: dict[str, Callable[[], bool]] = {"database": check_database}


@app.get("/healthz")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/readyz")
def readiness() -> JSONResponse:
    results = {}
    for name, check in DEPENDENCIES.items():
        try:
            results[name] = check()
        except Exception:
            results[name] = False
    ok = all(results.values())
    return JSONResponse(
        {"status": "ready" if ok else "not_ready", "checks": results},
        status_code=200 if ok else 503,
    )


@app.get("/items/{item_id}")
def get_item(item_id: int) -> dict[str, int]:
    with tracer.start_as_current_span("load_item") as span:  # child of the request span
        span.set_attribute("item.id", item_id)
        logger.info("loading item %s", item_id)
        return {"id": item_id}


if __name__ == "__main__":
    client = TestClient(app)
    print(client.get("/healthz").json())
    print(client.get("/readyz").json())
    r = client.get("/items/5", headers={"X-Request-ID": "req-abc"})
    print(r.json(), r.headers["X-Request-ID"])

    DEPENDENCIES["database"] = lambda: False  # simulate an outage
    r = client.get("/readyz")
    print(r.status_code, r.json())

    print("-- spans (finished, in order)")
    for span in span_exporter.get_finished_spans():
        if span.kind == SpanKind.SERVER or span.name == "load_item":
            attrs = span.attributes or {}
            keep = {
                k: v for k, v in attrs.items() if k in {"http.route", "http.status_code", "item.id"}
            }
            print(f"{span.name:<22} {span.kind.name:<8} {keep}")

    print("-- metric data points")
    data = metric_reader.get_metrics_data()
    for rm in data.resource_metrics if data else []:
        for sm in rm.scope_metrics:
            for metric in sm.metrics:
                for point in metric.data.data_points:  # type: ignore[attr-defined]
                    print(metric.name, dict(point.attributes), point.value)  # type: ignore[attr-defined]
