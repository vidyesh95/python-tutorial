# Async Telemetry Pipelines
"""
Robots produce samples faster and more irregularly than a database can absorb them. A
telemetry pipeline sits in between: producers -> bounded buffer -> (downsample) -> batcher ->
sink. This builds on the asyncio basics in t03 m_05 (tasks, queues, TaskGroup, cancellation).

Backpressure: an UNBOUNDED queue hides a slow consumer until memory runs out. A BOUNDED
`asyncio.Queue(maxsize=N)` makes `await queue.put()` wait when full, which slows the producer
(works for a pull-able source such as a file or a socket you can stop reading). A live sensor
cannot be slowed down, so when the buffer is full you must choose what to lose:
- drop_newest: keep the backlog, discard the incoming sample (`put_nowait` + QueueFull).
- drop_oldest: discard the stalest sample to make room; best for "latest state matters".
- block: wait (true backpressure). Only for sources that can wait.
Always COUNT drops and export the number; silent loss is the real danger.

Batching: one INSERT per sample is slow. Flush when the batch reaches `max_size` OR when
`max_wait` seconds passed since its first item, whichever comes first, so a quiet period
still flushes (bounded latency) and a busy one amortizes cost (throughput).

Downsampling: a 1 kHz IMU rarely needs storing at 1 kHz. Keep at most one sample per
`min_interval`, or aggregate (mean/min/max) per window (m_06 rollups).

Clocks: `time.monotonic()` never jumps backwards (NTP step, manual change) so use it for
durations, timeouts and rate limits; it has an arbitrary origin and means nothing across
machines or reboots. `time.time()` is the wall clock (UTC epoch): use it for what you store
and show. Convert once: `wall = mono + (wall_at_start - mono_at_start)`; re-measure the
offset to detect a clock jump. Better still, stamp samples at the SOURCE (device clock or
hardware timestamp) and keep the arrival time separately.

Shutdown: stop producers, put a sentinel (or close the buffer), let the consumer drain what
is queued and flush the last partial batch, then exit. For SIGINT/SIGTERM use
`loop.add_signal_handler(sig, stop_event.set)` and have loops watch the event.

Common mistakes
- `asyncio.Queue()` with no maxsize: memory grows without bound when the sink slows down.
- Dropping data without counting it, or dropping the shutdown sentinel with the data.
- Never flushing a partial batch on shutdown, losing the last few seconds.
- Blocking calls (sqlite, file writes) inside a coroutine stall every task: use
  `asyncio.to_thread` for blocking sinks.
- Mixing monotonic and wall-clock timestamps in one column.
- Swallowing CancelledError in a worker so shutdown hangs.

Production notes
- Export queue depth, drop count, batch size and flush latency as metrics and alert on them.
- Decide per stream: control/safety signals are latest-only and low-latency; logs and
  video are batched and may be dropped; audit events must never be dropped (use a durable
  queue or disk spool).
- A sink failure should retry with backoff and then spool to disk, not wedge the pipeline.
- Watchdog on the consumer side: no data for N seconds from a device means "offline",
  not "everything is fine" (m_09).
"""

import asyncio
import random
import signal
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

POLICIES = ("drop_newest", "drop_oldest", "block")


# Example 1: a bounded buffer with explicit drop policies
class BoundedBuffer:
    def __init__(self, maxsize: int, policy: str = "drop_oldest") -> None:
        if policy not in POLICIES:
            raise ValueError(f"policy must be one of {POLICIES}")
        self.queue: asyncio.Queue[Any] = asyncio.Queue(maxsize)
        self.policy = policy
        self.dropped = 0

    async def put(self, item: Any) -> None:
        if self.policy == "block":
            await self.queue.put(item)  # waits when full: backpressure
            return
        try:
            self.queue.put_nowait(item)
        except asyncio.QueueFull:
            self.dropped += 1
            if self.policy == "drop_oldest":
                self.queue.get_nowait()
                self.queue.put_nowait(item)

    async def get(self) -> Any:
        return await self.queue.get()

    async def close(self) -> None:
        await self.queue.put(None)  # sentinel; waits for room so it is never dropped


