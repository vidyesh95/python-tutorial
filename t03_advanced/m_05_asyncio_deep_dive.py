# asyncio Deep Dive
"""
asyncio runs many tasks on ONE thread using cooperative multitasking.
- A coroutine is what `async def` returns when called. Nothing runs until it is awaited
  or wrapped in a Task.
- The event loop picks a ready task, runs it until it hits an `await` that cannot finish
  yet, then switches to another. Blocking calls (time.sleep, requests, heavy CPU) freeze
  EVERY task: use `await asyncio.sleep`, async libraries, or `asyncio.to_thread`.
- A Task is a coroutine scheduled on the loop (asyncio.create_task / TaskGroup.create_task).
- Structured concurrency (3.11+): `async with asyncio.TaskGroup()` waits for all children;
  if one fails, the others are cancelled and the errors arrive as an ExceptionGroup.
- Cancellation is delivered as asyncio.CancelledError at the next await. Clean up in
  `finally` and re-raise it.
- asyncio.timeout(seconds) cancels the body when time runs out and raises TimeoutError.
- Semaphore limits concurrency; Queue gives back-pressure between producers and consumers.
"""

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

TICK = 0.01  # tiny sleeps keep the whole lesson fast


# Example: coroutines only run when awaited; gather runs them concurrently
async def fetch(name: str, delay: float) -> str:
    await asyncio.sleep(delay)
    return f"{name} done"


async def concurrency_basics() -> None:
    coro = fetch("a", TICK)  # created, NOT started
    print("coroutine object:", type(coro).__name__)
    print(await coro)

    start = time.perf_counter()
    results = await asyncio.gather(fetch("x", 0.05), fetch("y", 0.05), fetch("z", 0.05))
    elapsed = time.perf_counter() - start
    print(results, "concurrent:", elapsed < 0.12)  # ~0.05s, not 0.15s


# Example: gather vs TaskGroup when something fails
async def boom(delay: float) -> None:
    await asyncio.sleep(delay)
    raise ValueError(f"failed after {delay}")


async def gather_vs_taskgroup() -> None:
    # gather(return_exceptions=True) collects everything, including failures.
    results = await asyncio.gather(fetch("ok", TICK), boom(TICK), return_exceptions=True)
    print("gather:", results)

    # Without return_exceptions, gather raises the first error but the OTHER tasks keep
    # running in the background. TaskGroup cancels siblings and raises an ExceptionGroup.
    survivor_finished = False

    async def long_task() -> None:
        nonlocal survivor_finished
        await asyncio.sleep(1)
        survivor_finished = True  # never reached: cancelled by the group

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(long_task())
            tg.create_task(boom(TICK))
    except* ValueError as eg:  # except* matches inside an ExceptionGroup
        print("taskgroup caught:", [str(e) for e in eg.exceptions])
    print("sibling cancelled:", not survivor_finished)


# Example: timeouts and cancellation
async def cancellable_worker() -> None:
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        print("worker: cleaning up")
        raise  # always re-raise so the cancel completes
    finally:
        print("worker: finally runs")


async def timeouts_and_cancellation() -> None:
    try:
        async with asyncio.timeout(0.03):
            await asyncio.sleep(1)
    except TimeoutError:
        print("timed out")

    task = asyncio.create_task(cancellable_worker())
    await asyncio.sleep(TICK)  # let it start
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("task cancelled:", task.cancelled())


# Example: limit concurrency with a Semaphore
async def limited_demo() -> None:
    sem = asyncio.Semaphore(2)
    active = peak = 0

    async def job(i: int) -> None:
        nonlocal active, peak
        async with sem:
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(TICK)
            active -= 1

    await asyncio.gather(*(job(i) for i in range(6)))
    print("peak concurrency:", peak)  # 2


# Example: producer/consumer with asyncio.Queue
async def producer_consumer() -> None:
    q: asyncio.Queue[int | None] = asyncio.Queue(maxsize=2)  # put() waits when full
    results: list[int] = []

    async def producer() -> None:
        for i in range(5):
            await q.put(i)
        await q.put(None)

    async def consumer() -> None:
        while (item := await q.get()) is not None:
            await asyncio.sleep(0.001)
            results.append(item * 10)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(producer())
        tg.create_task(consumer())
    print("consumed:", results)


# Example: blocking code off the loop with to_thread
def blocking_read() -> str:
    time.sleep(0.02)  # stands in for a blocking SDK call or file read
    return "blocking result"


async def to_thread_demo() -> None:
    ticks = 0

    async def ticker(stop: asyncio.Event) -> None:
        nonlocal ticks
        while not stop.is_set():
            await asyncio.sleep(0.002)
            ticks += 1

    async def run_blocking(stop: asyncio.Event) -> str:
        try:
            return await asyncio.to_thread(blocking_read)  # runs in the default thread pool
        finally:
            stop.set()

    stop = asyncio.Event()
    _, result = await asyncio.gather(ticker(stop), run_blocking(stop))
    print(result, "| loop stayed responsive:", ticks > 0)


# Example: async generators and async context managers
async def countdown(n: int) -> AsyncIterator[int]:
    for i in range(n, 0, -1):
        await asyncio.sleep(0.001)
        yield i


@asynccontextmanager
async def connection(name: str) -> AsyncIterator[str]:
    print(f"open {name}")
    try:
        yield f"conn-{name}"
    finally:
        print(f"close {name}")  # runs even on errors or cancellation


async def async_iteration_demo() -> None:
    values = [i async for i in countdown(3)]  # async comprehension
    print("countdown:", values)
    async with connection("db") as conn:
        print("using", conn)


async def main() -> None:
    for step in (
        concurrency_basics,
        gather_vs_taskgroup,
        timeouts_and_cancellation,
        limited_demo,
        producer_consumer,
        to_thread_demo,
        async_iteration_demo,
    ):
        await step()


if __name__ == "__main__":
    asyncio.run(main())  # creates a loop, runs main, closes the loop


"""
Common mistakes
- Calling a blocking function (time.sleep, requests.get, CPU loops) inside a coroutine.
- Forgetting `await`: you get a coroutine object and a "never awaited" warning.
- create_task() without keeping a reference: the task can be garbage collected mid-run.
- Swallowing CancelledError (a bare `except Exception` is fine, `except BaseException` is not).
- asyncio.run() inside an already running loop (Jupyter, FastAPI handlers): just await.
- Unbounded gather over thousands of items: bound it with a Semaphore or a worker queue.
- Sharing a connection or client across event loops.

Where this shows up in backend/ML/robotics work
- Backend: FastAPI/Starlette handlers, async DB drivers, httpx, fan-out to several
  services with TaskGroup and a per-request timeout.
- ML/LLM: calling model APIs with bounded concurrency and retries, streaming tokens
  through async generators, batching requests from a queue.
- Robotics: message-bus clients, telemetry ingestion and websocket gateways; offload
  blocking driver calls with to_thread and keep control loops in separate processes.
"""
