import pytest

from _loader import load

ex = load("t01_fundamentals", "ex_07_conditionals")


def test_letter_grade():
    assert ex.letter_grade(95) == "A"
    assert ex.letter_grade(90) == "A"
    assert ex.letter_grade(80) == "B"
    assert ex.letter_grade(79) == "C"
    assert ex.letter_grade(60) == "D"
    assert ex.letter_grade(59) == "F"
    assert ex.letter_grade(0) == "F"


def test_letter_grade_out_of_range():
    with pytest.raises(ValueError):
        ex.letter_grade(101)
    with pytest.raises(ValueError):
        ex.letter_grade(-1)


def test_classify_triangle():
    assert ex.classify_triangle(3, 3, 3) == "equilateral"
    assert ex.classify_triangle(3, 3, 5) == "isosceles"
    assert ex.classify_triangle(5, 3, 3) == "isosceles"
    assert ex.classify_triangle(3, 4, 5) == "scalene"
    assert ex.classify_triangle(1, 2, 3) == "invalid"
    assert ex.classify_triangle(0, 1, 1) == "invalid"


def test_is_leap_year():
    assert ex.is_leap_year(2024) is True
    assert ex.is_leap_year(1900) is False
    assert ex.is_leap_year(2000) is True
    assert ex.is_leap_year(2023) is False


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (100, "informational"),
        (200, "success"),
        (302, "redirect"),
        (404, "client error"),
        (503, "server error"),
        (99, "unknown"),
        (600, "unknown"),
    ],
)
def test_http_category(code, expected):
    assert ex.http_category(code) == expected


def test_sign():
    assert ex.sign(-5) == -1
    assert ex.sign(0) == 0
    assert ex.sign(2.5) == 1
