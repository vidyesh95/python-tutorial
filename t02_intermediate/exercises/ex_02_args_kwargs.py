"""Exercise 02: *args and **kwargs.

Tasks
1. total: sum any number of positional arguments.
2. build_url: keyword-only options plus **params turned into a query string.
3. merge_configs: merge any number of dicts, later ones win.
4. first_and_rest: star-unpacking.
5. clamp: a positional-only function.

Run: uv run pytest t02_intermediate -k args_kwargs
"""

from typing import Any


def total(*numbers: float) -> float:
    """Sum all arguments; no arguments gives 0.

    >>> total(1, 2, 3.5)
    6.5
    """
    raise NotImplementedError


def build_url(host: str, *, port: int = 80, secure: bool = False, **params: Any) -> str:
    """Build 'scheme://host:port' and append '?k=v&k2=v2' if params are given.

    scheme is 'https' when secure else 'http'. Keep params in the order given.

    >>> build_url("example.com", port=8080, page=2, q="x")
    'http://example.com:8080?page=2&q=x'
    >>> build_url("example.com", secure=True)
    'https://example.com:80'
    """
    raise NotImplementedError


def merge_configs(*configs: dict[str, Any]) -> dict[str, Any]:
    """Merge dicts left to right; later values override earlier ones. Inputs are not mutated.

    >>> merge_configs({"a": 1, "b": 2}, {"b": 3}, {"c": 4})
    {'a': 1, 'b': 3, 'c': 4}
    """
    raise NotImplementedError


def first_and_rest(items: list[int]) -> tuple[int, list[int]]:
    """Return (first item, list of the remaining items). Use star-unpacking.

    Raise ValueError for an empty list.

    >>> first_and_rest([1, 2, 3])
    (1, [2, 3])
    """
    raise NotImplementedError


def clamp(value: float, low: float, high: float, /) -> float:
    """Limit value to the range [low, high]. All parameters are positional-only.

    >>> clamp(15, 0, 10)
    10
    """
    raise NotImplementedError
