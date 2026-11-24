# Debugging Production Systems
"""
When your integration breaks in the customer's environment you often have no debugger, no shell
on the box, and an anxious audience. Calm, systematic debugging is the FDE superpower.

The loop: 1) STABILIZE (stop the bleeding: roll back, flip a flag, pause the sync) -> 2) OBSERVE
(logs, metrics, traces: what changed, when, for whom?) -> 3) REPRODUCE (smallest case, ideally a
test) -> 4) FIX -> 5) VERIFY -> 6) WRITE IT DOWN (timeline + follow-ups).

Make systems debuggable BEFORE they break
- STRUCTURED LOGS: one JSON object per line (`level`, `message`, `correlation_id`, fields) so you
  can filter/group them. Free-text logs do not scale past one server.
- CORRELATION IDS: generate (or accept `X-Request-ID`) at the edge, keep it in a `contextvars`
  variable, put it on every log line and forward it on outgoing calls. One id = the whole story.
- NEVER LOG SECRETS OR PII: redact tokens/passwords/emails at the logger, not by hand.
- Metrics for the golden signals (latency, traffic, errors, saturation) and alerts on symptoms.

Reading tracebacks
- Read bottom-up: the last line is the exception, the frames above are how you got there.
- "The above exception was the direct cause of..." (`raise X from Y`) chains: the ROOT CAUSE is
  usually the first one. Find the last frame in YOUR code, not in the library.
- `exc.add_note("while syncing customer 42")` attaches context; `ExceptionGroup` bundles many.

Inspecting a live process (read-only first!)
- `faulthandler.dump_traceback()` / `dump_traceback_later(timeout)`: where is every thread right
  now? Enable with `-X faulthandler` or `PYTHONFAULTHANDLER=1`; sends on SIGSEGV too.
- `py-spy dump --pid <pid>` (stack of a running process, no restart) and
  `py-spy record -o profile.svg --pid <pid>` (flame graph); Python 3.15 also ships a sampling
  profiler: `python -m profiling.sampling run script.py` / attach by pid.
- `tracemalloc`: `start()`, take snapshots, `snap2.compare_to(snap1, "lineno")` shows who leaks.

Reproduce, then bisect
- RECORD real (redacted) requests/responses and REPLAY them through `httpx.MockTransport` in a
  test: the bug becomes deterministic.
- `git bisect` (or `first_bad` below): binary search the commit/config/deploy that broke it in
  log2(n) steps, given a quick good/bad check.
- FEATURE FLAGS give you a kill switch and gradual rollout (1% -> 10% -> 100%): bad change? Flip
  the flag instead of redeploying.

Incidents: keep a TIMELINE (UTC timestamps: detected, mitigated, resolved), note decisions, and
afterwards a blameless review with concrete follow-ups.

Run: uv run python -m t08_forward_deployed.m_08_debugging_production
"""

import faulthandler
import hashlib
import io
import json
import logging
import re
import sys
import tempfile
import threading
import traceback
import tracemalloc
import uuid
from collections import defaultdict
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
SENSITIVE = re.compile(r"token|secret|password|authorization|api[_-]?key", re.I)
_STD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "taskName"}


# Example 1: JSON logs with a correlation id and automatic redaction
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id.get(),
        }
        for key, value in vars(record).items():  # everything passed via extra={...}
            if key not in _STD_ATTRS:
                entry[key] = "[REDACTED]" if SENSITIVE.search(key) else value
        if record.exc_info:
            entry["exc"] = "".join(traceback.format_exception(*record.exc_info)).strip()
        return json.dumps(entry, default=str)


def make_logger(stream: io.StringIO) -> logging.Logger:
    logger = logging.getLogger(f"demo.{uuid.uuid4().hex[:6]}")  # unique: no handler build-up
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


