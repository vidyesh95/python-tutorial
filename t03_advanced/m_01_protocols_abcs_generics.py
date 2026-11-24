# Protocols, ABCs and Generics
"""
Python has two ways to describe "what an object can do":
- NOMINAL typing (abc.ABC): a class must explicitly inherit the base to count.
- STRUCTURAL typing (typing.Protocol): any class with the right methods counts
  ("duck typing, but checkable by mypy/pyright").
Generics let one class or function work over many types while keeping them linked:
    def first[T](items: list[T]) -> T      # PEP 695 syntax (3.12+): no TypeVar needed
Rules of thumb:
- Use a Protocol for "what I need from the caller" (small, consumer-defined).
- Use an ABC when you own the hierarchy and want shared code + enforced overrides.
- Type checkers (mypy, pyright) read these annotations; Python itself ignores them
  at runtime, except for @runtime_checkable isinstance checks and ABC abstractmethods.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


# Example: a Protocol (structural). Neither class below inherits from it.
@runtime_checkable
class SupportsClose(Protocol):
    def close(self) -> None: ...


class Connection:
    def close(self) -> None:
        print("connection closed")


class Temp:  # no close() method
    pass


def shutdown(resource: SupportsClose) -> None:
    resource.close()


shutdown(Connection())
# runtime_checkable only checks that the method NAMES exist, not their signatures
print(isinstance(Connection(), SupportsClose), isinstance(Temp(), SupportsClose))


# Example: a Protocol with an attribute and a method (what a "Shape" needs)
class Shape(Protocol):
    name: str

    def area(self) -> float: ...


@dataclass
class Square:
    side: float
    name: str = "square"

    def area(self) -> float:
        return self.side**2


@dataclass
class Circle:
    r: float
    name: str = "circle"

    def area(self) -> float:
        return 3.14159 * self.r**2


def total_area(shapes: Iterable[Shape]) -> float:
    return sum(s.area() for s in shapes)


print("total area:", round(total_area([Square(2), Circle(1)]), 2))


# Example: an ABC (nominal): shared code + enforced abstract methods
class Storage(ABC):
    @abstractmethod
    def read(self, key: str) -> str: ...

    @abstractmethod
    def write(self, key: str, value: str) -> None: ...

    def copy(self, src: str, dst: str) -> None:  # concrete method built on abstract ones
        self.write(dst, self.read(src))


class MemoryStorage(Storage):
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def read(self, key: str) -> str:
        return self._data[key]

    def write(self, key: str, value: str) -> None:
        self._data[key] = value


try:
    Storage()  # type: ignore[abstract]
except TypeError as exc:
    print("cannot instantiate ABC:", exc)

store = MemoryStorage()
store.write("a", "hello")
store.copy("a", "b")
print("copied:", store.read("b"))


# Example: generic class with PEP 695 syntax; T is tracked by the type checker
class Stack[T]:
    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        if not self._items:
            raise IndexError("pop from empty stack")
        return self._items.pop()

    def __iter__(self) -> Iterator[T]:
        return reversed(self._items)


ints = Stack[int]()
ints.push(1)
ints.push(2)
print("popped:", ints.pop(), "rest:", list(ints))


# Example: generic functions, with a bound (T must have __lt__ via a Protocol)
class Comparable(Protocol):
    def __lt__(self, other, /) -> bool: ...


def biggest[T: Comparable](items: Iterable[T]) -> T:
    it = iter(items)
    best = next(it)  # raises StopIteration if empty; real code would check
    for x in it:
        if best < x:
            best = x
    return best


print(biggest([3, 9, 2]), biggest(["pear", "apple"]))


# Example: a generic Repository protocol (shows up everywhere in backend code)
class Repository[K, V](Protocol):
    def get(self, key: K) -> V | None: ...
    def add(self, key: K, value: V) -> None: ...


class DictRepo[K, V]:
    def __init__(self) -> None:
        self._d: dict[K, V] = {}

    def get(self, key: K) -> V | None:
        return self._d.get(key)

    def add(self, key: K, value: V) -> None:
        self._d[key] = value


def seed(repo: Repository[int, str]) -> None:
    repo.add(1, "ada")


repo = DictRepo[int, str]()
seed(repo)
print("repo.get(1):", repo.get(1))

# Type aliases also use PEP 695: `type Json = dict[str, "Json"] | list["Json"] | str | int | None`
type Pair[T] = tuple[T, T]
swap_demo: Pair[int] = (1, 2)
print("pair:", swap_demo)

"""
Common mistakes
- Expecting Python to enforce annotations at runtime. Run `uv run mypy` or `pyright` for that.
- Using isinstance with a non-@runtime_checkable Protocol (TypeError), or trusting
  runtime_checkable to verify signatures (it only checks names).
- Making Protocols huge. Small, one-purpose protocols (SupportsClose) compose better.
- Inheriting from an ABC just to "tag" a class. If you only need a shape, use a Protocol.
- Forgetting that list[Dog] is NOT a list[Animal] (generics are invariant by default).

Where this shows up in backend/ML/robotics work
- Backend: repository/service interfaces, FastAPI dependencies typed as Protocols so tests
  can pass fakes; generic response wrappers like Page[T].
- ML: plugin-style Dataset / Transform / Metric interfaces; Generic containers for batches.
- Robotics: Sensor / Controller protocols so simulated and real hardware are interchangeable.
"""
