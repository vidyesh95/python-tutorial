import pytest

from _loader import load

ex = load("t01_fundamentals", "ex_10_tuples")


def test_min_max():
    assert ex.min_max([4, 9, 1, 7]) == (1, 9)
    assert ex.min_max([5]) == (5, 5)
    with pytest.raises(ValueError):
        ex.min_max([])


def test_swap_pairs():
    assert ex.swap_pairs([(1, "a"), (2, "b")]) == [("a", 1), ("b", 2)]
    assert ex.swap_pairs([]) == []


def test_head_tail():
    assert ex.head_tail((1, 2, 3)) == (1, [2, 3])
    assert ex.head_tail(("x",)) == ("x", [])
    with pytest.raises(ValueError):
        ex.head_tail(())


def test_distance():
    assert ex.distance((0, 0), (3, 4)) == 5.0
    assert ex.distance((1, 1), (1, 1)) == 0.0
    assert ex.distance((-1, -1), (2, 3)) == 5.0


def test_middle():
    assert ex.middle((1, 2, 3, 4)) == [2, 3]
    assert ex.middle((1, 2, 3)) == [2]
    assert ex.middle((1, 2)) == []
    assert ex.middle(()) == []
