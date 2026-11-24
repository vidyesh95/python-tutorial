"""Exercise 08: Enums.

Tasks
1. OrderStatus.is_final property and can_transition_to (StrEnum with behaviour).
2. parse_status: case-insensitive lookup with a clear error.
3. Priority (IntEnum) + most_urgent.
4. describe: use match/case on enum members.

Run: uv run pytest t02_intermediate -k enums
"""

from enum import IntEnum, StrEnum


class OrderStatus(StrEnum):
    """Lifecycle of an order. Members compare equal to their string values."""

    PENDING = "pending"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

    @property
    def is_final(self) -> bool:
        """True for DELIVERED and CANCELLED."""
        raise NotImplementedError

    def can_transition_to(self, new: "OrderStatus") -> bool:
        """Allowed moves: PENDING -> SHIPPED or CANCELLED, SHIPPED -> DELIVERED. Nothing else."""
        raise NotImplementedError


def parse_status(text: str) -> OrderStatus:
    """Parse text ignoring case and surrounding spaces. Raise ValueError('unknown status: x').

    >>> parse_status("  Shipped ")
    <OrderStatus.SHIPPED: 'shipped'>
    """
    raise NotImplementedError


class Priority(IntEnum):
    """Higher number means more urgent."""

    LOW = 1
    MEDIUM = 5
    HIGH = 10


def most_urgent(tasks: list[tuple[str, Priority]]) -> str:
    """Return the name of the task with the highest priority (first one wins ties).

    Raise ValueError for an empty list.

    >>> most_urgent([("a", Priority.LOW), ("b", Priority.HIGH)])
    'b'
    """
    raise NotImplementedError


def describe(status: OrderStatus) -> str:
    """Use match/case. PENDING -> 'waiting', SHIPPED -> 'on the way',
    DELIVERED -> 'done', CANCELLED -> 'stopped'.
    """
    raise NotImplementedError
