# Iterators and Generators
"""
Iterable: something you can loop over (has __iter__ returning an iterator).
Iterator: an object with __next__ that returns the next item or raises StopIteration.
A for loop calls iter() once, then next() repeatedly until StopIteration.
Generator function: a function with `yield`. Calling it returns a generator (an iterator)
that pauses at each yield and resumes where it left off, keeping local state.
`yield from other` delegates to another iterable.
Generators are lazy: values are produced one at a time, so memory stays tiny.
"""

from collections.abc import Iterable, Iterator
from itertools import islice

# Example: the iterator protocol by hand
nums = [10, 20, 30]
it = iter(nums)
print(next(it), next(it), next(it))
try:
    next(it)
except StopIteration:
    print("exhausted")
print(next(iter([]), "default"))  # next() accepts a default instead of raising


# Example: a custom iterator class
class CountUp:
    def __init__(self, stop: int) -> None:
        self.current = 0
        self.stop = stop

    def __iter__(self) -> Iterator[int]:
        return self

    def __next__(self) -> int:
        if self.current >= self.stop:
            raise StopIteration
        self.current += 1
        return self.current


print(list(CountUp(3)))


# Example: the same thing as a generator is far shorter
def count_up(stop: int) -> Iterator[int]:
    n = 1
    while n <= stop:
        yield n
        n += 1


print(list(count_up(3)))


# Example: generators pause and keep state
def fibonacci() -> Iterator[int]:
    a, b = 0, 1
    while True:  # infinite is fine, since values are produced on demand
        yield a
        a, b = b, a + b


print(list(islice(fibonacci(), 10)))  # islice takes just the first 10

gen = count_up(2)
print(next(gen), next(gen), list(gen))  # list(gen) is empty: already consumed


# Example: yield from delegates to a sub-iterable
def flatten(nested: Iterable[Iterable[int]]) -> Iterator[int]:
    for inner in nested:
        yield from inner


print(list(flatten([[1, 2], [3], [4, 5]])))


# Example: a generator pipeline: each stage lazily feeds the next
def numbers(limit: int) -> Iterator[int]:
    yield from range(limit)


def evens(source: Iterable[int]) -> Iterator[int]:
    return (n for n in source if n % 2 == 0)


def squared(source: Iterable[int]) -> Iterator[int]:
    return (n * n for n in source)


pipeline = squared(evens(numbers(1_000_000_000)))  # nothing computed yet
print(list(islice(pipeline, 4)))


# Example: send() and generator-based accumulators (advanced, but good to know)
def running_total() -> Iterator[int]:
    total = 0
    while True:
        value = yield total
        total += value or 0


acc = running_total()
next(acc)  # prime the generator
print(acc.send(5), acc.send(10))

# Example: lazy file-like processing
lines = iter(["a=1", "", "b=2"])
print(dict(line.split("=") for line in lines if line))

"""
Common mistakes
- Iterating a generator twice; the second pass yields nothing. Re-create it or list() it.
- Calling a generator function and forgetting to iterate it: nothing runs.
- Expecting `return x` inside a generator to produce a value; it only sets StopIteration.value.
- Turning a huge generator into a list and losing the memory advantage.
- Catching StopIteration inside a generator (PEP 479 turns it into RuntimeError).
"""

"""
Where this shows up in backend/ML work
- Streaming large files, DB cursors and paginated API results without loading everything.
- ML data loaders: yield batches of examples to the training loop.
- FastAPI StreamingResponse and LLM token streaming consume generators.
- Dependency functions with `yield` in FastAPI are generators (setup, yield, teardown).
"""
