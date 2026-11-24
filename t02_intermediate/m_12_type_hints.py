# Type Hints
"""
Type hints annotate what a value should be. Python does NOT enforce them at runtime;
tools do: mypy and pyright (also built into editors like VS Code/PyCharm) read the hints
and flag bugs before you run the code. Run e.g. `uv run mypy file.py` or `pyright file.py`.
Syntax (Python 3.10+/3.12+):
    x: int | None          union / optional (instead of Optional[int])
    list[int], dict[str, float]    built-in generics
    Callable[[int], str]   function type
    Literal["r", "w"]      only these exact values
    TypedDict              dict with known string keys
    Protocol               structural typing ("if it has these methods, it fits")
    def first[T](xs: list[T]) -> T        PEP 695 generic function
    class Box[T]: ...                     PEP 695 generic class
    type Alias = ...                      PEP 695 type alias
"""

from collections.abc import Callable, Sequence
from typing import Literal, Protocol, TypedDict


# Example: basics and unions
def greet(name: str, times: int = 1) -> str:
    return " ".join([f"hi {name}"] * times)


def find_user(user_id: int) -> str | None:  # may return None; callers must check
    return {1: "ada"}.get(user_id)


user = find_user(2)
print(user.upper() if user is not None else "not found")  # narrowing with an if

# Example: collections and aliases
type Matrix = list[list[float]]  # PEP 695 type alias
type JSON = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None


def transpose(m: Matrix) -> Matrix:
    return [list(row) for row in zip(*m, strict=True)]


print(transpose([[1, 2], [3, 4]]))


# Example: generic function and class with PEP 695 syntax
def first[T](items: Sequence[T]) -> T:
    return items[0]


class Box[T]:
    def __init__(self, item: T) -> None:
        self.item = item

    def map[U](self, func: Callable[[T], U]) -> Box[U]:
        return Box(func(self.item))


print(first([3, 4]), first("xyz"), Box(5).map(str).map(len).item)


# Bounded type variable: T must be comparable via the given bound
def biggest[T: (int, float)](a: T, b: T) -> T:
    return a if a >= b else b


print(biggest(2, 7), biggest(2.5, 1.5))

# Example: Literal and Callable
Mode = Literal["r", "w"]


def open_mode(mode: Mode) -> str:
    return f"opening in {mode}"


print(open_mode("r"))  # open_mode("x") is flagged by the type checker


def apply_twice(func: Callable[[int], int], value: int) -> int:
    return func(func(value))


print(apply_twice(lambda n: n + 3, 1))


# Example: TypedDict: dict shape known to the type checker
class MovieDict(TypedDict):
    title: str
    year: int


class MovieOptional(MovieDict, total=False):
    rating: float


movie: MovieOptional = {"title": "Alien", "year": 1979}
print(movie["title"], movie.get("rating"))


# Example: Protocol (structural typing, "duck typing with checking")
class SupportsClose(Protocol):
    def close(self) -> None: ...


class Resource:
    def close(self) -> None:  # no inheritance from SupportsClose needed
        print("resource closed")


def shutdown(thing: SupportsClose) -> None:
    thing.close()


shutdown(Resource())


# Runtime wrinkle: hints are stored, not enforced
def add(a: int, b: int) -> int:
    return a + b


print(add("a", "b"))  # works at runtime; mypy/pyright would flag it
print(add.__annotations__)

"""
Common mistakes
- Believing hints are enforced at runtime. Validate untrusted input explicitly
  (or with Pydantic).
- Overusing Any, which switches off checking.
- Using list instead of Sequence for read-only parameters (rejects tuples).
- Mutable default arguments, even when annotated.
- Not checking for None before using an `X | None` value.
- Writing `-> None` functions that actually return a value, or the reverse.
"""

"""
Where this shows up in backend/ML work
- FastAPI reads type hints to parse, validate and document requests automatically
  (dependency injection is driven by annotations).
- Pydantic models are validated type hints.
- Protocols describe pluggable backends (a Storage or LLMClient interface) for tests.
- Type checkers in CI catch None-handling bugs before they hit production.
"""
