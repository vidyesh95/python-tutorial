import pytest

from _loader import load

ex = load("t02_intermediate", "ex_10_decorators")


def test_call_counter():
    @ex.call_counter
    def add(a, b=0):
        """Add numbers."""
        return a + b

    assert add.calls == 0
    assert add(1, b=2) == 3
    add(5)
    assert add.calls == 2
    assert add.__name__ == "add" and add.__doc__ == "Add numbers."


def test_retry_succeeds_after_failures():
    state = {"calls": 0}

    @ex.retry(3, (ConnectionError,))
    def flaky():
        state["calls"] += 1
        if state["calls"] < 3:
            raise ConnectionError("down")
        return "ok"

    assert flaky() == "ok"
    assert state["calls"] == 3
    assert flaky.__name__ == "flaky"


def test_retry_gives_up_and_reraises():
    state = {"calls": 0}

    @ex.retry(2)
    def always_fails():
        state["calls"] += 1
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError, match="nope"):
        always_fails()
    assert state["calls"] == 2


def test_retry_ignores_other_exceptions():
    state = {"calls": 0}

    @ex.retry(5, (KeyError,))
    def wrong_error():
        state["calls"] += 1
        raise ValueError("not retried")

    with pytest.raises(ValueError):
        wrong_error()
    assert state["calls"] == 1


def test_memoize():
    calls = []

    @ex.memoize
    def square(n):
        """Square."""
        calls.append(n)
        return n * n

    assert square(4) == 16
    assert square(4) == 16
    assert square(5) == 25
    assert calls == [4, 5]
    assert square.__name__ == "square" and square.__doc__ == "Square."


def test_timed_records_duration_even_on_error():
    @ex.timed
    def work(fail=False):
        if fail:
            raise ValueError("x")
        return 42

    assert work.last_duration is None
    assert work() == 42
    assert isinstance(work.last_duration, float) and work.last_duration >= 0
    work.last_duration = None
    with pytest.raises(ValueError):
        work(fail=True)
    assert work.last_duration is not None


def test_add_repr_class_decorator():
    @ex.add_repr
    class Point:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    assert repr(Point(1, "a")) == "Point(x=1, y='a')"
    assert Point.__name__ == "Point"
