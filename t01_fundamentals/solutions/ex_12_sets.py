"""Exercise 12 - Sets.

Tasks:
1. has_duplicates: does a list contain repeated items?
2. common_elements: sorted list of items present in both lists.
3. only_in_first: sorted items that are in the first list but not in the second.
4. is_pangram: does a sentence use every letter a-z at least once?
5. unique_sorted: sorted list of distinct values.
"""

import string


def has_duplicates(items: list) -> bool:
    """Return True if any value occurs more than once.

    Examples:
        has_duplicates([1, 2, 3, 2]) -> True
        has_duplicates([1, 2, 3]) -> False
        has_duplicates([]) -> False
    """
    return len(set(items)) != len(items)


def common_elements(a: list[int], b: list[int]) -> list[int]:
    """Return a sorted list of distinct values present in both lists.

    Examples:
        common_elements([1, 2, 2, 3], [2, 3, 4]) -> [2, 3]
        common_elements([1], [2]) -> []
    """
    return sorted(set(a) & set(b))


def only_in_first(a: list[int], b: list[int]) -> list[int]:
    """Return a sorted list of distinct values in ``a`` that are not in ``b``.

    Examples:
        only_in_first([1, 2, 3, 3], [3, 4]) -> [1, 2]
        only_in_first([1], [1]) -> []
        only_in_first([], [1]) -> []
    """
    return sorted(set(a) - set(b))


def is_pangram(sentence: str) -> bool:
    """True if every letter a-z appears at least once (case-insensitive; other characters ignored).

    Examples:
        is_pangram("The quick brown fox jumps over the lazy dog") -> True
        is_pangram("Hello world") -> False
        is_pangram("") -> False
    """
    return set(string.ascii_lowercase) <= set(sentence.lower())


def unique_sorted(items: list[int]) -> list[int]:
    """Return the distinct values in ascending order.

    Examples:
        unique_sorted([3, 1, 3, 2, 1]) -> [1, 2, 3]
        unique_sorted([]) -> []
    """
    return sorted(set(items))
