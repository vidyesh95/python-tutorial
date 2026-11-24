"""Exercise 04: Threads, Processes and the GIL.

Tasks
1. ThreadSafeCounter: a counter whose `increment()` is safe across threads.
2. parallel_map_threads: run a function over items in a thread pool, keeping input order.
3. run_collecting_errors: run callables in threads; return (results, errors) without raising.
4. pipeline: producer/consumer with queue.Queue and a sentinel; return the transformed items.
5. cpu_sum_of_squares / parallel_sum_of_squares: split CPU work across a process pool.

Run: uv run pytest t03_advanced -k threading_multiprocessing
"""

import queue
import threading
from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any


class ThreadSafeCounter:
    """A counter with `value` (starts at 0) and `increment(n=1)` safe to call from many threads."""

    value: int

    def __init__(self) -> None:
        self.value = 0
        self._lock = threading.Lock()

    def increment(self, n: int = 1) -> None:
        with self._lock:
            self.value += n


def parallel_map_threads[T, R](
    func: Callable[[T], R], items: Iterable[T], max_workers: int = 4
) -> list[R]:
    """Apply `func` to every item using a ThreadPoolExecutor. Results keep the input order."""
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(func, items))


def run_collecting_errors(
    tasks: list[Callable[[], Any]], max_workers: int = 4
) -> tuple[list[Any], list[Exception]]:
    """Run each zero-argument task in a thread pool.

    Return (results, errors): `results` holds the return values of tasks that succeeded in
    their ORIGINAL order; `errors` holds the exceptions of those that failed (original order).
    Never raise.
    """
    results: list[Any] = []
    errors: list[Exception] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(task) for task in tasks]
        for fut in futures:
            exc = fut.exception()
            if exc is None:
                results.append(fut.result())
            else:
                assert isinstance(exc, Exception)
                errors.append(exc)
    return results, errors


_SENTINEL = object()


def pipeline[T, R](items: Iterable[T], transform: Callable[[T], R], maxsize: int = 2) -> list[R]:
    """Producer thread puts items on a bounded queue.Queue, a consumer thread applies
    `transform` and collects the results. Use a sentinel to stop. Return results in order.
    """
    q: queue.Queue[Any] = queue.Queue(maxsize=maxsize)
    out: list[R] = []

    def produce() -> None:
        for item in items:
            q.put(item)
        q.put(_SENTINEL)

    def consume() -> None:
        while (item := q.get()) is not _SENTINEL:
            out.append(transform(item))

    threads = [threading.Thread(target=produce), threading.Thread(target=consume)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return out


def cpu_sum_of_squares(n: int) -> int:
    """Return sum(i*i for i in range(n)). Must be a module-level function (picklable)."""
    return sum(i * i for i in range(n))


def parallel_sum_of_squares(numbers: list[int], max_workers: int = 2) -> list[int]:
    """Compute cpu_sum_of_squares for each number in a ProcessPoolExecutor (in input order)."""
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(cpu_sum_of_squares, numbers))
