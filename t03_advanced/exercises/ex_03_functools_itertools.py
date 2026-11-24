"""Exercise 03: functools and itertools.

Tasks
1. chunked: split an iterable into lists of size n (last may be shorter); lazy generator.
2. moving_average: moving average over a sliding window (pairwise-style), returns a list.
3. make_multiplier: use functools.partial to build a function that multiplies by a factor.
4. describe: a singledispatch function: int -> 'int:<v>', str -> 'str:<v>',
   list -> 'list of <n>', everything else -> 'other'.
5. run_length_encode: [(item, count), ...] using itertools.groupby.

Run: uv run pytest t03_advanced -k functools
"""

from collections.abc import Callable, Iterable, Iterator
from typing import Any


def chunked[T](items: Iterable[T], n: int) -> Iterator[list[T]]:
    """Yield lists of up to n items. Raise ValueError if n < 1. Must be lazy (a generator)."""
    raise NotImplementedError


def moving_average(values: Iterable[float], window: int) -> list[float]:
    """Average of each full window; [] if fewer than `window` values. window >= 1."""
    raise NotImplementedError


def make_multiplier(factor: float) -> Callable[[float], float]:
    """Return a function x -> x * factor, built with functools.partial and operator.mul."""
    raise NotImplementedError


def describe(value: Any) -> str:
    """Make this a functools.singledispatch function (register int, str, list)."""
    raise NotImplementedError


def run_length_encode(items: Iterable[Any]) -> list[tuple[Any, int]]:
    """'aaabcc' -> [('a', 3), ('b', 1), ('c', 2)] using itertools.groupby."""
    raise NotImplementedError