# Example 2: size- and time-bounded batching
async def batcher(
    queue: asyncio.Queue[Any], max_size: int, max_wait: float, sentinel: object = None
) -> AsyncIterator[list[Any]]:
    loop = asyncio.get_running_loop()
    batch: list[Any] = []
    deadline = 0.0
    while True:
        timeout = None
        if batch:
            timeout = deadline - loop.time()
            if timeout <= 0:
                yield batch
                batch = []
                continue
        try:
            item = await asyncio.wait_for(queue.get(), timeout)
        except TimeoutError:
            continue  # loop top flushes the stale batch
        if item is sentinel:
            if batch:
                yield batch
            return
        if not batch:
            deadline = loop.time() + max_wait
        batch.append(item)
        if len(batch) >= max_size:
            yield batch
            batch = []


# Example 3: downsampling by minimum interval
class Downsampler:
    def __init__(self, min_interval: float) -> None:
        self.min_interval = min_interval
        self.last: float | None = None

    def accept(self, ts: float) -> bool:
        if self.last is not None and not (ts - self.last >= self.min_interval):
            return False  # too soon (or time went backwards): skip
        self.last = ts
        return True


# Example 4: monotonic -> wall clock conversion with jump detection
class ClockSync:
    def __init__(
        self,
        mono_now: Callable[[], float] = time.monotonic,
        wall_now: Callable[[], float] = time.time,
    ) -> None:
        self.mono_now, self.wall_now = mono_now, wall_now
        self.offset = self._measure()

    def _measure(self) -> float:
        return self.wall_now() - self.mono_now()

    def to_wall(self, mono_ts: float) -> float:
        return mono_ts + self.offset

    def drift(self) -> float:
        """How far the wall clock moved relative to monotonic since the last sync."""
        return self._measure() - self.offset

    def resync(self) -> None:
        self.offset = self._measure()


def install_shutdown(stop: asyncio.Event) -> None:
    """SIGINT/SIGTERM set the event; a no-op where signal handlers are unsupported."""
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError, RuntimeError:
            pass


# Example 5: the whole pipeline
async def run_pipeline(
    n_samples: int, policy: str, sink_delay: float, seed: int = 1
) -> dict[str, Any]:
    rng = random.Random(seed)
    buffer = BoundedBuffer(maxsize=20, policy=policy)
    stored: list[int] = []
    flushes: list[int] = []
    down = Downsampler(min_interval=0.0)  # 0.0 keeps everything; raise it to thin the stream

    async def producer() -> None:
        for i in range(n_samples):
            sample = {"seq": i, "mono": time.monotonic(), "value": rng.gauss(0, 1)}
            await buffer.put(sample)
            if i % 10 == 0:
                await asyncio.sleep(0)  # let the consumer run, like a real sensor period
        await buffer.close()

    async def consumer() -> None:
        async for batch in batcher(buffer.queue, max_size=16, max_wait=0.02):
            kept = [s for s in batch if down.accept(s["mono"])]
            await asyncio.sleep(sink_delay)  # a slow database write
            stored.extend(s["seq"] for s in kept)
            flushes.append(len(kept))

    async with asyncio.TaskGroup() as tg:
        tg.create_task(producer())
        tg.create_task(consumer())
    return {
        "policy": policy,
        "stored": len(stored),
        "dropped": buffer.dropped,
        "flushes": len(flushes),
    }


async def demo() -> None:
    for policy in ("block", "drop_oldest", "drop_newest"):
        result = await run_pipeline(300, policy, sink_delay=0.002)
        print(result)  # 'block' stores everything; the others trade completeness for latency

    sync = ClockSync(mono_now=lambda: 100.0, wall_now=lambda: 1_700_000_100.0)
    print("wall time of mono=105:", sync.to_wall(105.0))

    stop = asyncio.Event()
    install_shutdown(stop)
    stop.set()  # normally set by SIGTERM
    print("stop requested:", stop.is_set())


def run_demo() -> None:
    asyncio.run(demo())


if __name__ == "__main__":
    run_demo()
