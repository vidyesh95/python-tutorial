import enum

import pytest

from _loader import load

ex = load("t02_intermediate", "ex_08_enums")
S = ex.OrderStatus


def test_is_final():
    assert S.DELIVERED.is_final and S.CANCELLED.is_final
    assert not S.PENDING.is_final and not S.SHIPPED.is_final
    assert S.SHIPPED == "shipped"  # StrEnum


@pytest.mark.parametrize(
    ("old", "new", "ok"),
    [
        (S.PENDING, S.SHIPPED, True),
        (S.PENDING, S.CANCELLED, True),
        (S.PENDING, S.DELIVERED, False),
        (S.SHIPPED, S.DELIVERED, True),
        (S.SHIPPED, S.CANCELLED, False),
        (S.DELIVERED, S.PENDING, False),
        (S.CANCELLED, S.SHIPPED, False),
    ],
)
def test_can_transition_to(old, new, ok):
    assert old.can_transition_to(new) is ok


def test_parse_status():
    assert ex.parse_status("  Shipped ") is S.SHIPPED
    assert ex.parse_status("PENDING") is S.PENDING
    with pytest.raises(ValueError, match="unknown status: nope"):
        ex.parse_status("nope")


def test_priority_and_most_urgent():
    assert issubclass(ex.Priority, enum.IntEnum)
    assert ex.Priority.HIGH > ex.Priority.MEDIUM > ex.Priority.LOW
    tasks = [("a", ex.Priority.LOW), ("b", ex.Priority.HIGH), ("c", ex.Priority.HIGH)]
    assert ex.most_urgent(tasks) == "b"  # first wins ties
    assert ex.most_urgent([("only", ex.Priority.LOW)]) == "only"
    with pytest.raises(ValueError):
        ex.most_urgent([])


def test_describe_every_member():
    assert ex.describe(S.PENDING) == "waiting"
    assert ex.describe(S.SHIPPED) == "on the way"
    assert ex.describe(S.DELIVERED) == "done"
    assert ex.describe(S.CANCELLED) == "stopped"
