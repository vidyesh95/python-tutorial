"""Exercise 14 - Scope and closures.

Tasks:
1. make_counter: a function factory whose returned function counts up (nonlocal).
2. make_multiplier: closure remembering a factor.
3. make_accumulator: closure returning the running total.
4. compose: combine two functions into one.
5. make_adders: list of closures, each adding a different number (watch late binding!).
"""

from collections.abc import Callable


def make_counter(start: int = 0) -> Callable[[], int]:
    """Return a function that, on each call, increases an internal count and returns it.
    The first call returns ``start + 1``. Separate counters must be independent.

    Examples:
        c = make_counter(); c(), c() -> 1, 2
        d = make_counter(10); d() -> 11
    """
    raise NotImplementedError


def make_multiplier(factor: float) -> Callable[[float], float]:
    """Return a function that multiplies its argument by ``factor``.

    Examples:
        make_multiplier(3)(4) -> 12
        make_multiplier(0.5)(10) -> 5.0
    """
    raise NotImplementedError


def make_accumulator() -> Callable[[float], float]:
    """Return a function ``add(n)`` that adds ``n`` to a running total and returns the total.

    Examples:
        acc = make_accumulator(); acc(5) -> 5; acc(10) -> 15; acc(-3) -> 12
    """
    raise NotImplementedError


def compose(f: Callable, g: Callable) -> Callable:
    """Return a function equivalent to ``lambda x: f(g(x))``.

    Examples:
        compose(str.upper, str.strip)("  hi ") -> "HI"
        compose(len, str)(12345) -> 5
    """
    raise NotImplementedError


def make_adders(numbers: list[int]) -> list[Callable[[int], int]]:
    """Return one function per number; the function at index i adds ``numbers[i]`` to its argument.

    Examples:
        [f(10) for f in make_adders([1, 2, 3])] -> [11, 12, 13]
        make_adders([]) -> []
    """
    raise NotImplementedError
