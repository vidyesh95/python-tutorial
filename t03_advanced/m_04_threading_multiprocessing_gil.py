# Threads, Processes and the GIL
"""
Python gives you three concurrency tools. Pick by the kind of work:

- I/O-bound (network, disk, DB waits): threads (or asyncio). The GIL is released while
  a thread waits on I/O, so many threads overlap their waiting.
- CPU-bound (number crunching in pure Python): processes. Each process has its own
  interpreter and its own GIL, so they run on separate cores.
- Shared state between threads needs locks (or better: queues, which do the locking).

The GIL (Global Interpreter Lock) is a mutex in CPython: only one thread executes Python
bytecode at a time. It keeps reference counting simple and safe, but it means CPU-bound
threads do not run in parallel. It does NOT make your own compound operations atomic
(`counter += 1` is read, add, write: threads can interleave in the middle).

concurrent.futures gives one API for both: ThreadPoolExecutor and ProcessPoolExecutor.

Free-threaded CPython (the "t" builds, e.g. `uv python install 3.15t`) removes the GIL
(PEP 703). It was experimental in 3.13 and became officially supported in 3.14 (PEP 779),
though the default build still has the GIL. Threads then run Python code in parallel, but you must lock shared state yourself, and some C extensions may re-enable
the GIL (override with the PYTHON_GIL=0/1 environment variable).
"""

import queue
import sys
import threading
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

# Spawned child processes re-import this module, so ALL demo code lives in functions that
# are only called under the __main__ guard below. Only definitions stay at module level.


# Example: which build am I on? (_is_gil_enabled only exists on 3.13+, so guard it)
def demo_gil_build() -> None:
    is_gil_enabled = getattr(sys, "_is_gil_enabled", lambda: True)
    print("GIL enabled:", is_gil_enabled())


# Example: threads overlap waiting (simulated I/O with sleep)
def fake_io(i: int) -> int:
    time.sleep(0.05)  # sleep releases the GIL, just like a socket read would
    return i * 2


def demo_threads_for_io() -> None:
    start = time.perf_counter()
    results = [fake_io(i) for i in range(8)]
    serial = time.perf_counter() - start

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as pool:
        threaded_results = list(pool.map(fake_io, range(8)))  # results keep input order
    threaded = time.perf_counter() - start
    print("same results:", results == threaded_results)
    print("threads faster for I/O:", threaded < serial)  # ~0.05s vs ~0.4s


# Example: a race condition, and the Lock that fixes it
class Counter:
    def __init__(self) -> None:
        self.value = 0
        self._lock = threading.Lock()

    def unsafe_incr(self) -> None:
        self.value += 1  # read-modify-write: NOT atomic

    def safe_incr(self) -> None:
        with self._lock:  # only one thread inside at a time
            self.value += 1


def hammer(fn: Callable[[], None], n: int) -> None:
    for _ in range(n):
        fn()


def demo_lock() -> None:
    counter = Counter()
    threads = [threading.Thread(target=hammer, args=(counter.safe_incr, 20_000)) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print("locked counter:", counter.value)  # always 80000
    # unsafe_incr may or may not lose updates depending on build and version: never rely on it.


# Example: producer/consumer with queue.Queue (thread-safe, no explicit locks needed)
def producer(q: queue.Queue[int | None], n: int) -> None:
    for i in range(n):
        q.put(i)
    q.put(None)  # sentinel: "no more work"


def consumer(q: queue.Queue[int | None], out: list[int]) -> None:
    while (item := q.get()) is not None:
        out.append(item * item)


def demo_queue() -> None:
    q: queue.Queue[int | None] = queue.Queue(maxsize=4)  # maxsize gives back-pressure
    squares: list[int] = []
    workers = [
        threading.Thread(target=producer, args=(q, 5)),
        threading.Thread(target=consumer, args=(q, squares)),
    ]
    for t in workers:
        t.start()
    for t in workers:
        t.join()
    print("squares:", squares)


# Example: futures, as_completed and exceptions that travel back to the caller
def risky(n: int) -> int:
    if n == 3:
        raise ValueError("three is unlucky")
    return n


def demo_futures() -> None:
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(risky, n): n for n in range(5)}
        for fut in as_completed(futures):  # yields in completion order
            try:
                fut.result()  # re-raises the worker's exception here
            except ValueError as exc:
                print(f"task {futures[fut]} failed: {exc}")


# Example: CPU-bound work in processes
def cpu_heavy(n: int) -> int:
    return sum(i * i for i in range(n))


def demo_processes() -> None:
    # Worker functions must be importable and arguments picklable.
    with ProcessPoolExecutor(max_workers=2) as proc_pool:
        totals = list(proc_pool.map(cpu_heavy, [10_000, 20_000, 30_000]))
    print("process results:", totals)


if __name__ == "__main__":
    demo_gil_build()
    demo_threads_for_io()
    demo_lock()
    demo_queue()
    demo_futures()
    demo_processes()


"""
Common mistakes
- Using threads to speed up pure-Python number crunching (the GIL serializes it).
- Using processes for tiny tasks: spawning and pickling cost more than the work.
- Forgetting the `if __name__ == "__main__":` guard around process pools.
- Sharing mutable state across threads without a Lock or Queue.
- Passing lambdas or open sockets to a process pool (not picklable).
- Calling fut.result() never: exceptions in workers are silently stored in the future.
- Assuming the GIL makes `x += 1` or check-then-act sequences safe.

Where this shows up in backend/ML/robotics work
- Backend: thread pools for blocking DB drivers and SDKs; gunicorn/uvicorn workers are
  processes (one GIL each); background job queues feed worker threads.
- ML: PyTorch DataLoader workers are processes; NumPy and PyTorch release the GIL in
  C code so threads help there too; free-threaded Python is being tested for inference servers.
- Robotics: sensor reader threads feed a queue consumed by a control loop; heavy vision
  or planning moves to separate processes (ROS nodes are processes).
"""
