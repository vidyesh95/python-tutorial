"""Exercise 02 - Data types.

Tasks:
1. type_name: return the name of a value's type as a string.
2. to_int_or_none: convert text to int, or None when it is not a valid integer.
3. is_collection: True for list, tuple, set, frozenset and dict values.
4. bytes_to_text: decode UTF-8 bytes to str and report how many bytes were used.
"""


def type_name(value: object) -> str:
    """Return the type name of ``value``.

    Examples:
        type_name(5) -> "int"
        type_name([1]) -> "list"
        type_name(None) -> "NoneType"
    """
    return type(value).__name__


def to_int_or_none(text: str) -> int | None:
    """Convert ``text`` to an int; return None if impossible.

    Examples:
        to_int_or_none("42") -> 42
        to_int_or_none(" -7 ") -> -7
        to_int_or_none("4.2") -> None
        to_int_or_none("abc") -> None
    """
    try:
        return int(text)
    except ValueError:
        return None


def is_collection(value: object) -> bool:
    """Return True if ``value`` is a list, tuple, set, frozenset or dict (strings do NOT count).

    Examples:
        is_collection([1, 2]) -> True
        is_collection({"a": 1}) -> True
        is_collection("abc") -> False
        is_collection(5) -> False
    """
    return isinstance(value, list | tuple | set | frozenset | dict)


def bytes_to_text(data: bytes) -> tuple[str, int]:
    """Decode UTF-8 ``data`` and return ``(text, number_of_bytes)``.

    Examples:
        bytes_to_text(b"hi") -> ("hi", 2)
        bytes_to_text("é".encode()) -> ("é", 2)
        bytes_to_text(b"") -> ("", 0)
    """
    return data.decode("utf-8"), len(data)
