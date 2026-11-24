"""Exercise 03 - Operators.

Tasks:
1. is_even: use the modulus operator.
2. apply_discount: reduce a price by a percentage, rounded to 2 decimals.
3. in_range: inclusive range check using a chained comparison.
4. has_flag: test whether a bit is set in an integer using bitwise operators.
5. fizzbuzz_word: classic FizzBuzz for one number.
"""


def is_even(n: int) -> bool:
    """Return True when ``n`` is even.

    Examples:
        is_even(4) -> True
        is_even(7) -> False
        is_even(-2) -> True
        is_even(0) -> True
    """
    return n % 2 == 0


def apply_discount(price: float, percent: float) -> float:
    """Return ``price`` reduced by ``percent`` percent, rounded to 2 decimals.

    Examples:
        apply_discount(100, 20) -> 80.0
        apply_discount(19.99, 10) -> 17.99
        apply_discount(50, 0) -> 50.0
    """
    return round(price * (1 - percent / 100), 2)


def in_range(x: float, low: float, high: float) -> bool:
    """Return True if ``low <= x <= high``.

    Examples:
        in_range(5, 1, 10) -> True
        in_range(10, 1, 10) -> True
        in_range(11, 1, 10) -> False
    """
    return low <= x <= high


def has_flag(flags: int, bit: int) -> bool:
    """Return True if bit number ``bit`` (0 = least significant) is set in ``flags``.

    Examples:
        has_flag(0b0101, 0) -> True
        has_flag(0b0101, 1) -> False
        has_flag(0b0101, 2) -> True
    """
    return flags & (1 << bit) != 0


def fizzbuzz_word(n: int) -> str:
    """Return "FizzBuzz" for multiples of 15, "Fizz" for 3, "Buzz" for 5, otherwise ``str(n)``.

    Examples:
        fizzbuzz_word(3) -> "Fizz"
        fizzbuzz_word(10) -> "Buzz"
        fizzbuzz_word(30) -> "FizzBuzz"
        fizzbuzz_word(7) -> "7"
    """
    if n % 15 == 0:
        return "FizzBuzz"
    if n % 3 == 0:
        return "Fizz"
    if n % 5 == 0:
        return "Buzz"
    return str(n)
