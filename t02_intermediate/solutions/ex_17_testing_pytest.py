"""Exercise 17: Testing with pytest.

Implement these small units. The test file for this exercise (tests/test_ex_17_*.py) is a
live example of fixtures, parametrize, pytest.raises, tmp_path, monkeypatch and caplog;
read it, then write similar tests for your own code.

Tasks
1. fizzbuzz: classic, easy to parametrize.
2. is_palindrome: ignore case and non-alphanumerics.
3. ShoppingCart: add, total, validation (needs a fixture to test comfortably).
4. read_config: parse KEY=VALUE files (tmp_path).
5. get_api_key: read an environment variable (monkeypatch).

Run: uv run pytest t02_intermediate -k pytest
"""

import os
from pathlib import Path


def fizzbuzz(n: int) -> str:
    """'FizzBuzz' if divisible by 15, 'Fizz' if by 3, 'Buzz' if by 5, else str(n).

    >>> [fizzbuzz(i) for i in (1, 3, 5, 15)]
    ['1', 'Fizz', 'Buzz', 'FizzBuzz']
    """
    if n % 15 == 0:
        return "FizzBuzz"
    if n % 3 == 0:
        return "Fizz"
    if n % 5 == 0:
        return "Buzz"
    return str(n)


def is_palindrome(text: str) -> bool:
    """Ignore case and anything that is not a letter or digit.

    >>> is_palindrome("A man, a plan, a canal: Panama")
    True
    """
    cleaned = [c.lower() for c in text if c.isalnum()]
    return cleaned == cleaned[::-1]


class ShoppingCart:
    """Holds line items of (name, unit price, quantity)."""

    def __init__(self) -> None:
        self._items: list[tuple[str, float, int]] = []

    def add(self, name: str, price: float, qty: int = 1) -> None:
        """Add an item. Raise ValueError if qty < 1 or price < 0."""
        if qty < 1:
            raise ValueError("qty must be >= 1")
        if price < 0:
            raise ValueError("price must be >= 0")
        self._items.append((name, price, qty))

    def total(self) -> float:
        """Sum of price * qty over all items (0 for an empty cart)."""
        return sum(price * qty for _, price, qty in self._items)

    def __len__(self) -> int:
        """Number of line items (not units)."""
        return len(self._items)


def read_config(path: Path) -> dict[str, str]:
    """Parse a file of KEY=VALUE lines into a dict.

    - ignore blank lines and lines starting with '#'
    - strip spaces around keys and values
    - split on the FIRST '=' only (values may contain '=')
    - raise ValueError for a non-blank, non-comment line without '='
    """
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"invalid line: {line}")
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def get_api_key() -> str:
    """Return the API_KEY environment variable. Raise KeyError('API_KEY is not set')
    when it is missing or empty.
    """
    key = os.environ.get("API_KEY", "")
    if not key:
        raise KeyError("API_KEY is not set")
    return key
