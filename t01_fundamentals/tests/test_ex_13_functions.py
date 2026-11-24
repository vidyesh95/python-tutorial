import pytest

from _loader import load

ex = load("t01_fundamentals", "ex_13_functions")


def test_power():
    assert ex.power(3) == 9
    assert ex.power(2, 10) == 1024
    assert ex.power(exponent=3, base=2) == 8


def test_clamp():
    assert ex.clamp(5, 0, 3) == 3
    assert ex.clamp(-2) == 0
    assert ex.clamp(0.4) == 0.4
    assert ex.clamp(2, 5, 8) == 5
    with pytest.raises(ValueError):
        ex.clamp(1, 5, 2)


def test_join_words():
    assert ex.join_words("a", "b", "c") == "a b c"
    assert ex.join_words("a", "b", sep="-") == "a-b"
    assert ex.join_words() == ""


def test_join_words_sep_is_keyword_only():
    assert ex.join_words("a", "b", "-") == "a b -"  # a third positional is just another word


def test_build_user():
    assert ex.build_user("Ada") == {"name": "Ada"}
    assert ex.build_user("Ada", age=36, city="London") == {
        "name": "Ada",
        "age": 36,
        "city": "London",
    }


def test_fibonacci():
    assert ex.fibonacci(0) == []
    assert ex.fibonacci(1) == [0]
    assert ex.fibonacci(7) == [0, 1, 1, 2, 3, 5, 8]
    with pytest.raises(ValueError):
        ex.fibonacci(-1)
