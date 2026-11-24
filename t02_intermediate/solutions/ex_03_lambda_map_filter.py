"""Exercise 03: lambda, map, filter, sorted, reduce.

Tasks
1. sort_words: sort by length, then alphabetically, using a key function.
2. top_n_by: pick the n largest dicts by a field.
3. product: multiply numbers with functools.reduce.
4. compose: chain functions left to right (reduce).
5. parse_positive_ints: filter + map pipeline over strings.

Run: uv run pytest t02_intermediate -k lambda
"""

from collections.abc import Callable
from functools import reduce
from typing import Any


def sort_words(words: list[str]) -> list[str]:
    """Sort by length, ties broken alphabetically. Return a new list.

    >>> sort_words(["pear", "fig", "apple", "kiwi"])
    ['fig', 'kiwi', 'pear', 'apple']
    """
    return sorted(words, key=lambda w: (len(w), w))


def top_n_by(items: list[dict[str, Any]], field: str, n: int) -> list[dict[str, Any]]:
    """Return the n items with the largest item[field], largest first.

    >>> top_n_by([{"v": 1}, {"v": 9}, {"v": 5}], "v", 2)
    [{'v': 9}, {'v': 5}]
    """
    return sorted(items, key=lambda item: item[field], reverse=True)[:n]


def product(numbers: list[int]) -> int:
    """Multiply all numbers using functools.reduce. The empty product is 1.

    >>> product([2, 3, 4])
    24
    """
    return reduce(lambda acc, n: acc * n, numbers, 1)


def compose(*funcs: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Return a function that applies funcs left to right. With no funcs it returns its input.

    >>> compose(lambda x: x + 1, lambda x: x * 10)(2)
    30
    """
    return lambda value: reduce(lambda acc, f: f(acc), funcs, value)


def parse_positive_ints(strings: list[str]) -> list[int]:
    """Keep only strings made of digits, convert to int, drop zeros.

    >>> parse_positive_ints(["3", "x", "0", "12", "-4", ""])
    [3, 12]
    """
    return [n for n in map(int, filter(lambda s: s.isdigit(), strings)) if n > 0]
