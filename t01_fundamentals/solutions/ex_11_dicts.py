"""Exercise 11 - Dictionaries.

Tasks:
1. word_count: count words (case-insensitive).
2. invert_dict: swap keys and values.
3. merge_with_sum: merge two dicts, adding values for shared keys.
4. group_by_length: group words by their length.
5. get_nested: safely read a value from nested dictionaries with a key path.
"""


def word_count(text: str) -> dict[str, int]:
    """Count words, ignoring case; words are separated by whitespace (no punctuation handling needed).

    Examples:
        word_count("the cat and The hat") -> {"the": 2, "cat": 1, "and": 1, "hat": 1}
        word_count("") -> {}
    """
    counts: dict[str, int] = {}
    for word in text.lower().split():
        counts[word] = counts.get(word, 0) + 1
    return counts


def invert_dict(d: dict) -> dict:
    """Swap keys and values (values are unique and hashable).

    Examples:
        invert_dict({"a": 1, "b": 2}) -> {1: "a", 2: "b"}
        invert_dict({}) -> {}
    """
    return {value: key for key, value in d.items()}


def merge_with_sum(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
    """Return a new dict with keys of both; shared keys have summed values. Inputs are not modified.

    Examples:
        merge_with_sum({"x": 1, "y": 2}, {"y": 10, "z": 3}) -> {"x": 1, "y": 12, "z": 3}
        merge_with_sum({}, {"a": 1}) -> {"a": 1}
    """
    result = dict(a)
    for key, value in b.items():
        result[key] = result.get(key, 0) + value
    return result


def group_by_length(words: list[str]) -> dict[int, list[str]]:
    """Group words by length, preserving the original order inside each group.

    Examples:
        group_by_length(["a", "bb", "c", "dd", "eee"]) -> {1: ["a", "c"], 2: ["bb", "dd"], 3: ["eee"]}
        group_by_length([]) -> {}
    """
    groups: dict[int, list[str]] = {}
    for word in words:
        groups.setdefault(len(word), []).append(word)
    return groups


def get_nested(data: dict, path: list[str], default: object = None) -> object:
    """Follow ``path`` through nested dicts; return ``default`` if any key is missing
    or an intermediate value is not a dict.

    Examples:
        get_nested({"a": {"b": {"c": 1}}}, ["a", "b", "c"]) -> 1
        get_nested({"a": {"b": 1}}, ["a", "x"], default=0) -> 0
        get_nested({"a": 5}, ["a", "b"]) -> None
        get_nested({"a": 1}, []) -> {"a": 1}
    """
    current: object = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current
