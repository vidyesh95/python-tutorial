"""Exercise 09: Iterators and generators.

Tasks
1. countdown: a simple generator.
2. chunked: lazily split an iterable into lists of a given size.
3. Fibonacci: an iterator CLASS (implement __iter__ and __next__).
4. deep_flatten: recursive generator with yield from.
5. parse_numbers: a lazy pipeline stage over lines of text.

Run: uv run pytest t02_intermediate -k iterators
"""

from collections.abc import Iterable, Iterator
from itertools import islice
from typing import Any


def countdown(n: int) -> Iterator[int]:
    """Yield n, n-1, ..., 1. Yield nothing for n <= 0.

    >>> list(countdown(3))
    [3, 2, 1]
    """
    while n > 0:
        yield n
        n -= 1


def chunked(items: Iterable[Any], size: int) -> Iterator[list[Any]]:
    """Yield successive lists of up to `size` items. Raise ValueError if size < 1.

    >>> list(chunked([1, 2, 3, 4, 5], 2))
    [[1, 2], [3, 4], [5]]
    """
    if size < 1:
        raise ValueError("size must be >= 1")
    it = iter(items)
    while chunk := list(islice(it, size)):
        yield chunk


class Fibonacci:
    """Iterator over the first `count` Fibonacci numbers: 0, 1, 1, 2, 3, ..."""

    def __init__(self, count: int) -> None:
        self.count = count
        self._produced = 0
        self._a, self._b = 0, 1

    def __iter__(self) -> "Fibonacci":
        """An iterator returns itself."""
        return self

    def __next__(self) -> int:
        """Return the next number or raise StopIteration when `count` have been produced."""
        if self._produced >= self.count:
            raise StopIteration
        value = self._a
        self._a, self._b = self._b, self._a + self._b
        self._produced += 1
        return value


def deep_flatten(nested: Iterable[Any]) -> Iterator[Any]:
    """Yield all non-list leaves of arbitrarily nested lists/tuples (use yield from).

    Strings are leaves, they must not be split into characters.

    >>> list(deep_flatten([1, [2, [3, "ab"]], (4,)]))
    [1, 2, 3, 'ab', 4]
    """
    for item in nested:
        if isinstance(item, list | tuple):
            yield from deep_flatten(item)
        else:
            yield item


def parse_numbers(lines: Iterable[str]) -> Iterator[int]:
    """Lazily yield ints from lines. Skip blank lines and lines starting with '#'.

    Must not consume more of `lines` than needed (it is a generator).

    >>> list(parse_numbers(["1", "", "# note", " 2 "]))
    [1, 2]
    """
    for line in lines:
        text = line.strip()
        if text and not text.startswith("#"):
            yield int(text)
