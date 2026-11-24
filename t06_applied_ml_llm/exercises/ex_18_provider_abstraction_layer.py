"""Exercise 18: retries, fallback chain and cost tracking for an LLM provider layer.

Provided: `Completion`, `RetryableError`, `AllProvidersFailed` and `FakeLLM` (a scripted
provider for tests: each script item is a reply string or an Exception to raise).
Implement the four pieces below.

Tasks
1. is_retryable(exc) -> bool. True when exc is a `RetryableError`, a `TimeoutError` or a
   `ConnectionError`, or has an integer `status_code` attribute of 408, 409, 429 or >= 500.
   Everything else (ValueError, a 400/401/404 status, ...) is False.
2. backoff_delays(n, base=0.5, factor=2.0, cap=8.0) -> list of the first n delays:
   min(cap, base * factor**i) for i in 0..n-1. (No jitter here, so it is testable.)
3. call_with_retry(fn, *, max_attempts=3, base=0.5, sleep=time.sleep): call fn() and return
   its result. On a retryable error call sleep(delay) with the next backoff delay and try
   again; after the last attempt re-raise the error. Non-retryable errors are raised
   immediately with no sleep. Never sleep after the final failed attempt.
4. FallbackChain(providers): `complete(messages)` tries providers in order (each has
   `.name` and `.complete(messages)`). The first success is returned and its name stored in
   `self.last_used`. If a provider raises ANY Exception, remember it and try the next. When all
   fail raise `AllProvidersFailed(errors)` (errors in order). No providers -> AllProvidersFailed([]).
5. CostTracker(prices): `prices` maps model -> (usd_per_million_input, usd_per_million_output).
   `record(model, input_tokens, output_tokens)` adds the cost (unknown models cost 0.0) and
   counts the call. Properties/attrs: `total_cost` (float), `calls` (int), and
   `by_model()` -> {model: total_cost_for_that_model}.

Run: uv run pytest t06_applied_ml_llm -k ex_18
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Completion:
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0


class RetryableError(Exception):
    """Transient provider failure (rate limit, overload, network)."""


class AllProvidersFailed(Exception):
    def __init__(self, errors: list[Exception]) -> None:
        super().__init__(f"{len(errors)} provider(s) failed")
        self.errors = errors


class FakeLLM:
    def __init__(self, script: list[str | Exception], name: str = "fake") -> None:
        self.script, self.name = list(script), name
        self.calls = 0

    def complete(self, messages: list[dict[str, str]]) -> Completion:
        self.calls += 1
        item = self.script.pop(0) if self.script else "ok"
        if isinstance(item, Exception):
            raise item
        return Completion(item, "fake-1", self.name, 10, len(item.split()))


def is_retryable(exc: BaseException) -> bool:
    raise NotImplementedError


def backoff_delays(n: int, base: float = 0.5, factor: float = 2.0, cap: float = 8.0) -> list[float]:
    raise NotImplementedError


def call_with_retry(
    fn: Callable[[], Any],
    *,
    max_attempts: int = 3,
    base: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    raise NotImplementedError


class FallbackChain:
    def __init__(self, providers: list[Any]) -> None:
        raise NotImplementedError

    def complete(self, messages: list[dict[str, str]]) -> Completion:
        raise NotImplementedError


class CostTracker:
    def __init__(self, prices: dict[str, tuple[float, float]]) -> None:
        raise NotImplementedError

    def record(self, model: str, input_tokens: int, output_tokens: int) -> None:
        raise NotImplementedError

    @property
    def total_cost(self) -> float:
        raise NotImplementedError

    def by_model(self) -> dict[str, float]:
        raise NotImplementedError
