# Dunder (Magic) Methods
"""
Dunder methods ("double underscore") let your objects plug into Python syntax:
    __repr__ / __str__   -> repr(obj) / str(obj) / print(obj)
    __eq__, __lt__       -> ==, <  (use functools.total_ordering for the rest)
    __hash__             -> hash(obj); needed for dict keys and set members
    __len__              -> len(obj)
    __iter__ / __getitem__ -> for-loops, indexing, slicing, `in`
    __add__              -> obj + other
    __bool__, __contains__, __call__, __enter__ ... (many more)
Python calls them for you; you rarely call them directly.
"""

from collections.abc import Iterator
from functools import total_ordering


# Example: a Vector that supports many operators
@total_ordering  # fills in <=, >, >= from __eq__ and __lt__
class Vector:
    def __init__(self, *components: float) -> None:
        self._data = tuple(components)

    def __repr__(self) -> str:  # unambiguous, for developers
        return f"Vector{self._data}"

    def __str__(self) -> str:  # friendly, for users
        return "<" + ", ".join(str(c) for c in self._data) + ">"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector):
            return NotImplemented  # let Python try the reflected operation
        return self._data == other._data

    def __lt__(self, other: Vector) -> bool:
        return abs(self) < abs(other)

    def __hash__(self) -> int:  # must agree with __eq__
        return hash(self._data)

    def __abs__(self) -> float:
        return sum(c * c for c in self._data) ** 0.5

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[float]:
        return iter(self._data)

    def __getitem__(self, index: int | slice) -> float | tuple[float, ...]:
        return self._data[index]

    def __add__(self, other: Vector) -> Vector:
        return Vector(*(a + b for a, b in zip(self, other, strict=True)))

    def __mul__(self, scalar: float) -> Vector:
        return Vector(*(c * scalar for c in self))

    __rmul__ = __mul__  # makes 3 * v work too

    def __bool__(self) -> bool:
        return any(self._data)


v, w = Vector(3, 4), Vector(1, 2)
print(repr(v), str(v), f"{v}")
print("add:", v + w, "scale:", v * 2, 2 * v)
print("len:", len(v), "index:", v[0], "slice:", v[0:1], "iter:", list(v))
print("abs:", abs(v), "eq:", v == Vector(3, 4), "ne:", v != w)
print("order:", w < v, w <= v, v > w, sorted([v, w]))
print("truthy:", bool(Vector(0, 0)), bool(v))

# Hashable objects work in sets and as dict keys
print(len({Vector(1, 2), Vector(1, 2), Vector(2, 1)}))
print("unpack:", *v)  # works because of __iter__


# Example: __getitem__ alone makes an object iterable and indexable
class Countdown:
    def __init__(self, start: int) -> None:
        self.start = start

    def __len__(self) -> int:
        return self.start

    def __getitem__(self, i: int) -> int:
        if not 0 <= i < self.start:
            raise IndexError(i)  # signals the end of iteration
        return self.start - i


print(list(Countdown(3)), 2 in Countdown(3))


# Example: __call__ makes instances callable
class Multiplier:
    def __init__(self, factor: int) -> None:
        self.factor = factor

    def __call__(self, x: int) -> int:
        return x * self.factor


print(Multiplier(3)(7))

"""
Common mistakes
- Defining __eq__ without __hash__: Python sets __hash__ to None, so instances
  become unhashable. Define both, based on the same immutable fields.
- Returning False instead of NotImplemented from __eq__ for unknown types.
- Mutating fields used in __hash__ while the object lives in a set or dict.
- __repr__ that is not helpful. Aim for something you could paste back as code.
- Making __lt__ inconsistent with __eq__, which gives surprising sort results.
"""

"""
Where this shows up in backend/ML work
- Tensors/arrays (numpy, torch) overload +, *, @, [] using exactly these hooks.
- ORM models and Pydantic models define __eq__, __repr__ and __iter__.
- Value objects (Money, UserId) with __eq__/__hash__ are safe as dict keys and cache keys.
- Callable objects (__call__) implement stateful middleware and model wrappers.
"""
