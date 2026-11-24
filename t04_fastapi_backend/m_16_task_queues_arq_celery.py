# Task Queues: arq and Celery
"""
When BackgroundTasks (m_11) is not enough, use a task queue. Three roles:

    PRODUCER  (your API)  -- enqueue(job) -->  BROKER (Redis/RabbitMQ)  -->  WORKER process(es)
                                                      ^ jobs wait here, survive restarts

- Producer: the API enqueues a small message (function name + arguments) and returns 202.
- Broker: durable storage for pending jobs (Redis for arq; Redis/RabbitMQ/SQS for Celery).
- Worker: a SEPARATE process that pulls jobs and runs them. Scale it independently.
- Result backend (optional): where status/return values are stored so the API can report them.

Reliability rules
- Retries with backoff: transient errors (network, 503) should be retried with exponential
  delay (0.5s, 1s, 2s, ... capped); permanent errors (bad input) should fail fast.
- At-least-once delivery: a job can run MORE THAN ONCE (worker crash after doing the work but
  before acking). So make jobs IDEMPOTENT: a stable job id / idempotency key, "upsert" instead
  of "insert", check "already done?" first. Never "charge the card" twice.
- Timeouts, a max-tries limit, and a dead-letter list/alert for jobs that keep failing.
- Pass IDs, not objects: serialize small JSON-able arguments and reload fresh data in the job.

arq (async, Redis-only, tiny): see `WorkerSettings` below. Producer side:
    pool = await arq.create_pool(RedisSettings.from_dsn(REDIS_URL))
    await pool.enqueue_job("send_report", 42, _job_id="report-42")   # same _job_id => deduped
Worker:  uv run arq t04_fastapi_backend.m_16_task_queues_arq_celery.WorkerSettings

Celery comparison (sync-first, mature, much bigger):
    celery_app = Celery("proj", broker="redis://...", backend="redis://...")
    @celery_app.task(bind=True, autoretry_for=(ConnectionError,), retry_backoff=True,
                     max_retries=5, acks_late=True)
    def send_report(self, user_id: int): ...
    send_report.delay(42)            # producer;   worker: celery -A proj worker
  Pick Celery for: RabbitMQ, canvas workflows (chains/groups), beat scheduling, huge ecosystem.
  Pick arq for: an all-async FastAPI codebase that already has Redis and wants minimal setup.
  Others: RQ (simple), Dramatiq, Temporal (durable workflows), cloud queues (SQS, Pub/Sub).

Below: an in-process asyncio.Queue worker with the SAME ideas (ids, retries, idempotency) so
the lesson runs with no Redis. It is for learning: jobs die with the process.

Run live:  uv run fastapi dev t04_fastapi_backend/m_16_task_queues_arq_celery.py

Common mistakes
- Running the worker with different code/config than the API (version skew).
- Non-idempotent jobs plus retries = duplicated side effects.
- Putting big payloads (files, ORM objects) in the message.
- No timeout: one stuck job blocks a worker slot forever.
- Retrying forever on permanent errors, hammering a dependency that is already down.

Production notes
- Run workers as their own deployment (same image, different command), scaled separately.
- Monitor queue depth, job age, failure rate (Flower for Celery; arq has `health_check`).
- Graceful shutdown: let in-flight jobs finish (SIGTERM) before stopping the worker.
- Cron-style jobs: arq `cron_jobs`, Celery beat, or Kubernetes CronJob. Ensure only one runs.
"""

import asyncio
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from arq.connections import RedisSettings
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel


# Example: the arq side (imported and configured, but not run in this offline demo)
async def send_report(ctx: dict[str, Any], user_id: int) -> str:
    """An arq job: first positional arg is always the worker context dict."""
    # ctx["job_try"] is 1 on the first attempt. Raise arq.Retry(defer=...) to retry later.
    return f"report for user {user_id} (try {ctx['job_try']})"


class WorkerSettings:
    """Discovered by the `arq` CLI. Nothing connects until the worker starts."""

    functions = [send_report]
    redis_settings = RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379"))
    max_tries = 5  # attempts per job
    job_timeout = 60  # seconds before a job is cancelled
    keep_result = 3600  # seconds the result stays queryable
    max_jobs = 10  # concurrency per worker process


