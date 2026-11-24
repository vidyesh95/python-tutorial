"""Exercise 01: Protocols, ABCs and Generics (reference solution)."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Protocol


class Notifier(Protocol):
    """Structural type: anything with `send(message) -> bool`."""

    def send(self, message: str) -> bool: ...


def notify_all(notifiers: Iterable[Notifier], message: str) -> int:
    """Send `message` through each notifier; return how many sends returned True."""
    return sum(1 for n in notifiers if n.send(message))


class Plugin(ABC):
    """Abstract plugin with abstract `name` and `run`, and concrete `describe`."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def run(self, data: Any) -> Any: ...

    def describe(self) -> str:
        return f"name: {self.name}"


class Upper(Plugin):
    @property
    def name(self) -> str:
        return "upper"

    def run(self, data: str) -> str:
        return data.upper()


class Reverse(Plugin):
    @property
    def name(self) -> str:
        return "reverse"

    def run(self, data: str) -> str:
        return data[::-1]


class TypedQueue[T]:
    def __init__(self) -> None:
        self._items: list[T] = []

    def put(self, item: T) -> None:
        self._items.append(item)

    def get(self) -> T:
        if not self._items:
            raise IndexError("get from empty queue")
        return self._items.pop(0)

    def __len__(self) -> int:
        return len(self._items)


def max_by[T, K](items: Iterable[T], key: Callable[[T], K]) -> T:
    it = iter(items)
    try:
        best = next(it)
    except StopIteration:
        raise ValueError("max_by() arg is an empty iterable") from None
    best_key = key(best)
    for item in it:
        k = key(item)
        if k > best_key:  # type: ignore[operator]
            best, best_key = item, k
    return best


@dataclass(frozen=True)
class Ok[T]:
    value: T


@dataclass(frozen=True)
class Err:
    reason: str


def safe_div(a: float, b: float) -> Ok[float] | Err:
    if b == 0:
        return Err("division by zero")
    return Ok(a / b)
