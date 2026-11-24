"""Exercise 01: Protocols, ABCs and Generics.

Tasks
1. Notifier: a Protocol with `send(self, message: str) -> bool`, and `notify_all`
   that calls every notifier and returns how many returned True.
2. Plugin: an ABC with abstract `name` (property) and `run(data)`, and a concrete
   `describe()` method returning 'name: <name>'. Then implement `Upper` and `Reverse`.
3. TypedQueue[T]: a generic FIFO queue with put/get/__len__; get() on empty raises IndexError.
4. max_by[T, K]: a generic function returning the item with the largest key(item).
5. Result types: `Ok[T]` and `Err` dataclasses plus `safe_div` returning Ok/Err.

Run: uv run pytest t03_advanced -k protocols
"""

from abc import ABC
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol


class Notifier(Protocol):
    """Structural type: anything with `send(message) -> bool`."""

    def send(self, message: str) -> bool: ...


def notify_all(notifiers: Iterable[Notifier], message: str) -> int:
    """Send `message` through each notifier; return how many sends returned True."""
    raise NotImplementedError


class Plugin(ABC):  # noqa: B024
    """Abstract plugin. Subclasses MUST define `name` (property) and `run(data)`.

    Add the abstract members, plus a concrete `describe()` -> 'name: <name>'.
    Instantiating Plugin (or a subclass missing members) must raise TypeError.
    (Delete the placeholder __init__ below once you add the abstract members.)
    """

    def __init__(self) -> None:
        raise NotImplementedError

    def describe(self) -> str:
        raise NotImplementedError


class Upper(Plugin):
    """name == 'upper'; run(text) -> text.upper()"""

    def __init__(self) -> None:
        raise NotImplementedError


class Reverse(Plugin):
    """name == 'reverse'; run(text) -> text[::-1]"""

    def __init__(self) -> None:
        raise NotImplementedError


class TypedQueue[T]:
    """FIFO queue. put(item), get() -> oldest item (IndexError if empty), len(q)."""

    def __init__(self) -> None:
        raise NotImplementedError

    def put(self, item: T) -> None:
        raise NotImplementedError

    def get(self) -> T:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError


def max_by[T, K](items: Iterable[T], key: Callable[[T], K]) -> T:
    """Return the item with the largest key. Raise ValueError on empty input."""
    raise NotImplementedError


@dataclass(frozen=True)
class Ok[T]:
    value: T


@dataclass(frozen=True)
class Err:
    reason: str


def safe_div(a: float, b: float) -> Ok[float] | Err:
    """Ok(a / b), or Err('division by zero') when b == 0."""
    raise NotImplementedError
