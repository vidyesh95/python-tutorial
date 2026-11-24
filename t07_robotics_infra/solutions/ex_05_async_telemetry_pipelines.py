"""Exercise 05: bounded buffers, batching, downsampling and clocks for telemetry.

Tasks
1. BoundedBuffer: asyncio.Queue wrapper with a drop policy and a drop counter.
2. batcher: async generator yielding lists flushed by size OR by max_wait.
3. Downsampler: accept at most one timestamp per min_interval.
4. ClockSync: convert monotonic timestamps to wall-clock time and detect clock jumps.

Run: uv run pytest t07_robotics_infra -k async_telemetry
"""

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

POLICIES = ("drop_newest", "drop_oldest", "block")


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


class Downsampler:
    def __init__(self, min_interval: float) -> None:
        self.min_interval = min_interval
        self.last: float | None = None

    def accept(self, ts: float) -> bool:
        if self.last is not None and not (ts - self.last >= self.min_interval):
            return False  # too soon (or time went backwards): skip
        self.last = ts
        return True


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
