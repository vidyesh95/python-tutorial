"""Exercise 01: Comprehensions.

Tasks
1. squares_of_evens: list comprehension with a filter.
2. word_lengths: dict comprehension.
3. unique_first_letters: set comprehension.
4. flatten: nested comprehension over a matrix.
5. lazy_squares: return a generator expression, not a list.

Run: uv run pytest t02_intermediate -k comprehensions
"""

from collections.abc import Iterator


def squares_of_evens(nums: list[int]) -> list[int]:
    """Return the squares of the even numbers, keeping order.

    >>> squares_of_evens([1, 2, 3, 4])
    [4, 16]
    """
    raise NotImplementedError


def word_lengths(words: list[str]) -> dict[str, int]:
    """Map each word to its length. Duplicates collapse into one key.

    >>> word_lengths(["hi", "hello"])
    {'hi': 2, 'hello': 5}
    """
    raise NotImplementedError


def unique_first_letters(words: list[str]) -> set[str]:
    """Return the set of lowercase first letters. Skip empty strings.

    >>> sorted(unique_first_letters(["Apple", "avocado", "Banana", ""]))
    ['a', 'b']
    """
    raise NotImplementedError


def flatten(matrix: list[list[int]]) -> list[int]:
    """Flatten a list of lists one level deep, row by row.

    >>> flatten([[1, 2], [], [3]])
    [1, 2, 3]
    """
    raise NotImplementedError


def lazy_squares(n: int) -> Iterator[int]:
    """Return a LAZY iterator of the squares of 0..n-1 (a generator expression).

    >>> list(lazy_squares(4))
    [0, 1, 4, 9]
    """
    raise NotImplementedError
