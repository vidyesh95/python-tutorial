"""Exercise 09: Design patterns, the Pythonic way.

Tasks
1. apply_strategy: pick a pricing strategy by name from a dict of callables.
2. Registry: a class-based factory with a `register` decorator and `create`.
3. EventEmitter: observer pattern with `on` (returns an unsubscribe function) and `emit`.
4. CelsiusAdapter: adapt an object exposing `read_fahrenheit()` to `read_celsius()`.
5. NotificationService: dependency injection (a sender callable passed in).

Run: uv run pytest t03_advanced -k design_patterns
"""

from collections import defaultdict
from collections.abc import Callable
from typing import Any

STRATEGIES: dict[str, Callable[[float], float]] = {
    "none": lambda p: p,
    "half": lambda p: p / 2,
    "minus10": lambda p: p - 10,
}


def apply_strategy(name: str, price: float) -> float:
    """Look up `name` in STRATEGIES and apply it to `price`.

    Raise ValueError (mentioning the name) for an unknown strategy.
    """
    try:
        return STRATEGIES[name](price)
    except KeyError:
        raise ValueError(f"unknown strategy {name!r}") from None


class Registry:
    """Factory registry: map names to classes."""

    def __init__(self) -> None:
        self._classes: dict[str, type] = {}

    def register(self, name: str) -> Callable[[type], type]:
        """Return a class decorator storing the class under `name` and returning it unchanged."""

        def decorator(cls: type) -> type:
            self._classes[name] = cls
            return cls

        return decorator

    def create(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Instantiate the class registered as `name` with the given arguments.

        Raise KeyError for unknown names.
        """
        return self._classes[name](*args, **kwargs)


class EventEmitter:
    """Observer pattern."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[..., None]]] = defaultdict(list)

    def on(self, event: str, handler: Callable[..., None]) -> Callable[[], None]:
        """Subscribe `handler` to `event`. Return a function that unsubscribes it."""
        self._handlers[event].append(handler)

        def unsubscribe() -> None:
            if handler in self._handlers[event]:
                self._handlers[event].remove(handler)

        return unsubscribe

    def emit(self, event: str, *args: Any, **kwargs: Any) -> int:
        """Call every handler for `event` in subscription order; return how many were called.

        A handler may unsubscribe itself while being called without breaking the loop.
        """
        handlers = list(self._handlers[event])
        for handler in handlers:
            handler(*args, **kwargs)
        return len(handlers)


class CelsiusAdapter:
    """Wrap any object with `read_fahrenheit()` and expose `read_celsius()` (rounded to 1 dp)."""

    def __init__(self, legacy: Any) -> None:
        self._legacy = legacy

    def read_celsius(self) -> float:
        return round((self._legacy.read_fahrenheit() - 32) * 5 / 9, 1)


class NotificationService:
    """Dependency injection: the sender is passed in, never imported."""

    def __init__(self, sender: Callable[[str, str], bool]) -> None:
        self._sender = sender

    def notify_all(self, recipients: list[str], message: str) -> list[str]:
        """Send `message` to each recipient with `sender(recipient, message)`.

        Return the recipients for which the sender returned False (failed deliveries).
        """
        return [r for r in recipients if not self._sender(r, message)]