# Example 2: correlation id at the edge, forwarded downstream, grouped afterwards
def group_by_correlation(lines: list[str]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue  # a stray non-JSON line must not break the analysis
        groups[entry.get("correlation_id") or "-"].append(entry)
    return dict(groups)


def handle_request(
    logger: logging.Logger, http: httpx.Client, customer: int, request_id: str | None = None
) -> None:
    token = correlation_id.set(request_id or uuid.uuid4().hex[:8])  # accept the caller's id if sent
    try:
        logger.info(
            "sync started", extra={"customer": customer, "api_key": "sk_live_should_not_appear"}
        )
        try:
            http.get(
                f"/customers/{customer}", headers={"X-Request-ID": correlation_id.get() or ""}
            ).raise_for_status()
            logger.info("sync finished", extra={"customer": customer})
        except httpx.HTTPStatusError as exc:
            try:
                raise RuntimeError(f"sync failed for customer {customer}") from exc
            except RuntimeError:
                logger.exception("sync error", extra={"customer": customer})
    finally:
        correlation_id.reset(token)


# Example 3: reading a traceback programmatically
def root_cause(exc: BaseException) -> BaseException:
    while exc.__cause__ or (exc.__context__ and not exc.__suppress_context__):
        exc = exc.__cause__ or exc.__context__  # type: ignore[assignment]
    return exc


def last_app_frame(exc: BaseException, marker: str) -> str | None:
    frames = [f for f in traceback.extract_tb(exc.__traceback__) if marker in f.filename]
    return f"{frames[-1].name}:{frames[-1].lineno}" if frames else None


# Example 4: look inside a running process
def dump_threads() -> str:
    names = {t.ident: t.name for t in threading.enumerate()}
    return "\n".join(
        f"thread {names.get(tid, tid)}: {traceback.extract_stack(frame)[-1].name}"
        for tid, frame in sys._current_frames().items()
    )


def faulthandler_demo() -> str:
    with tempfile.TemporaryFile("w+") as fh:  # faulthandler needs a real file descriptor
        faulthandler.dump_traceback(file=fh, all_threads=True)
        fh.seek(0)
        return fh.read().splitlines()[0]


def leak_demo() -> str:
    tracemalloc.start()
    before = tracemalloc.take_snapshot()
    leaked = [bytes(1000) for _ in range(500)]  # the "leak": a cache nothing ever clears
    after = tracemalloc.take_snapshot()
    top = after.compare_to(before, "lineno")[0]
    tracemalloc.stop()
    return f"{top.traceback[0].filename.split('/')[-1]}:{top.traceback[0].lineno} +{top.size_diff // 1024} KiB ({len(leaked)} objects)"


# Example 5: record real traffic, replay it deterministically
class Recorder(httpx.BaseTransport):
    def __init__(self, inner: httpx.BaseTransport) -> None:
        self.inner, self.log = inner, []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = self.inner.handle_request(request)
        response.read()
        self.log.append(
            {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "body": response.text,
            }
        )  # headers (auth!) are deliberately not recorded
        return response


def replay_transport(recording: list[dict]) -> httpx.MockTransport:
    index = {(r["method"], r["path"]): r for r in recording}

    def handler(request: httpx.Request) -> httpx.Response:
        hit = index[(request.method, request.url.path)]
        return httpx.Response(hit["status"], text=hit["body"])

    return httpx.MockTransport(handler)


# Example 6: bisect, feature flags, incident timeline
def first_bad(items: list, is_bad: Callable[[object], bool]) -> object | None:
    """Binary search the first bad item, assuming everything after it is bad too."""
    lo, hi, found = 0, len(items) - 1, None
    while lo <= hi:
        mid = (lo + hi) // 2
        if is_bad(items[mid]):
            found, hi = items[mid], mid - 1
        else:
            lo = mid + 1
    return found


def flag_enabled(flag: str, user: str, percent: int, kill_switch: bool = False) -> bool:
    if kill_switch:
        return False
    bucket = int(hashlib.sha256(f"{flag}:{user}".encode()).hexdigest(), 16) % 100  # stable per user
    return bucket < percent


@dataclass
class Event:
    at: datetime
    what: str


def timeline_report(events: list[Event]) -> str:
    ordered = sorted(events, key=lambda e: e.at)
    start = ordered[0].at
    lines = [
        f"+{int((e.at - start).total_seconds() // 60):>3}m  {e.at:%H:%M}Z  {e.what}"
        for e in ordered
    ]
    return "\n".join(lines)


def run_demo() -> None:
    stream = io.StringIO()
    logger = make_logger(stream)

    def customer_api(request: httpx.Request) -> httpx.Response:
        bad = request.url.path.endswith("/13")
        return httpx.Response(500 if bad else 200, json={"id": request.url.path})

    recorder = Recorder(httpx.MockTransport(customer_api))
    http = httpx.Client(base_url="https://api.customer.test", transport=recorder)
    for customer in (7, 13, 21):
        handle_request(
            logger, http, customer, request_id=f"req-{customer}" if customer == 13 else None
        )

    groups = group_by_correlation(stream.getvalue().splitlines() + ["not json at all"])
    print("correlation ids:", len(groups), "| secrets in logs:", "sk_live" in stream.getvalue())
    for entry in groups["req-13"]:
        print(
            f"  req-13 {entry['level']:<5} {entry['message']}",
            "[REDACTED]" if entry.get("api_key") else "",
        )

    try:
        http.get("/customers/13").raise_for_status()
    except httpx.HTTPStatusError as exc:
        try:
            raise RuntimeError("sync failed") from exc
        except RuntimeError as err:
            print(
                "root cause:",
                type(root_cause(err)).__name__,
                "| app frame:",
                last_app_frame(err, "m_08_"),
            )
    print(
        "recorded",
        len(recorder.log),
        "requests; replay 13 ->",
        httpx.Client(base_url="https://x.test", transport=replay_transport(recorder.log))
        .get("/customers/13")
        .status_code,
    )

    print("\nthreads:", dump_threads().splitlines()[0])
    print("faulthandler:", faulthandler_demo())
    print("tracemalloc:", leak_demo())

    commits = [f"c{i:02d}" for i in range(32)]
    steps = []
    culprit = first_bad(commits, lambda c: (steps.append(c), c >= "c21")[1])
    print(f"\nbisect found {culprit} in {len(steps)} checks out of {len(commits)} commits")
    rollout = sum(flag_enabled("new-sync", f"user{i}", 10) for i in range(1000))
    print(
        f"flag at 10%: {rollout / 10:.1f}% of 1000 users | kill switch:",
        flag_enabled("new-sync", "user1", 100, True),
    )

    t0 = datetime(2026, 11, 24, 14, 2, tzinfo=UTC)
    print(
        "\n"
        + timeline_report(
            [
                Event(t0 + timedelta(minutes=19), "Rolled back release 41; error rate recovering"),
                Event(t0, "Alert: sync error rate > 5%"),
                Event(
                    t0 + timedelta(minutes=7),
                    "Correlated errors with customer 13 (HTTP 500 from ERP)",
                ),
                Event(t0 + timedelta(minutes=45), "Customer confirmed ERP patch; resolved"),
            ]
        )
    )


"""
Common mistakes:
- Debugging by adding print() to production, or changing three things at once.
- Logging at INFO for every row (cost, noise) yet nothing at the decision points.
- Losing the original exception (`raise NewError(...)` without `from exc`) or swallowing it.
- Logging secrets/PII "temporarily". Logs are copied everywhere and retained for months.
- Attaching a debugger or `gdb` to a customer process; prefer read-only tools (py-spy, logs).
- Fixing the symptom (restart) without a follow-up for the cause, or no timeline at all.

In the field:
- Ask first: what changed (deploy, data, volume, their upgrade), who is affected, since when.
- Keep a shared incident doc with UTC timestamps; communicate every 30 minutes even if "no news".
- Give the customer a one-line status and a next-update time, not a stream of theories.
- Add the missing log/metric/alert that would have caught it sooner, and a regression test.
- Never run experiments on production data; reproduce against a copy or recorded traffic.
"""

if __name__ == "__main__":
    run_demo()
