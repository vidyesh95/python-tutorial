import inspect

import pytest

from _loader import load

ex = load("t03_advanced", "ex_03_functools_itertools")


def test_chunked_basic_and_lazy():
    assert list(ex.chunked([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]
    assert list(ex.chunked([], 3)) == []
    assert inspect.isgenerator(ex.chunked(iter(range(3)), 2))


def test_chunked_infinite_input():
    import itertools

    gen = ex.chunked(itertools.count(), 3)
    assert next(gen) == [0, 1, 2]
    assert next(gen) == [3, 4, 5]


def test_chunked_bad_n():
    with pytest.raises(ValueError):
        list(ex.chunked([1], 0))


def test_moving_average():
    assert ex.moving_average([1, 2, 3, 4, 5], 3) == [2.0, 3.0, 4.0]
    assert ex.moving_average([4, 8], 1) == [4.0, 8.0]
    assert ex.moving_average([1, 2], 3) == []
    assert ex.moving_average(iter([2, 4, 6]), 2) == [3.0, 5.0]


def test_make_multiplier():
    triple = ex.make_multiplier(3)
    assert triple(5) == 15
    assert ex.make_multiplier(0.5)(8) == 4.0


def test_describe_dispatch():
    assert ex.describe(7) == "int:7"
    assert ex.describe("hi") == "str:hi"
    assert ex.describe([1, 2, 3]) == "list of 3"
    assert ex.describe(2.5) == "other"
    assert ex.describe(None) == "other"
    assert hasattr(ex.describe, "register")  # really a singledispatch function


def test_run_length_encode():
    assert ex.run_length_encode("aaabcc") == [("a", 3), ("b", 1), ("c", 2)]
    assert ex.run_length_encode([]) == []
    assert ex.run_length_encode([1, 1, 2, 1]) == [(1, 2), (2, 1), (1, 1)]
