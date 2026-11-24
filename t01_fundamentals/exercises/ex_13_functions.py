"""Exercise 13 - Functions.

Tasks:
1. power: default argument.
2. clamp: keep a value inside [low, high].
3. join_words: *args and a keyword-only separator.
4. build_user: **kwargs merged into a dict.
5. fibonacci: return the first n Fibonacci numbers.
"""


def power(base: float, exponent: float = 2) -> float:
    """Return ``base ** exponent``; the exponent defaults to 2.

    Examples:
        power(3) -> 9
        power(2, 10) -> 1024
        power(exponent=3, base=2) -> 8
    """
    raise NotImplementedError


def clamp(value: float, low: float = 0, high: float = 1) -> float:
    """Limit ``value`` to the range ``low..high``. Raise ValueError if low > high.

    Examples:
        clamp(5, 0, 3) -> 3
        clamp(-2) -> 0
        clamp(0.4) -> 0.4
        clamp(1, 5, 2) -> raises ValueError
    """
    raise NotImplementedError


def join_words(*words: str, sep: str = " ") -> str:
    """Join any number of words with ``sep`` (keyword-only).

    Examples:
        join_words("a", "b", "c") -> "a b c"
        join_words("a", "b", sep="-") -> "a-b"
        join_words() -> ""
    """
    raise NotImplementedError


def build_user(name: str, **extra: object) -> dict[str, object]:
    """Return ``{"name": name, **extra}``.

    Examples:
        build_user("Ada") -> {"name": "Ada"}
        build_user("Ada", age=36, city="London") -> {"name": "Ada", "age": 36, "city": "London"}
    """
    raise NotImplementedError


def fibonacci(n: int) -> list[int]:
    """Return the first ``n`` Fibonacci numbers starting 0, 1. ``n`` must be >= 0.

    Examples:
        fibonacci(0) -> []
        fibonacci(1) -> [0]
        fibonacci(7) -> [0, 1, 1, 2, 3, 5, 8]
        fibonacci(-1) -> raises ValueError
    """
    raise NotImplementedError
