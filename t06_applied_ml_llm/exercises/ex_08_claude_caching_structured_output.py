"""Exercise 08: prompt-caching math and structured output (logic only, no network).

Tasks
1. cache_savings(usage, *, input_price, write_mult=1.25, read_mult=0.1): `usage` has
   input_tokens, cache_creation_input_tokens and cache_read_input_tokens (the last two may be
   None). `input_price` is dollars per MILLION tokens. Return a dict:
     actual_cost   = (input + write * write_mult + read * read_mult) * price / 1e6
     baseline_cost = (input + write + read) * price / 1e6        (what no caching would cost)
     saved         = baseline_cost - actual_cost
     hit_rate      = read / (input + write + read), or 0.0 when there are no input tokens
2. build_cached_request(static_context, question, *, model=MODEL, ttl=None, max_tokens=1024):
   kwargs for messages.create where the STABLE text is a single `system` text block carrying
   cache_control {"type": "ephemeral"} (add "ttl": ttl when given; allowed: None, "5m", "1h",
   else ValueError) and the changing question is the only user message (AFTER the cache
   breakpoint, never cached).
3. parse_structured(text, model_cls): the model may wrap JSON in a ```json fenced block. Strip
   the fences, json-decode and validate with the pydantic `model_cls`. Raise
   StructuredOutputError (message mentions what went wrong) for invalid JSON OR validation errors.
4. extract_with_retry(client, text, model_cls, *, model=MODEL, max_attempts=3): ask the model
   to extract data. Call client.messages.create(model=model, max_tokens=1024, messages=messages)
   and parse the joined text blocks with parse_structured. On StructuredOutputError append
   {"role": "assistant", "content": reply_text} and a user message that contains the error
   text, then try again. After max_attempts failures re-raise the last StructuredOutputError.
5. break_even_requests(write_mult, read_mult): the smallest number of requests k (k >= 1) sharing
   a cached prefix for which caching is cheaper:  write_mult + (k - 1) * read_mult < k.
   Raise ValueError if it never pays off (check up to k = 1000).

Run: uv run pytest t06_applied_ml_llm -k ex_08
"""

import json  # noqa: F401
from typing import Any

from pydantic import BaseModel, ValidationError  # noqa: F401

MODEL = "claude-opus-5-5"


class StructuredOutputError(ValueError):
    """The model's reply was not valid JSON for the requested schema."""


def cache_savings(
    usage: Any, *, input_price: float, write_mult: float = 1.25, read_mult: float = 0.1
) -> dict[str, float]:
    raise NotImplementedError


def build_cached_request(
    static_context: str,
    question: str,
    *,
    model: str = MODEL,
    ttl: str | None = None,
    max_tokens: int = 1024,
) -> dict[str, Any]:
    raise NotImplementedError


def parse_structured[M: BaseModel](text: str, model_cls: type[M]) -> M:
    raise NotImplementedError


def extract_with_retry[M: BaseModel](
    client: Any, text: str, model_cls: type[M], *, model: str = MODEL, max_attempts: int = 3
) -> M:
    raise NotImplementedError


def break_even_requests(write_mult: float, read_mult: float) -> int:
    raise NotImplementedError
