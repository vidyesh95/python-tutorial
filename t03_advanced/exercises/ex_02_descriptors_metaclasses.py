"""Exercise 02: Descriptors and Metaclasses.

Tasks
1. Bounded: a data descriptor enforcing `low <= value <= high` (ValueError otherwise),
   storing values per instance and using __set_name__ for the attribute name.
2. ReadOnly: a descriptor that can be set once in __init__ but never changed after
   (a second assignment raises AttributeError).
3. CountedAccess: a descriptor wrapper that counts how many times the attribute was read,
   stored per instance in `obj.__dict__['_reads_<name>']`.
4. Registry via __init_subclass__: `Command` subclasses register under `Command.registry`
   by their `name` class keyword (default: lowercase class name).
5. SingletonMeta: a metaclass making every class that uses it a singleton.

Run: uv run pytest t03_advanced -k descriptors
"""

from typing import Any


class Bounded:
    """Data descriptor: Bounded(low, high). Out-of-range sets raise ValueError.

    Accessing via the class (obj is None) returns the descriptor itself.
    """

    def __init__(self, low: float, high: float) -> None:
        raise NotImplementedError

    def __set_name__(self, owner: type, name: str) -> None:
        raise NotImplementedError

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        raise NotImplementedError

    def __set__(self, obj: Any, value: float) -> None:
        raise NotImplementedError


class ReadOnly:
    """Data descriptor: first assignment per instance works, later ones raise AttributeError."""

    def __set_name__(self, owner: type, name: str) -> None:
        raise NotImplementedError

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        raise NotImplementedError

    def __set__(self, obj: Any, value: Any) -> None:
        raise NotImplementedError


class CountedAccess:
    """Descriptor that stores a value like a normal attribute and counts reads.

    The read count lives in `obj.__dict__['_reads_<name>']`; use `reads(obj)` to get it.
    """

    def __set_name__(self, owner: type, name: str) -> None:
        raise NotImplementedError

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        raise NotImplementedError

    def __set__(self, obj: Any, value: Any) -> None:
        raise NotImplementedError

    def reads(self, obj: Any) -> int:
        raise NotImplementedError


class Command:
    """Base class; subclasses auto-register in `Command.registry` (name -> class).

    `class Run(Command): ...` registers as 'run'; `class X(Command, name='go')` as 'go'.
    Implement __init_subclass__.
    """

    registry: dict[str, type[Command]] = {}

    def __init_subclass__(cls, /, name: str | None = None, **kwargs: Any) -> None:
        raise NotImplementedError


class SingletonMeta(type):
    """Metaclass: calling the class always returns the same instance (per class)."""

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError
