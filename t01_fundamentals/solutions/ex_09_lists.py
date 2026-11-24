"""Exercise 09 - Lists.

Tasks:
1. remove_duplicates: drop repeats but keep the first-seen order.
2. rotate: rotate a list to the right by k places (without modifying the input).
3. flatten: flatten one level of nesting.
4. second_largest: second largest DISTINCT value.
5. chunk: split a list into pieces of a given size.
"""


def remove_duplicates(items: list) -> list:
    """Return a new list without duplicates, keeping first occurrences in order.

    Examples:
        remove_duplicates([3, 1, 3, 2, 1]) -> [3, 1, 2]
        remove_duplicates([]) -> []
    """
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def rotate(items: list, k: int) -> list:
    """Return a NEW list rotated right by ``k`` (k may be larger than the length or negative).

    Examples:
        rotate([1, 2, 3, 4, 5], 2) -> [4, 5, 1, 2, 3]
        rotate([1, 2, 3], 3) -> [1, 2, 3]
        rotate([1, 2, 3], -1) -> [2, 3, 1]
        rotate([], 4) -> []
    """
    if not items:
        return []
    k %= len(items)
    return items[-k:] + items[:-k] if k else items[:]


def flatten(nested: list[list]) -> list:
    """Flatten a list of lists by one level.

    Examples:
        flatten([[1, 2], [3], []]) -> [1, 2, 3]
        flatten([]) -> []
    """
    return [item for sub in nested for item in sub]


def second_largest(nums: list[int]) -> int | None:
    """Return the second largest distinct number, or None if there are fewer than 2 distinct values.

    Examples:
        second_largest([4, 9, 2, 7]) -> 7
        second_largest([5, 5, 3]) -> 3
        second_largest([1, 1]) -> None
        second_largest([]) -> None
    """
    unique = sorted(set(nums), reverse=True)
    return unique[1] if len(unique) >= 2 else None


def chunk(items: list, size: int) -> list[list]:
    """Split ``items`` into consecutive lists of ``size`` (the last may be shorter). ``size`` must be > 0.

    Examples:
        chunk([1, 2, 3, 4, 5], 2) -> [[1, 2], [3, 4], [5]]
        chunk([], 3) -> []
        chunk([1, 2], 5) -> [[1, 2]]
        chunk([1], 0) -> raises ValueError
    """
    if size <= 0:
        raise ValueError("size must be positive")
    return [items[i : i + size] for i in range(0, len(items), size)]
