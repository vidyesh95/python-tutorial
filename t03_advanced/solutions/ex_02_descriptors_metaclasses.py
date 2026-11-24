"""Exercise 02: Descriptors and Metaclasses (reference solution)."""

from typing import Any


class Bounded:
    def __init__(self, low: float, high: float) -> None:
        self.low = low
        self.high = high

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        self.private = f"_{name}"

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        if obj is None:
            return self
        return obj.__dict__[self.private]

    def __set__(self, obj: Any, value: float) -> None:
        if not self.low <= value <= self.high:
            raise ValueError(f"{self.name} must be between {self.low} and {self.high}")
        obj.__dict__[self.private] = value


class ReadOnly:
    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        self.private = f"_{name}"

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        if obj is None:
            return self
        return obj.__dict__[self.private]

    def __set__(self, obj: Any, value: Any) -> None:
        if self.private in obj.__dict__:
            raise AttributeError(f"{self.name} is read-only")
        obj.__dict__[self.private] = value


class CountedAccess:
    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        self.private = f"_{name}"
        self.counter = f"_reads_{name}"

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        if obj is None:
            return self
        obj.__dict__[self.counter] = obj.__dict__.get(self.counter, 0) + 1
        return obj.__dict__[self.private]

    def __set__(self, obj: Any, value: Any) -> None:
        obj.__dict__[self.private] = value

    def reads(self, obj: Any) -> int:
        return obj.__dict__.get(self.counter, 0)


class Command:
    registry: dict[str, type[Command]] = {}

    def __init_subclass__(cls, /, name: str | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        Command.registry[name or cls.__name__.lower()] = cls


class SingletonMeta(type):
    _instances: dict[type, Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in SingletonMeta._instances:
            SingletonMeta._instances[cls] = super().__call__(*args, **kwargs)
        return SingletonMeta._instances[cls]
