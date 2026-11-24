"""Exercise 12: Type hints.

Tasks
1. first: a generic function (PEP 695) with an optional default.
2. Box[T]: a generic class.
3. make_user / is_adult: TypedDict.
4. greet_all: a Protocol (structural typing).
5. apply_n: Callable types.

Hints are not enforced at runtime, but keep them accurate; check with pyright or mypy.

Run: uv run pytest t02_intermediate -k type_hints
"""

from collections.abc import Callable, Iterable, Sequence
from typing import Protocol, TypedDict


def first[T](items: Sequence[T], default: T | None = None) -> T | None:
    """Return the first item, or `default` when items is empty.

    >>> first([3, 4]), first([], default=0)
    (3, 0)
    """
    raise NotImplementedError


class Box[T]:
    """Holds one value of type T."""

    def __init__(self, item: T) -> None:
        raise NotImplementedError

    def map[U](self, func: Callable[[T], U]) -> Box[U]:
        """Return a new Box containing func(item).

        >>> Box(3).map(str).item
        '3'
        """
        raise NotImplementedError

    def get_or(self, fallback: T) -> T:
        """Return item unless it is None, in which case return fallback."""
        raise NotImplementedError


class User(TypedDict):
    """A user record."""

    name: str
    age: int


def make_user(name: str, age: int) -> User:
    """Build a User dict. Raise ValueError if age is negative."""
    raise NotImplementedError


def is_adult(user: User) -> bool:
    """True when age >= 18."""
    raise NotImplementedError


class Greeter(Protocol):
    """Anything with a greet() -> str method fits; no inheritance needed."""

    def greet(self) -> str: ...


def greet_all(greeters: Iterable[Greeter]) -> list[str]:
    """Call greet() on each object and collect the results."""
    raise NotImplementedError


def apply_n(func: Callable[[int], int], value: int, n: int) -> int:
    """Apply func to value n times. n == 0 returns value. Raise ValueError if n < 0.

    >>> apply_n(lambda x: x * 2, 1, 3)
    8
    """
    raise NotImplementedError
