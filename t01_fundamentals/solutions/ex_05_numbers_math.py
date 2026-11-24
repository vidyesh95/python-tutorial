"""Exercise 05 - Numbers and math.

Tasks:
1. is_prime: primality test.
2. digit_sum: sum of the digits of an integer (ignore the sign).
3. hypotenuse: length of the hypotenuse of a right triangle.
4. round_half_up: round the way people expect (2.5 -> 3), not banker's rounding.
"""

import math
from decimal import ROUND_HALF_UP, Decimal


def is_prime(n: int) -> bool:
    """Return True if ``n`` is a prime number.

    Examples:
        is_prime(2) -> True
        is_prime(15) -> False
        is_prime(1) -> False
        is_prime(-7) -> False
    """
    if n < 2:
        return False
    return all(n % d != 0 for d in range(2, math.isqrt(n) + 1))


def digit_sum(n: int) -> int:
    """Return the sum of the decimal digits of ``abs(n)``.

    Examples:
        digit_sum(123) -> 6
        digit_sum(-45) -> 9
        digit_sum(0) -> 0
    """
    return sum(int(ch) for ch in str(abs(n)))


def hypotenuse(a: float, b: float) -> float:
    """Return ``sqrt(a**2 + b**2)``.

    Examples:
        hypotenuse(3, 4) -> 5.0
        hypotenuse(0, 2) -> 2.0
    """
    return math.hypot(a, b)


def round_half_up(x: float, ndigits: int = 0) -> float:
    """Round ``x`` to ``ndigits`` decimals, rounding halves AWAY from zero.

    Hint: the decimal module's ROUND_HALF_UP; build the Decimal from ``str(x)``.

    Examples:
        round_half_up(2.5) -> 3.0
        round_half_up(2.675, 2) -> 2.68
        round_half_up(-2.5) -> -3.0
        round_half_up(3.14159, 3) -> 3.142
    """
    quantum = Decimal(1).scaleb(-ndigits)
    return float(Decimal(str(x)).quantize(quantum, rounding=ROUND_HALF_UP))
