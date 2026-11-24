import types

import pytest

from _loader import load

ex = load("t02_intermediate", "ex_09_iterators_generators")


def test_countdown():
    assert list(ex.countdown(3)) == [3, 2, 1]
    assert list(ex.countdown(0)) == []
    assert list(ex.countdown(-2)) == []
    assert isinstance(ex.countdown(2), types.GeneratorType)


def test_chunked():
    assert list(ex.chunked([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]
    assert list(ex.chunked([], 3)) == []
    assert list(ex.chunked("abcd", 4)) == [["a", "b", "c", "d"]]
    assert list(ex.chunked(iter(range(3)), 10)) == [[0, 1, 2]]  # works on one-shot iterators
    with pytest.raises(ValueError):
        list(ex.chunked([1], 0))


def test_fibonacci_iterator():
    assert list(ex.Fibonacci(8)) == [0, 1, 1, 2, 3, 5, 8, 13]
    assert list(ex.Fibonacci(0)) == []
    it = ex.Fibonacci(2)
    assert iter(it) is it
    assert (next(it), next(it)) == (0, 1)
    with pytest.raises(StopIteration):
        next(it)


def test_deep_flatten():
    assert list(ex.deep_flatten([1, [2, [3, "ab"]], (4,)])) == [1, 2, 3, "ab", 4]
    assert list(ex.deep_flatten([])) == []
    assert list(ex.deep_flatten([[], [[]]])) == []


def test_parse_numbers_is_lazy():
    assert list(ex.parse_numbers(["1", "", "# note", " 2 "])) == [1, 2]
    consumed = []

    def source():
        for line in ["1", "2", "3"]:
            consumed.append(line)
            yield line

    gen = ex.parse_numbers(source())
    assert next(gen) == 1
    assert consumed == ["1"]  # only what was needed
