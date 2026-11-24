"""Exercise 17 - File I/O.

Every function receives a ``pathlib.Path`` (tests pass a temporary directory path).
Always use ``with`` and ``encoding="utf-8"``.

Tasks:
1. write_lines: write a list of strings to a file, one per line.
2. read_lines: read a file back into a list of lines without trailing newlines.
3. append_line: add one line to the end of an existing (or new) file.
4. count_words: number of whitespace-separated words in a file.
5. save_json / load_json: round-trip a dict through a JSON file.
"""

from pathlib import Path


def write_lines(path: Path, lines: list[str]) -> None:
    """Write each string of ``lines`` to ``path`` followed by a newline (overwrites the file).

    Examples:
        write_lines(p, ["a", "b"]) -> file content "a\\nb\\n"
        write_lines(p, []) -> empty file
    """
    raise NotImplementedError


def read_lines(path: Path) -> list[str]:
    """Return the lines of the file without newline characters. A missing file returns ``[]``.

    Examples:
        read_lines(p) for content "a\\nb\\n" -> ["a", "b"]
        read_lines(missing_path) -> []
    """
    raise NotImplementedError


def append_line(path: Path, line: str) -> None:
    """Append ``line`` plus a newline; create the file if it does not exist.

    Examples:
        append_line(p, "x"); append_line(p, "y") -> file content "x\\ny\\n"
    """
    raise NotImplementedError


def count_words(path: Path) -> int:
    """Return the number of whitespace-separated words in the file.

    Examples:
        content "hello world\\nfoo" -> 3
        empty file -> 0
    """
    raise NotImplementedError


def save_json(path: Path, data: dict) -> None:
    """Write ``data`` to ``path`` as JSON.

    Examples:
        save_json(p, {"a": 1})
    """
    raise NotImplementedError


def load_json(path: Path) -> dict:
    """Read JSON from ``path`` and return the dict.

    Examples:
        load_json(p) after save_json(p, {"a": [1, 2]}) -> {"a": [1, 2]}
    """
    raise NotImplementedError
