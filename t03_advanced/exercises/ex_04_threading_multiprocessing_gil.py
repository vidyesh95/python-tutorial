"""Exercise 04: Threads, Processes and the GIL.

Tasks
1. ThreadSafeCounter: a counter whose `increment()` is safe across threads.
2. parallel_map_threads: run a function over items in a thread pool, keeping input order.
3. run_collecting_errors: run callables in threads; return (results, errors) without raising.
4. pipeline: producer/consumer with queue.Queue and a sentinel; return the transformed items.
5. cpu_sum_of_squares / parallel_sum_of_squares: split CPU work across a process pool.

Run: uv run pytest t03_advanced -k threading_multiprocessing
"""

from collections.abc import Callable, Iterable
from typing import Any


class ThreadSafeCounter:
    """A counter with `value` (starts at 0) and `increment(n=1)` safe to call from many threads."""

    value: int

    def __init__(self) -> None:
        raise NotImplementedError

    def increment(self, n: int = 1) -> None:
        raise NotImplementedError


def parallel_map_threads[T, R](
    func: Callable[[T], R], items: Iterable[T], max_workers: int = 4
) -> list[R]:
    """Apply `func` to every item using a ThreadPoolExecutor. Results keep the input order."""
    raise NotImplementedError


def run_collecting_errors(
    tasks: list[Callable[[], Any]], max_workers: int = 4
) -> tuple[list[Any], list[Exception]]:
    """Run each zero-argument task in a thread pool.

    Return (results, errors): `results` holds the return values of tasks that succeeded in
    their ORIGINAL order; `errors` holds the exceptions of those that failed (original order).
    Never raise.
    """
    raise NotImplementedError


def pipeline[T, R](items: Iterable[T], transform: Callable[[T], R], maxsize: int = 2) -> list[R]:
    """Producer thread puts items on a bounded queue.Queue, a consumer thread applies
    `transform` and collects the results. Use a sentinel to stop. Return results in order.
    """
    raise NotImplementedError


def cpu_sum_of_squares(n: int) -> int:
    """Return sum(i*i for i in range(n)). Must be a module-level function (picklable)."""
    raise NotImplementedError


def parallel_sum_of_squares(numbers: list[int], max_workers: int = 2) -> list[int]:
    """Compute cpu_sum_of_squares for each number in a ProcessPoolExecutor (in input order)."""
    raise NotImplementedError
