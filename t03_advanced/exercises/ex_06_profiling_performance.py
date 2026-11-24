"""Exercise 06: Profiling and Performance.

Tasks
1. best_time: benchmark a callable with timeit and return the MINIMUM per-call seconds.
2. peak_memory: measure peak bytes allocated while a callable runs (tracemalloc).
3. call_counts: profile a callable with cProfile and return {function name: call count}.
4. has_duplicates: O(n) duplicate check (use a set, not nested loops).
5. Vec2: a 2D vector with __slots__ (no per-instance __dict__).

Run: uv run pytest t03_advanced -k profiling
"""

from collections.abc import Callable, Hashable, Iterable
from typing import Any


def best_time(func: Callable[[], Any], repeat: int = 3, number: int = 10) -> float:
    """Return the minimum of `repeat` runs, each calling `func` `number` times, divided by `number`.

    Use timeit.repeat. The result is seconds per single call.
    """
    raise NotImplementedError


def peak_memory(func: Callable[[], Any]) -> int:
    """Run `func()` under tracemalloc and return the peak number of traced bytes.

    Make sure tracing is stopped again afterwards, even if `func` raises.
    """
    raise NotImplementedError


def call_counts(func: Callable[[], Any]) -> dict[str, int]:
    """Run `func()` under cProfile; return {function_name: number_of_calls}.

    Hint: pstats.Stats(profiler).stats maps (file, line, name) -> (cc, nc, tt, ct, callers).
    Use `nc` (total calls). If two functions share a name, add their counts.
    """
    raise NotImplementedError


def has_duplicates(items: Iterable[Hashable]) -> bool:
    """Return True if any item appears twice. Must be O(n) and work on any iterable."""
    raise NotImplementedError


class Vec2:
    """A 2D vector with attributes `x` and `y` that uses __slots__.

    Instances must have no __dict__ and must reject new attributes (AttributeError).
    """

    def __init__(self, x: float, y: float) -> None:
        raise NotImplementedError
