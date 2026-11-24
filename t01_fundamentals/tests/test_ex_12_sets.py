from _loader import load

ex = load("t01_fundamentals", "ex_12_sets")


def test_has_duplicates():
    assert ex.has_duplicates([1, 2, 3, 2]) is True
    assert ex.has_duplicates([1, 2, 3]) is False
    assert ex.has_duplicates([]) is False


def test_common_elements():
    assert ex.common_elements([1, 2, 2, 3], [2, 3, 4]) == [2, 3]
    assert ex.common_elements([1], [2]) == []
    assert ex.common_elements([], []) == []


def test_only_in_first():
    assert ex.only_in_first([1, 2, 3, 3], [3, 4]) == [1, 2]
    assert ex.only_in_first([1], [1]) == []
    assert ex.only_in_first([], [1]) == []


def test_is_pangram():
    assert ex.is_pangram("The quick brown fox jumps over the lazy dog") is True
    assert ex.is_pangram("Hello world") is False
    assert ex.is_pangram("") is False


def test_unique_sorted():
    assert ex.unique_sorted([3, 1, 3, 2, 1]) == [1, 2, 3]
    assert ex.unique_sorted([]) == []
    assert ex.unique_sorted([-1, -1, 0]) == [-1, 0]
