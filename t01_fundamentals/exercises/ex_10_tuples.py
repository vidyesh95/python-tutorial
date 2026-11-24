"""Exercise 10 - Tuples and unpacking.

Tasks:
1. min_max: return both extremes as a tuple.
2. swap_pairs: swap the two items of every pair.
3. head_tail: split a sequence into first item and the rest (star unpacking).
4. distance: Euclidean distance between two (x, y) points.
5. middle: everything except the first and last item.
"""


def min_max(values: list[int]) -> tuple[int, int]:
    """Return ``(smallest, largest)``. Raise ValueError for an empty list.

    Examples:
        min_max([4, 9, 1, 7]) -> (1, 9)
        min_max([5]) -> (5, 5)
        min_max([]) -> raises ValueError
    """
    raise NotImplementedError


def swap_pairs(pairs: list[tuple]) -> list[tuple]:
    """Return a list where each ``(a, b)`` becomes ``(b, a)``.

    Examples:
        swap_pairs([(1, "a"), (2, "b")]) -> [("a", 1), ("b", 2)]
        swap_pairs([]) -> []
    """
    raise NotImplementedError


def head_tail(items: tuple) -> tuple[object, list]:
    """Return ``(first, [rest...])``. Raise ValueError for an empty tuple.

    Examples:
        head_tail((1, 2, 3)) -> (1, [2, 3])
        head_tail(("x",)) -> ("x", [])
        head_tail(()) -> raises ValueError
    """
    raise NotImplementedError


def distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Euclidean distance between two points.

    Examples:
        distance((0, 0), (3, 4)) -> 5.0
        distance((1, 1), (1, 1)) -> 0.0
    """
    raise NotImplementedError


def middle(items: tuple) -> list:
    """Return the items between the first and the last as a list (empty if fewer than 3 items).

    Examples:
        middle((1, 2, 3, 4)) -> [2, 3]
        middle((1, 2)) -> []
        middle(()) -> []
    """
    raise NotImplementedError
