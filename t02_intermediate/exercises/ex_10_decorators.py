"""Exercise 10: Decorators.

Tasks
1. call_counter: a decorator that tracks `.calls` on the wrapper.
2. retry: a decorator FACTORY that retries on selected exceptions.
3. memoize: cache results by positional arguments.
4. timed: record the duration of the last call in `.last_duration`.
5. add_repr: a CLASS decorator that adds a __repr__.

All wrappers must use functools.wraps.

Run: uv run pytest t02_intermediate -k decorators
"""

from collections.abc import Callable
from typing import Any


def call_counter(func: Callable[..., Any]) -> Callable[..., Any]:
    """Count calls in `wrapper.calls` (starts at 0). Preserve __name__ and __doc__."""
    raise NotImplementedError


def retry(times: int, exceptions: tuple[type[Exception], ...] = (Exception,)) -> Callable:
    """Retry the function up to `times` attempts when one of `exceptions` is raised.

    After the last failed attempt, re-raise that exception. Other exceptions propagate
    immediately. No sleeping.

    >>> # @retry(3, (ConnectionError,)) -> up to 3 calls in total
    """
    raise NotImplementedError


def memoize(func: Callable[..., Any]) -> Callable[..., Any]:
    """Cache results keyed by the positional arguments (all hashable). Keep metadata."""
    raise NotImplementedError


def timed(func: Callable[..., Any]) -> Callable[..., Any]:
    """Store the seconds taken by the most recent call in `wrapper.last_duration`.

    Record it even if the function raises. Initial value: None.
    """
    raise NotImplementedError


def add_repr[T: type](cls: T) -> T:
    """Class decorator: give the class a __repr__ like 'Point(x=1, y=2)' from vars(self).

    Return the same class.
    """
    raise NotImplementedError
