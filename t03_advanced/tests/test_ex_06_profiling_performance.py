import pytest

from _loader import load

ex = load("t03_advanced", "ex_06_profiling_performance")


def test_best_time_is_per_call_and_positive():
    calls = []
    t = ex.best_time(lambda: calls.append(1), repeat=3, number=5)
    assert len(calls) == 15
    assert isinstance(t, float) and 0 <= t < 0.1


def test_best_time_tracks_work_done():
    fast = ex.best_time(lambda: None, repeat=3, number=20)
    slow = ex.best_time(lambda: sum(range(50_000)), repeat=3, number=20)
    assert slow > fast


def test_peak_memory_sees_allocations():
    small = ex.peak_memory(lambda: [0] * 10)
    big = ex.peak_memory(lambda: [0] * 1_000_000)
    assert big > 1_000_000 > small


def test_peak_memory_stops_tracing_even_on_error():
    import tracemalloc

    def boom():
        raise ValueError("x")

    with pytest.raises(ValueError):
        ex.peak_memory(boom)
    assert not tracemalloc.is_tracing()


def test_call_counts():
    def helper(n):
        return n + 1

    def work():
        for i in range(7):
            helper(i)

    counts = ex.call_counts(work)
    assert counts["helper"] == 7
    assert counts["work"] == 1


def test_has_duplicates():
    assert ex.has_duplicates([1, 2, 3, 1]) is True
    assert ex.has_duplicates([1, 2, 3]) is False
    assert ex.has_duplicates([]) is False
    assert ex.has_duplicates(iter("hello")) is True
    assert ex.has_duplicates(str(i) for i in range(1000)) is False


def test_vec2_uses_slots():
    v = ex.Vec2(1.0, 2.0)
    assert (v.x, v.y) == (1.0, 2.0)
    assert not hasattr(v, "__dict__")
    with pytest.raises(AttributeError):
        v.z = 3  # type: ignore[attr-defined]
    v.x = 5.0
    assert v.x == 5.0
