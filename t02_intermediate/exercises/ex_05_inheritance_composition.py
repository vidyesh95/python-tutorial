"""Exercise 05: Inheritance and composition.

Tasks
1. Employee / Manager: subclass and extend with super().
2. mro_names: report the method resolution order.
3. Notifier: composition, a sender object is injected.
4. Stack: wrap a list instead of inheriting from it.

Run: uv run pytest t02_intermediate -k inheritance
"""

from typing import Protocol


class Employee:
    """Has a name and a base salary."""

    def __init__(self, name: str, salary: float) -> None:
        raise NotImplementedError

    def pay(self) -> float:
        """Monthly pay: just the salary."""
        raise NotImplementedError


class Manager(Employee):
    """An Employee with direct reports. Pay = salary + 500 per report."""

    def __init__(self, name: str, salary: float) -> None:
        raise NotImplementedError

    def add_report(self, employee: Employee) -> None:
        """Add a direct report."""
        raise NotImplementedError

    def pay(self) -> float:
        """Base pay (via super()) plus 500 for each report.

        >>> m = Manager("Mo", 1000); m.add_report(Employee("Al", 500)); m.pay()
        1500
        """
        raise NotImplementedError


def mro_names(cls: type) -> list[str]:
    """Names of the classes in cls's MRO, excluding `object`.

    >>> class A: pass
    >>> class B(A): pass
    >>> mro_names(B)
    ['B', 'A']
    """
    raise NotImplementedError


class Sender(Protocol):
    """Anything with send(to, message) -> None can be used as a sender."""

    def send(self, to: str, message: str) -> None: ...


class Notifier:
    """Sends a message to many users through an injected sender (composition)."""

    def __init__(self, sender: Sender) -> None:
        raise NotImplementedError

    def notify_all(self, users: list[str], message: str) -> int:
        """Send message to every non-empty user name via self.sender. Return how many were sent.

        >>> # Notifier(fake).notify_all(["a", "", "b"], "hi") -> 2
        """
        raise NotImplementedError


class Stack:
    """LIFO stack that HAS a list; it must not subclass list."""

    def __init__(self) -> None:
        raise NotImplementedError

    def push(self, item: int) -> None:
        """Add item on top."""
        raise NotImplementedError

    def pop(self) -> int:
        """Remove and return the top item. Raise IndexError('pop from empty stack') if empty."""
        raise NotImplementedError

    def peek(self) -> int:
        """Return the top item without removing it. Raise IndexError if empty."""
        raise NotImplementedError

    def size(self) -> int:
        """Number of items."""
        raise NotImplementedError
