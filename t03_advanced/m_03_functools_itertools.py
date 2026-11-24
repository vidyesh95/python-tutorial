# functools and itertools in Practice
"""
Two stdlib modules that turn loops into one-liners and make code lazy and fast.

functools: tools that operate on FUNCTIONS
- cache / lru_cache: memoize pure functions (arguments must be hashable)
- partial: pre-fill some arguments of a function
- singledispatch: pick an implementation by the TYPE of the first argument
- reduce: fold an iterable into one value
- wraps, cached_property, total_ordering are also worth knowing

itertools: tools that operate on ITERATORS (all lazy; they produce values on demand)
- chain, islice, groupby, accumulate, product, combinations, permutations, cycle, count
- Python 3.12+: batched, 3.10+: pairwise

Rule of thumb: prefer these over hand-written index loops, and keep pipelines lazy until
the final list()/sum()/for.
"""

import functools
import itertools
import operator
from collections.abc import Iterable, Iterator
from typing import Any


# Example: cache (memoization turns exponential recursion into linear)
@functools.cache
def fib(n: int) -> int:
    return n if n < 2 else fib(n - 1) + fib(n - 2)


print("fib(80):", fib(80))
print("cache info:", fib.cache_info())  # hits/misses; fib.cache_clear() resets


# Example: lru_cache with a size limit (bounds memory; evicts least recently used)
@functools.lru_cache(maxsize=2)
def square(n: int) -> int:
    return n * n


square(1), square(2), square(3), square(3)
print("lru:", square.cache_info())


# Example: partial (freeze arguments) instead of a lambda
def power(base: float, exp: float) -> float:
    return base**exp


cube = functools.partial(power, exp=3)
print("cube(2):", cube(2), "| partial keeps:", cube.func.__name__, cube.keywords)


# Example: singledispatch (open-ended "if isinstance" chain)
@functools.singledispatch
def to_json(value: Any) -> str:
    raise TypeError(f"cannot serialize {type(value).__name__}")


@to_json.register
def _(value: int) -> str:  # dispatches on the annotation
    return str(value)


@to_json.register
def _(value: str) -> str:
    return f'"{value}"'


@to_json.register
def _(value: list) -> str:
    return "[" + ", ".join(to_json(v) for v in value) + "]"


print("dispatch:", to_json([1, "a", [2]]))
try:
    to_json(3.5)
except TypeError as exc:
    print("unregistered type:", exc)


# Example: reduce and its friends
nums = [1, 2, 3, 4]
print("reduce product:", functools.reduce(operator.mul, nums, 1))
print("accumulate:", list(itertools.accumulate(nums)))  # running totals, lazy cousin of reduce


# Example: cached_property (computed once per instance, stored in the instance __dict__)
class Dataset:
    def __init__(self, rows: list[int]) -> None:
        self.rows = rows

    @functools.cached_property
    def mean(self) -> float:
        print("  (computing mean once)")
        return sum(self.rows) / len(self.rows)


ds = Dataset([2, 4, 6])
print("mean:", ds.mean, ds.mean)


# Example: lazy pipelines: chain, islice, count
def evens() -> Iterator[int]:
    return (n for n in itertools.count() if n % 2 == 0)  # infinite, but lazy


print("first 5 evens:", list(itertools.islice(evens(), 5)))
print("chain:", list(itertools.chain([1, 2], (3,), range(4, 6))))


# Example: groupby (input MUST be sorted by the key first)
words = ["apple", "avocado", "banana", "blueberry", "cherry"]
for letter, group in itertools.groupby(words, key=lambda w: w[0]):
    print(f"  {letter}: {list(group)}")


# Example: batched (3.12+) and pairwise (3.10+)
print("batched:", list(itertools.batched(range(7), 3, strict=False)))
print("pairwise:", list(itertools.pairwise([1, 4, 9, 16])))  # consecutive pairs -> diffs
print("diffs:", [b - a for a, b in itertools.pairwise([1, 4, 9, 16])])


# Example: combinatorics
print("product:", list(itertools.product("ab", [0, 1])))
print("combinations:", list(itertools.combinations("abc", 2)))
print("permutations:", len(list(itertools.permutations(range(4)))))


# Example: recipes (from the itertools docs) built from the primitives
def take(n: int, iterable: Iterable[Any]) -> list[Any]:
    return list(itertools.islice(iterable, n))


def flatten(list_of_lists: Iterable[Iterable[Any]]) -> Iterator[Any]:
    return itertools.chain.from_iterable(list_of_lists)


def sliding_window(iterable: Iterable[Any], n: int) -> Iterator[tuple[Any, ...]]:
    it = iter(iterable)
    window = tuple(itertools.islice(it, n))
    if len(window) == n:
        yield window
    for x in it:
        window = window[1:] + (x,)
        yield window


print("take:", take(3, itertools.cycle("xy")))
print("flatten:", list(flatten([[1, 2], [3], []])))
print("window:", list(sliding_window(range(5), 3)))

# Example: tee (copy an iterator) and zip_longest
a, b = itertools.tee(iter([1, 2, 3]))
print("tee:", list(a), list(b))
print("zip_longest:", list(itertools.zip_longest("ab", [1, 2, 3], fillvalue="-")))

"""
Common mistakes
- Caching a function with unhashable arguments (lists/dicts) -> TypeError; or caching an
  impure function (time, randomness, DB reads) and serving stale results.
- @cache on a method keeps every `self` alive forever (a memory leak); use
  cached_property or a per-instance cache instead.
- Forgetting groupby needs sorted input and that each group is a one-shot iterator
  (consume it before advancing).
- Iterating a tee/generator twice: iterators are exhausted after one pass.
- Using lru_cache(maxsize=None) in a long-running service on unbounded keys.

Where this shows up in backend/ML/robotics work
- Backend: @cache for config and expensive lookups, partial for callbacks, singledispatch
  for serializers, batched for chunked DB inserts or API calls.
- ML: batched/islice to stream training data, product for hyperparameter grids,
  accumulate for running metrics, pairwise for diffs and deltas.
- Robotics: sliding_window / pairwise over sensor streams for smoothing and velocities.
"""
