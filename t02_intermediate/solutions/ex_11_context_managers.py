"""Exercise 11: Context managers.

Tasks
1. Timer: class-based context manager recording `.elapsed`.
2. temp_attr: restore an attribute afterwards (generator-based).
3. cd: temporarily change the working directory.
4. Transaction: commit on success, discard changes on error.
5. ignore_errors: re-implement contextlib.suppress.

Run: uv run pytest t02_intermediate -k context
"""

import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import Any


class Timer:
    """`with Timer() as t:` -> after the block, t.elapsed is the duration in seconds (float).

    Exceptions inside the block must propagate (do not suppress them).
    """

    def __enter__(self) -> Timer:
        self.elapsed = 0.0
        self._start = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        self.elapsed = time.perf_counter() - self._start
        return False


@contextmanager
def temp_attr(obj: Any, name: str, value: Any) -> Iterator[None]:
    """Set obj.name = value inside the block, then restore the old value, even on error.

    If the attribute did not exist before, delete it afterwards.
    """
    missing = object()
    old = getattr(obj, name, missing)
    setattr(obj, name, value)
    try:
        yield
    finally:
        if old is missing:
            delattr(obj, name)
        else:
            setattr(obj, name, old)


@contextmanager
def cd(path: Path) -> Iterator[Path]:
    """Change the working directory to `path` inside the block; always change back.

    Yields the path.
    """
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield path
    finally:
        os.chdir(previous)


class Transaction:
    """Edit a copy of `store`; apply it only if the block finishes without an exception.

    with Transaction(store) as tx:   # tx is a working copy (dict)
        tx["a"] = 1
    On success the store becomes equal to tx; on error the store is left untouched and the
    exception propagates.
    """

    def __init__(self, store: dict[str, Any]) -> None:
        self.store = store

    def __enter__(self) -> dict[str, Any]:
        self.pending = dict(self.store)
        return self.pending

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if exc_type is None:
            self.store.clear()
            self.store.update(self.pending)
        return False


@contextmanager
def ignore_errors(*exc_types: type[BaseException]) -> Iterator[None]:
    """Swallow the given exception types raised inside the block; others propagate."""
    try:
        yield
    except exc_types:
        pass
