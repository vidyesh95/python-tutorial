import math

import pytest

from _loader import load

ex = load("t01_fundamentals", "ex_05_numbers_math")


def test_is_prime():
    assert ex.is_prime(2) is True
    assert ex.is_prime(97) is True
    assert ex.is_prime(15) is False
    assert ex.is_prime(1) is False
    assert ex.is_prime(0) is False
    assert ex.is_prime(-7) is False


def test_digit_sum():
    assert ex.digit_sum(123) == 6
    assert ex.digit_sum(-45) == 9
    assert ex.digit_sum(0) == 0


def test_hypotenuse():
    assert ex.hypotenuse(3, 4) == 5.0
    assert ex.hypotenuse(0, 2) == 2.0
    assert ex.hypotenuse(1, 1) == pytest.approx(math.sqrt(2))


def test_round_half_up():
    assert ex.round_half_up(2.5) == 3.0
    assert ex.round_half_up(3.5) == 4.0
    assert ex.round_half_up(2.675, 2) == 2.68
    assert ex.round_half_up(-2.5) == -3.0
    assert ex.round_half_up(3.14159, 3) == 3.142
