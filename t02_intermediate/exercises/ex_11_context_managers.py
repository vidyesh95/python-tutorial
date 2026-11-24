"""Exercise 11: Context managers.

Tasks
1. Timer: class-based context manager recording `.elapsed`.
2. temp_attr: restore an attribute afterwards (generator-based).
3. cd: temporarily change the working directory.
4. Transaction: commit on success, discard changes on error.
5. ignore_errors: re-implement contextlib.suppress.

Run: uv run pytest t02_intermediate -k context
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import Any


class Timer:
    """`with Timer() as t:` -> after the block, t.elapsed is the duration in seconds (float).

    Exceptions inside the block must propagate (do not suppress them).
    """

    def __enter__(self) -> "Timer":
        raise NotImplementedError

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        raise NotImplementedError


@contextmanager
def temp_attr(obj: Any, name: str, value: Any) -> Iterator[None]:
    """Set obj.name = value inside the block, then restore the old value, even on error.

    If the attribute did not exist before, delete it afterwards.
    """
    raise NotImplementedError


@contextmanager
def cd(path: Path) -> Iterator[Path]:
    """Change the working directory to `path` inside the block; always change back.

    Yields the path.
    """
    raise NotImplementedError


class Transaction:
    """Edit a copy of `store`; apply it only if the block finishes without an exception.

    with Transaction(store) as tx:   # tx is a working copy (dict)
        tx["a"] = 1
    On success the store becomes equal to tx; on error the store is left untouched and the
    exception propagates.
    """

    def __init__(self, store: dict[str, Any]) -> None:
        raise NotImplementedError

    def __enter__(self) -> dict[str, Any]:
        raise NotImplementedError

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        raise NotImplementedError


@contextmanager
def ignore_errors(*exc_types: type[BaseException]) -> Iterator[None]:
    """Swallow the given exception types raised inside the block; others propagate."""
    raise NotImplementedError