# Example: the same ideas, in process
Handler = Callable[[dict[str, Any], dict[str, Any]], Awaitable[Any]]  # (ctx, payload) -> result


@dataclass
class Job:
    job_id: str
    payload: dict[str, Any]
    status: str = "queued"  # queued -> running -> done | failed
    attempts: int = 0
    result: Any = None
    error: str | None = None
    history: list[str] = field(default_factory=list)


class InProcessQueue:
    def __init__(self, handler: Handler, max_tries: int = 3, base_delay: float = 0.01) -> None:
        self.handler = handler
        self.max_tries = max_tries
        self.base_delay = base_delay
        self.jobs: dict[str, Job] = {}  # job_id -> Job (our "result backend")
        self._queue: asyncio.Queue[str | None] = asyncio.Queue()  # our "broker"
        self._task: asyncio.Task[None] | None = None

    async def enqueue(self, job_id: str, payload: dict[str, Any]) -> tuple[Job, bool]:
        """Idempotent: re-enqueueing the same job_id returns the existing job."""
        if job_id in self.jobs:
            return self.jobs[job_id], False
        job = self.jobs[job_id] = Job(job_id, payload)
        await self._queue.put(job_id)
        return job, True

    async def _run(self, job: Job) -> None:
        job.status = "running"
        while job.attempts < self.max_tries:
            job.attempts += 1
            try:
                job.result = await self.handler(
                    {"job_try": job.attempts, "job_id": job.job_id}, job.payload
                )
                job.status = "done"
                return
            except Exception as exc:
                job.error = str(exc)
                job.history.append(f"try {job.attempts}: {exc}")
                if job.attempts < self.max_tries:
                    await asyncio.sleep(min(1.0, self.base_delay * 2 ** (job.attempts - 1)))
        job.status = "failed"  # a real system would dead-letter and alert here

    async def worker(self) -> None:
        while (job_id := await self._queue.get()) is not None:
            await self._run(self.jobs[job_id])

    def start(self) -> None:
        self._task = asyncio.create_task(self.worker())

    async def stop(self) -> None:
        await self._queue.put(None)  # sentinel: drain, then exit
        if self._task:
            await self._task


async def flaky_report(ctx: dict[str, Any], payload: dict[str, Any]) -> str:
    if ctx["job_try"] <= payload.get("fail_times", 0):
        raise ConnectionError("upstream unavailable")  # transient: worth retrying
    return f"report ready after {ctx['job_try']} tries"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.queue = InProcessQueue(flaky_report)
    app.state.queue.start()  # the "worker process" (here: a task on the same loop)
    yield
    await app.state.queue.stop()


app = FastAPI(title="Task queues", lifespan=lifespan)


class JobRequest(BaseModel):
    job_id: str
    fail_times: int = 0


@app.post("/jobs", status_code=202)
async def create_job(body: JobRequest, request: Request) -> dict[str, Any]:
    job, created = await request.app.state.queue.enqueue(body.job_id, body.model_dump())
    return {"job_id": job.job_id, "status": job.status, "created": created}


@app.get("/jobs/{job_id}")
async def job_status(job_id: str, request: Request) -> dict[str, Any]:
    job: Job | None = request.app.state.queue.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job")
    return {
        "status": job.status,
        "attempts": job.attempts,
        "result": job.result,
        "history": job.history,
    }


def wait_for(client: TestClient, job_id: str, timeout: float = 2.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"/jobs/{job_id}").json()
        if body["status"] in {"done", "failed"}:
            return body
        time.sleep(0.01)
    raise TimeoutError(job_id)


if __name__ == "__main__":
    print("arq worker would run:", [f.__name__ for f in WorkerSettings.functions])
    with TestClient(app) as client:  # `with` starts the lifespan, and so the worker
        print(client.post("/jobs", json={"job_id": "a", "fail_times": 2}).json())
        print(wait_for(client, "a"))  # fails twice, succeeds on try 3

        again = client.post("/jobs", json={"job_id": "a", "fail_times": 2}).json()
        print("duplicate enqueue created a new job?", again["created"])  # False: idempotent

        client.post("/jobs", json={"job_id": "b", "fail_times": 99})
        print(wait_for(client, "b")["status"], "(gave up after max tries)")
