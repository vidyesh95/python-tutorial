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
    """Bounded queue with a policy for what to do when it is full.

    - `queue` attribute: the underlying asyncio.Queue(maxsize) (tests read it directly).
    - policy "block": `await put` waits for room (backpressure); nothing is ever dropped.
    - policy "drop_newest": when full, discard the INCOMING item.
    - policy "drop_oldest": when full, discard the oldest queued item and enqueue the new one.
    - `dropped` counts discarded items. An unknown policy raises ValueError in __init__.
    - `get()` returns the next item; `close()` enqueues the sentinel None and must never
      drop it, so it waits for room (even for the drop policies).
    """

    def __init__(self, maxsize: int, policy: str = "drop_oldest") -> None:
        raise NotImplementedError

    async def put(self, item: Any) -> None:
        raise NotImplementedError

    async def get(self) -> Any:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError


async def batcher(
    queue: asyncio.Queue[Any], max_size: int, max_wait: float, sentinel: object = None
) -> AsyncIterator[list[Any]]:
    """Read from `queue` and yield lists of items.

    - Yield as soon as a batch holds `max_size` items.
    - Yield a partial batch when `max_wait` seconds have passed since its FIRST item
      (never yield an empty batch; with no items just keep waiting).
    - When `sentinel` is read, yield the remaining partial batch (if any) and stop.
    Hint: asyncio.wait_for(queue.get(), timeout) and loop.time().
    """
    raise NotImplementedError
    yield []  # pragma: no cover  (makes this an async generator)


class Downsampler:
    """Keep at most one timestamp per `min_interval` seconds.

    accept(ts) is True for the first timestamp, then only when ts - last_accepted >=
    min_interval. A rejected timestamp does not move the reference. A timestamp earlier than
    the last accepted one (time went backwards) is rejected.
    """

    def __init__(self, min_interval: float) -> None:
        raise NotImplementedError

    def accept(self, ts: float) -> bool:
        raise NotImplementedError


class ClockSync:
    """Map a monotonic clock onto the wall clock (both injectable for tests).

    - On construction measure offset = wall_now() - mono_now() and store it in `offset`.
    - to_wall(mono_ts) = mono_ts + offset.
    - drift() = current (wall_now() - mono_now()) minus the stored offset: how far the wall
      clock jumped (NTP step) since the last sync. Positive = wall clock moved forward.
    - resync() re-measures and stores the offset.
    """

    def __init__(
        self,
        mono_now: Callable[[], float] = time.monotonic,
        wall_now: Callable[[], float] = time.time,
    ) -> None:
        raise NotImplementedError

    def to_wall(self, mono_ts: float) -> float:
        raise NotImplementedError

    def drift(self) -> float:
        raise NotImplementedError

    def resync(self) -> None:
        raise NotImplementedError
