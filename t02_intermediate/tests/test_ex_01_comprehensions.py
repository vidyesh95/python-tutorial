import types

from _loader import load

ex = load("t02_intermediate", "ex_01_comprehensions")


def test_squares_of_evens():
    assert ex.squares_of_evens([1, 2, 3, 4]) == [4, 16]
    assert ex.squares_of_evens([]) == []
    assert ex.squares_of_evens([1, 3]) == []
    assert ex.squares_of_evens([-2, 0]) == [4, 0]


def test_word_lengths():
    assert ex.word_lengths(["hi", "hello"]) == {"hi": 2, "hello": 5}
    assert ex.word_lengths([]) == {}
    assert ex.word_lengths(["a", "a"]) == {"a": 1}


def test_unique_first_letters():
    assert ex.unique_first_letters(["Apple", "avocado", "Banana", ""]) == {"a", "b"}
    assert ex.unique_first_letters([]) == set()
    assert isinstance(ex.unique_first_letters(["x"]), set)


def test_flatten():
    assert ex.flatten([[1, 2], [], [3]]) == [1, 2, 3]
    assert ex.flatten([]) == []
    assert ex.flatten([[5]]) == [5]


def test_lazy_squares_is_lazy():
    result = ex.lazy_squares(4)
    assert isinstance(result, types.GeneratorType)  # not a list
    assert list(result) == [0, 1, 4, 9]
    assert list(ex.lazy_squares(0)) == []
    assert next(ex.lazy_squares(10**12)) == 0  # would hang or run out of memory if eager
