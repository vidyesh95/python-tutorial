"""Reference solution for Exercise 08: caching math and structured output."""

import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError

MODEL = "claude-opus-5-5"


class StructuredOutputError(ValueError):
    """The model's reply was not valid JSON for the requested schema."""


def cache_savings(
    usage: Any, *, input_price: float, write_mult: float = 1.25, read_mult: float = 0.1
) -> dict[str, float]:
    uncached = usage.input_tokens or 0
    write = usage.cache_creation_input_tokens or 0
    read = usage.cache_read_input_tokens or 0
    total = uncached + write + read
    actual = (uncached + write * write_mult + read * read_mult) * input_price / 1_000_000
    baseline = total * input_price / 1_000_000
    return {
        "actual_cost": actual,
        "baseline_cost": baseline,
        "saved": baseline - actual,
        "hit_rate": read / total if total else 0.0,
    }


def build_cached_request(
    static_context: str,
    question: str,
    *,
    model: str = MODEL,
    ttl: str | None = None,
    max_tokens: int = 1024,
) -> dict[str, Any]:
    if ttl not in (None, "5m", "1h"):
        raise ValueError(f"unsupported ttl: {ttl!r}")
    cache_control: dict[str, str] = {"type": "ephemeral"}
    if ttl is not None:
        cache_control["ttl"] = ttl
    return {
        "model": model,
        "max_tokens": max_tokens,
        "system": [{"type": "text", "text": static_context, "cache_control": cache_control}],
        "messages": [{"role": "user", "content": question}],
    }


_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def parse_structured[M: BaseModel](text: str, model_cls: type[M]) -> M:
    cleaned = text.strip()
    fenced = _FENCE.match(cleaned)
    if fenced:
        cleaned = fenced.group(1)
    try:
        return model_cls.model_validate(json.loads(cleaned))
    except json.JSONDecodeError as exc:
        raise StructuredOutputError(f"invalid JSON: {exc}") from exc
    except ValidationError as exc:
        raise StructuredOutputError(f"schema validation failed: {exc}") from exc


def extract_with_retry[M: BaseModel](
    client: Any, text: str, model_cls: type[M], *, model: str = MODEL, max_attempts: int = 3
) -> M:
    messages: list[dict[str, Any]] = [{"role": "user", "content": text}]
    last_error: StructuredOutputError | None = None
    for _ in range(max_attempts):
        response = client.messages.create(model=model, max_tokens=1024, messages=messages)
        reply = "".join(b.text for b in response.content if b.type == "text")
        try:
            return parse_structured(reply, model_cls)
        except StructuredOutputError as exc:
            last_error = exc
            messages.append({"role": "assistant", "content": reply})
            messages.append(
                {"role": "user", "content": f"That was invalid: {exc}. Return only corrected JSON."}
            )
    assert last_error is not None
    raise last_error


def break_even_requests(write_mult: float, read_mult: float) -> int:
    for k in range(1, 1001):
        if write_mult + (k - 1) * read_mult < k:
            return k
    raise ValueError("caching never pays off with these multipliers")
