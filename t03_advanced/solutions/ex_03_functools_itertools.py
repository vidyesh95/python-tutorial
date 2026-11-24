"""Exercise 03: functools and itertools (reference solution)."""

import functools
import itertools
import operator
from collections.abc import Callable, Iterable, Iterator
from typing import Any


def chunked[T](items: Iterable[T], n: int) -> Iterator[list[T]]:
    if n < 1:
        raise ValueError("n must be >= 1")
    it = iter(items)
    while chunk := list(itertools.islice(it, n)):
        yield chunk


def moving_average(values: Iterable[float], window: int) -> list[float]:
    if window < 1:
        raise ValueError("window must be >= 1")
    it = iter(values)
    buf = list(itertools.islice(it, window))
    if len(buf) < window:
        return []
    out = [sum(buf) / window]
    for x in it:
        buf = buf[1:] + [x]
        out.append(sum(buf) / window)
    return out


def make_multiplier(factor: float) -> Callable[[float], float]:
    return functools.partial(operator.mul, factor)


@functools.singledispatch
def describe(value: Any) -> str:
    return "other"


@describe.register
def _(value: bool) -> str:
    return "other"  # bool is a subclass of int; treat it as "other"


@describe.register
def _(value: int) -> str:
    return f"int:{value}"


@describe.register
def _(value: str) -> str:
    return f"str:{value}"


@describe.register
def _(value: list) -> str:
    return f"list of {len(value)}"


def run_length_encode(items: Iterable[Any]) -> list[tuple[Any, int]]:
    return [(k, sum(1 for _ in g)) for k, g in itertools.groupby(items)]
