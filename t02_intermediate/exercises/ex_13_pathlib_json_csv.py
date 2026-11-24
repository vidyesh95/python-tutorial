"""Exercise 13: pathlib, json and csv.

Tasks
1. write_json / read_json: pretty-printed JSON, creating parent folders.
2. find_files: recursive search by suffix.
3. read_scores: read a CSV into typed dicts.
4. write_csv: write a list of dicts as CSV.
5. csv_to_json: combine the helpers.

Tests use pytest's tmp_path, so nothing is written to the repo.

Run: uv run pytest t02_intermediate -k pathlib
"""

from pathlib import Path
from typing import Any


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write data as JSON with indent=2 and sorted keys. Create missing parent directories."""
    raise NotImplementedError


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object. Return {} if the file does not exist."""
    raise NotImplementedError


def find_files(root: Path, suffix: str) -> list[Path]:
    """Return all files under root (recursively) ending with suffix (e.g. '.csv'), sorted.

    Directories are not included.
    """
    raise NotImplementedError


def read_scores(path: Path) -> list[dict[str, str | int]]:
    """Read a CSV with header 'name,score' into [{'name': 'Ada', 'score': 91}, ...].

    score must be converted to int.
    """
    raise NotImplementedError


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write rows as CSV with a header taken from the first row's keys.

    For an empty list, create an empty file. Create parent directories if needed.
    """
    raise NotImplementedError


def csv_to_json(csv_path: Path, json_path: Path) -> int:
    """Convert a CSV file to a JSON file {"rows": [...]} (values stay strings).

    Return the number of rows converted.
    """
    raise NotImplementedError
