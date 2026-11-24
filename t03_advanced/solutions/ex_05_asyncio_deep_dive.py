"""Exercise 05: asyncio Deep Dive.

Tasks
1. gather_limited: run coroutine factories concurrently but never more than `limit` at once.
2. first_success: return the first successful result, cancelling the rest (all fail -> raise).
3. with_timeout: await a coroutine with a deadline; return a default on timeout.
4. worker_pool: N workers consume an asyncio.Queue; return results in input order.
5. collect_stream: consume an async generator and return a list; plus `ticks`, an async
   generator that yields 0..n-1.

Tests call these with asyncio.run(...). Keep sleeps tiny.

Run: uv run pytest t03_advanced -k asyncio_deep_dive
"""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable


async def gather_limited[T](factories: list[Callable[[], Awaitable[T]]], limit: int) -> list[T]:
    """Call each factory to get an awaitable, run them concurrently with at most `limit`
    in flight (asyncio.Semaphore), and return results in the ORIGINAL order.
    If one raises, propagate (use a TaskGroup so the rest are cancelled).
    """
    sem = asyncio.Semaphore(limit)

    async def run(factory: Callable[[], Awaitable[T]]) -> T:
        async with sem:
            return await factory()

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(run(f)) for f in factories]
    return [t.result() for t in tasks]


async def first_success[T](factories: list[Callable[[], Awaitable[T]]]) -> T:
    """Start all factories concurrently; return the first result that does NOT raise.

    Cancel the remaining tasks before returning. If every factory fails, raise RuntimeError.
    """

    async def run(factory: Callable[[], Awaitable[T]]) -> T:
        return await factory()

    pending = {asyncio.ensure_future(run(f)) for f in factories}
    try:
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                if task.exception() is None:
                    return task.result()
        raise RuntimeError("all tasks failed")
    finally:
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)


async def with_timeout[T](awaitable: Awaitable[T], seconds: float, default: T) -> T:
    """Await `awaitable` for at most `seconds` (asyncio.timeout); return `default` on timeout."""
    try:
        async with asyncio.timeout(seconds):
            return await awaitable
    except TimeoutError:
        return default


async def worker_pool[T, R](
    items: list[T], handler: Callable[[T], Awaitable[R]], workers: int = 3
) -> list[R]:
    """Put items (with their index) on an asyncio.Queue; `workers` tasks pull from it and call
    `handler`. Return the results in input order. Use a TaskGroup and queue.join()/sentinels.
    """
    queue: asyncio.Queue[tuple[int, T] | None] = asyncio.Queue()
    for pair in enumerate(items):
        queue.put_nowait(pair)
    for _ in range(workers):
        queue.put_nowait(None)  # one stop signal per worker
    results: list[R | None] = [None] * len(items)

    async def worker() -> None:
        while (job := await queue.get()) is not None:
            index, item = job
            results[index] = await handler(item)

    async with asyncio.TaskGroup() as tg:
        for _ in range(workers):
            tg.create_task(worker())
    return results  # type: ignore[return-value]


async def ticks(n: int) -> AsyncIterator[int]:
    """Async generator yielding 0..n-1, awaiting asyncio.sleep(0) between items."""
    for i in range(n):
        await asyncio.sleep(0)
        yield i


async def collect_stream[T](stream: AsyncIterator[T]) -> list[T]:
    """Consume an async iterator fully and return its items as a list."""
    return [item async for item in stream]
