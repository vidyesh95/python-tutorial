# Decorators
"""
A decorator is a function that takes a function and returns a (usually wrapped) function.
    @decorator
    def f(): ...
is exactly   f = decorator(f).
Rules of thumb:
- Always use functools.wraps so the wrapper keeps the original name and docstring.
- To pass arguments, write a decorator FACTORY: a function returning the real decorator.
- Class decorators receive a class and return a class (often the same one, modified).
- Wrappers accept (*args, **kwargs) so they work with any signature.
"""

import functools
import time
from collections.abc import Callable
from typing import Any


# Example: the simplest decorator (with wraps)
def shout(func: Callable[..., str]) -> Callable[..., str]:
    @functools.wraps(func)  # keeps __name__, __doc__
    def wrapper(*args: Any, **kwargs: Any) -> str:
        return func(*args, **kwargs).upper()

    return wrapper


@shout
def greet(name: str) -> str:
    """Return a greeting."""
    return f"hello {name}"


print(greet("ada"), greet.__name__, greet.__doc__)


# Example: timing decorator
def timed(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            print(f"{func.__name__} took {elapsed * 1000:.2f} ms")

    return wrapper


@timed
def slow_sum(n: int) -> int:
    return sum(range(n))


print(slow_sum(100_000))


# Example: decorator with arguments (a factory): retry
def retry(times: int, exceptions: tuple[type[Exception], ...] = (Exception,)) -> Callable:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last: Exception | None = None
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last = exc
                    print(f"attempt {attempt} failed: {exc}")
            assert last is not None
            raise last

        return wrapper

    return decorator


calls = {"n": 0}


@retry(times=3, exceptions=(ConnectionError,))
def flaky() -> str:
    calls["n"] += 1
    if calls["n"] < 3:
        raise ConnectionError("network down")
    return "ok"


print(flaky())


# Example: a decorator that keeps state (call counter)
def count_calls(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        wrapper.calls += 1  # type: ignore[attr-defined]
        return func(*args, **kwargs)

    wrapper.calls = 0  # type: ignore[attr-defined]
    return wrapper


@count_calls
def ping() -> None:
    pass


ping()
ping()
print("ping calls:", ping.calls)  # type: ignore[attr-defined]


# Example: stacking decorators apply bottom-up
@shout
@functools.cache  # built-in memoization decorator (lru_cache(maxsize=128) is bounded)
def cached_greet(name: str) -> str:
    return f"hi {name}"


print(cached_greet("bob"))

# Example: class decorator that registers classes
REGISTRY: dict[str, type] = {}


def register[T: type](cls: T) -> T:
    REGISTRY[cls.__name__.lower()] = cls
    return cls


@register
class CsvExporter:
    pass


@register
class JsonExporter:
    pass


print(sorted(REGISTRY))

"""
Common mistakes
- Forgetting functools.wraps: debuggers, docs and frameworks (FastAPI!) lose the signature.
- Forgetting to return the wrapper (the decorated name becomes None).
- Using @retry instead of @retry(times=3) when the decorator takes arguments.
- Not returning func(*args, **kwargs)'s result from the wrapper.
- Retrying non-idempotent operations blindly (e.g. charging a card twice).
"""

"""
Where this shows up in backend/ML work
- FastAPI routes: @app.get("/users") registers a function (a decorator with arguments).
- Auth, rate limiting, caching (lru_cache), retries with backoff, request timing.
- Dependency-injection and Flask/Click style frameworks are built on decorators.
- ML: @torch.no_grad(), @jit, experiment tracking wrappers.
"""
