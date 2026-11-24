"""Exercise 07 - Conditionals.

Tasks:
1. letter_grade: map a score to a letter with if/elif/else.
2. classify_triangle: equilateral, isosceles, scalene or invalid.
3. is_leap_year: the Gregorian leap-year rule.
4. http_category: classify an HTTP status code using match/case.
5. sign: return -1, 0 or 1 with a conditional expression or if/else.
"""


def letter_grade(score: int) -> str:
    """90+ "A", 80-89 "B", 70-79 "C", 60-69 "D", otherwise "F". Scores outside 0-100 raise ValueError.

    Examples:
        letter_grade(95) -> "A"
        letter_grade(80) -> "B"
        letter_grade(59) -> "F"
        letter_grade(101) -> raises ValueError
    """
    raise NotImplementedError


def classify_triangle(a: float, b: float, c: float) -> str:
    """Return "invalid" (non-positive side or triangle inequality fails), "equilateral",
    "isosceles" or "scalene".

    Examples:
        classify_triangle(3, 3, 3) -> "equilateral"
        classify_triangle(3, 3, 5) -> "isosceles"
        classify_triangle(3, 4, 5) -> "scalene"
        classify_triangle(1, 2, 3) -> "invalid"
    """
    raise NotImplementedError


def is_leap_year(year: int) -> bool:
    """Divisible by 4, except centuries, unless divisible by 400.

    Examples:
        is_leap_year(2024) -> True
        is_leap_year(1900) -> False
        is_leap_year(2000) -> True
        is_leap_year(2023) -> False
    """
    raise NotImplementedError


def http_category(code: int) -> str:
    """Use match/case: 1xx "informational", 2xx "success", 3xx "redirect", 4xx "client error",
    5xx "server error", anything else "unknown".

    Examples:
        http_category(200) -> "success"
        http_category(404) -> "client error"
        http_category(503) -> "server error"
        http_category(99) -> "unknown"
    """
    raise NotImplementedError


def sign(n: float) -> int:
    """Return -1 for negatives, 0 for zero and 1 for positives.

    Examples:
        sign(-5) -> -1
        sign(0) -> 0
        sign(2.5) -> 1
    """
    raise NotImplementedError
