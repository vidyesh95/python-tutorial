"""Reference solution for Exercise 18: retries, fallback chain and cost tracking."""

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
    if isinstance(exc, RetryableError | TimeoutError | ConnectionError):
        return True
    status = getattr(exc, "status_code", None)
    return isinstance(status, int) and (status in (408, 409, 429) or status >= 500)


def backoff_delays(n: int, base: float = 0.5, factor: float = 2.0, cap: float = 8.0) -> list[float]:
    return [min(cap, base * factor**i) for i in range(n)]


def call_with_retry(
    fn: Callable[[], Any],
    *,
    max_attempts: int = 3,
    base: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    delays = backoff_delays(max_attempts - 1, base=base)
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as exc:
            if not is_retryable(exc) or attempt == max_attempts - 1:
                raise
            sleep(delays[attempt])
    raise AssertionError("unreachable")


class FallbackChain:
    def __init__(self, providers: list[Any]) -> None:
        self.providers = providers
        self.last_used: str | None = None

    def complete(self, messages: list[dict[str, str]]) -> Completion:
        errors: list[Exception] = []
        for provider in self.providers:
            try:
                result = provider.complete(messages)
            except Exception as exc:
                errors.append(exc)
                continue
            self.last_used = provider.name
            return result
        raise AllProvidersFailed(errors)


class CostTracker:
    def __init__(self, prices: dict[str, tuple[float, float]]) -> None:
        self.prices = prices
        self.calls = 0
        self._by_model: dict[str, float] = {}

    def record(self, model: str, input_tokens: int, output_tokens: int) -> None:
        price_in, price_out = self.prices.get(model, (0.0, 0.0))
        cost = (input_tokens * price_in + output_tokens * price_out) / 1_000_000
        self._by_model[model] = self._by_model.get(model, 0.0) + cost
        self.calls += 1

    @property
    def total_cost(self) -> float:
        return sum(self._by_model.values())

    def by_model(self) -> dict[str, float]:
        return dict(self._by_model)
