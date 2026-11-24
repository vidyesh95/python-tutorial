"""Exercise 16: Task queues (an in-process queue and worker, no Redis needed).

Tasks
1. backoff_delay: exponential backoff with a cap.
2. JobQueue.enqueue: idempotent enqueue by job id.
3. run_job: run a handler with retries and backoff; report the outcome.
4. worker: consume the queue until the close sentinel, recording each job's outcome.

Run: uv run pytest t04_fastapi_backend -k task_queues
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

Handler = Callable[[dict[str, Any]], Awaitable[Any]]
Sleep = Callable[[float], Awaitable[None]]


def backoff_delay(attempt: int, base: float = 0.5, cap: float = 30.0) -> float:
    """Seconds to wait after failed attempt number `attempt` (1-based).

    base * 2 ** (attempt - 1), but never more than `cap`.
    >>> backoff_delay(1), backoff_delay(2), backoff_delay(3)
    (0.5, 1.0, 2.0)
    """
    return min(cap, base * 2 ** (attempt - 1))


class JobQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue()
        self._seen: set[str] = set()

    async def enqueue(self, job_id: str, payload: dict[str, Any]) -> bool:
        """Put (job_id, payload) on the queue and return True.

        If this job_id was enqueued before, do nothing and return False (idempotency).
        """
        if job_id in self._seen:
            return False
        self._seen.add(job_id)
        await self._queue.put((job_id, payload))
        return True

    async def get(self) -> tuple[str, dict[str, Any]] | None:
        return await self._queue.get()

    async def close(self) -> None:
        """Tell the worker to stop after the jobs already queued."""
        await self._queue.put(None)


async def run_job(
    handler: Handler,
    payload: dict[str, Any],
    max_tries: int = 3,
    sleep: Sleep = asyncio.sleep,
) -> tuple[str, int]:
    """Call `await handler(payload)` up to `max_tries` times.

    Return ("done", attempts) on the first success. After each failed attempt that is not
    the last, `await sleep(backoff_delay(attempt))`. If every attempt fails return
    ("failed", max_tries). Never raise.
    """
    for attempt in range(1, max_tries + 1):
        try:
            await handler(payload)
            return "done", attempt
        except Exception:
            if attempt < max_tries:
                await sleep(backoff_delay(attempt))
    return "failed", max_tries


async def worker(
    queue: JobQueue,
    handler: Handler,
    results: dict[str, str],
    *,
    max_tries: int = 3,
    sleep: Sleep = asyncio.sleep,
) -> None:
    """Loop: `item = await queue.get()`; stop when it is None. Otherwise run the job with
    run_job and store results[job_id] = "done" or "failed".
    """
    while (item := await queue.get()) is not None:
        job_id, payload = item
        status, _ = await run_job(handler, payload, max_tries, sleep)
        results[job_id] = status
