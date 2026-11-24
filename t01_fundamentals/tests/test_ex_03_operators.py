import pytest

from _loader import load

ex = load("t01_fundamentals", "ex_03_operators")


def test_is_even():
    assert ex.is_even(4) is True
    assert ex.is_even(7) is False
    assert ex.is_even(-2) is True
    assert ex.is_even(0) is True


def test_apply_discount():
    assert ex.apply_discount(100, 20) == 80.0
    assert ex.apply_discount(19.99, 10) == 17.99
    assert ex.apply_discount(50, 0) == 50.0
    assert ex.apply_discount(50, 100) == 0.0


def test_in_range():
    assert ex.in_range(5, 1, 10) is True
    assert ex.in_range(1, 1, 10) is True
    assert ex.in_range(10, 1, 10) is True
    assert ex.in_range(11, 1, 10) is False
    assert ex.in_range(0.5, 1, 10) is False


def test_has_flag():
    assert ex.has_flag(0b0101, 0) is True
    assert ex.has_flag(0b0101, 1) is False
    assert ex.has_flag(0b0101, 2) is True
    assert ex.has_flag(0, 5) is False


@pytest.mark.parametrize(
    ("n", "expected"),
    [(3, "Fizz"), (10, "Buzz"), (30, "FizzBuzz"), (7, "7"), (1, "1"), (15, "FizzBuzz")],
)
def test_fizzbuzz_word(n, expected):
    assert ex.fizzbuzz_word(n) == expected
