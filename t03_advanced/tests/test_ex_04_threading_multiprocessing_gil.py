import threading
import time

from _loader import load

ex = load("t03_advanced", "ex_04_threading_multiprocessing_gil")


def test_counter_is_thread_safe():
    counter = ex.ThreadSafeCounter()
    assert counter.value == 0

    def work():
        for _ in range(5_000):
            counter.increment()

    threads = [threading.Thread(target=work) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert counter.value == 20_000
    counter.increment(5)
    assert counter.value == 20_005


def test_parallel_map_threads_keeps_order():
    def slow_double(x):
        time.sleep(0.03 if x % 2 == 0 else 0.0)  # later items finish first
        return x * 2

    assert ex.parallel_map_threads(slow_double, range(8), max_workers=4) == [
        0,
        2,
        4,
        6,
        8,
        10,
        12,
        14,
    ]


def test_parallel_map_threads_actually_uses_threads():
    names = ex.parallel_map_threads(lambda _: threading.current_thread().name, range(4))
    assert all(n != threading.main_thread().name for n in names)


def test_run_collecting_errors():
    def boom():
        raise ValueError("bad")

    tasks = [lambda: 1, boom, lambda: 3, lambda: (_ for _ in ()).throw(KeyError("k"))]
    results, errors = ex.run_collecting_errors(tasks)
    assert results == [1, 3]
    assert [type(e) for e in errors] == [ValueError, KeyError]


def test_run_collecting_errors_all_ok():
    assert ex.run_collecting_errors([lambda: "a", lambda: "b"]) == (["a", "b"], [])


def test_pipeline_runs_in_other_threads_and_preserves_order():
    seen = set()

    def transform(x):
        seen.add(threading.current_thread().name)
        return x * x

    assert ex.pipeline(range(10), transform, maxsize=2) == [i * i for i in range(10)]
    assert threading.main_thread().name not in seen
    assert ex.pipeline([], str) == []


def test_pipeline_allows_none_items():
    # None / falsy values are real items, not a stop signal.
    assert ex.pipeline([1, None, 0, 2], lambda x: x) == [1, None, 0, 2]


def test_cpu_sum_of_squares():
    assert ex.cpu_sum_of_squares(0) == 0
    assert ex.cpu_sum_of_squares(4) == 0 + 1 + 4 + 9


def test_parallel_sum_of_squares_uses_processes():
    numbers = [10, 100, 1_000, 5]
    assert ex.parallel_sum_of_squares(numbers) == [sum(i * i for i in range(n)) for n in numbers]
