import pytest

from _loader import load

ex = load("t01_fundamentals", "ex_09_lists")


def test_remove_duplicates():
    assert ex.remove_duplicates([3, 1, 3, 2, 1]) == [3, 1, 2]
    assert ex.remove_duplicates([]) == []
    assert ex.remove_duplicates(["a", "a"]) == ["a"]


def test_rotate():
    assert ex.rotate([1, 2, 3, 4, 5], 2) == [4, 5, 1, 2, 3]
    assert ex.rotate([1, 2, 3], 3) == [1, 2, 3]
    assert ex.rotate([1, 2, 3], -1) == [2, 3, 1]
    assert ex.rotate([], 4) == []
    original = [1, 2, 3]
    ex.rotate(original, 1)
    assert original == [1, 2, 3]


def test_flatten():
    assert ex.flatten([[1, 2], [3], []]) == [1, 2, 3]
    assert ex.flatten([]) == []
    assert ex.flatten([["a"], ["b", "c"]]) == ["a", "b", "c"]


def test_second_largest():
    assert ex.second_largest([4, 9, 2, 7]) == 7
    assert ex.second_largest([5, 5, 3]) == 3
    assert ex.second_largest([1, 1]) is None
    assert ex.second_largest([]) is None
    assert ex.second_largest([-1, -5]) == -5


def test_chunk():
    assert ex.chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert ex.chunk([], 3) == []
    assert ex.chunk([1, 2], 5) == [[1, 2]]
    with pytest.raises(ValueError):
        ex.chunk([1], 0)
