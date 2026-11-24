# Context Managers
"""
A context manager guarantees setup and cleanup around a block:
    with open("f.txt") as f: ...
Protocol: __enter__(self) runs on entry (its return value is bound by `as`);
__exit__(self, exc_type, exc, tb) runs on exit EVEN IF an exception happened.
Return True from __exit__ to swallow the exception (rarely a good idea).
Easier way: @contextlib.contextmanager turns a generator with one `yield` into one.
Also handy: contextlib.suppress, ExitStack, closing, redirect_stdout.
"""

import time
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager, suppress
from types import TracebackType


# Example: class-based context manager
class Timer:
    def __enter__(self) -> Timer:
        self.start = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        self.elapsed = time.perf_counter() - self.start
        print(f"block finished (error={exc_type.__name__ if exc_type else None})")
        return False  # False/None: do not swallow exceptions


with Timer() as t:
    total = sum(range(10_000))
print("elapsed is float:", isinstance(t.elapsed, float))

try:
    with Timer():
        raise ValueError("boom")
except ValueError as exc:
    print("exception still propagated:", exc)


# Example: @contextmanager: code before yield is __enter__, after is __exit__
@contextmanager
def tag(name: str) -> Iterator[str]:
    print(f"<{name}>")
    try:
        yield name  # value bound by `as`
    finally:  # try/finally makes cleanup run even on errors
        print(f"</{name}>")


with tag("section") as label:
    print("inside", label)


# Example: managing a resource (pretend connection)
class FakeConnection:
    def __init__(self) -> None:
        self.open = True

    def close(self) -> None:
        self.open = False


@contextmanager
def connection() -> Iterator[FakeConnection]:
    conn = FakeConnection()
    try:
        yield conn
    finally:
        conn.close()


with connection() as conn:
    print("open inside:", conn.open)
print("open after:", conn.open)

# Example: suppress ignores specific exceptions
with suppress(KeyError):
    {}["missing"]
print("KeyError ignored")

# Example: ExitStack handles a dynamic number of context managers
with ExitStack() as stack:
    tags = [stack.enter_context(tag(n)) for n in ("a", "b")]
    stack.callback(print, "callback runs last-in-first-out")
    print("tags:", tags)

# Example: several managers in one `with`
with tag("x") as x, tag("y") as y:
    print(x, y)


# Example: a context manager that swallows an error on purpose
@contextmanager
def ignore_zero_division() -> Iterator[None]:
    try:
        yield
    except ZeroDivisionError:
        print("division by zero ignored")


with ignore_zero_division():
    _ = 1 / 0

"""
Common mistakes
- Writing a @contextmanager without try/finally, so cleanup is skipped on errors.
- Yielding more than once in a @contextmanager generator (RuntimeError).
- Returning True from __exit__ by accident and silently hiding bugs.
- Forgetting that `as` binds what __enter__ returns, which may not be self.
- Using the resource after the `with` block has closed it.
"""

"""
Where this shows up in backend/ML work
- Files, sockets, DB sessions and transactions (commit on success, rollback on error).
- FastAPI lifespan handlers and dependencies with `yield` are context managers in disguise.
- Temporary directories, locks, timers, and torch.no_grad() / autocast blocks.
- Patching in tests: unittest.mock.patch(...) used as a `with` block.
"""
