"""Exercise 06: Claude Messages API (logic only, no network).

Your code is tested against fake clients and hand-built response objects, so no API key is
needed. The shapes match the real `anthropic` SDK.

Tasks
1. build_request(history, user_text, *, system=None, model=MODEL, max_tokens=1024): return the
   kwargs dict for `client.messages.create(...)`:
   {"model", "max_tokens", "messages": history + [new user message]} plus "system" ONLY when a
   system prompt is given. Do not mutate `history` (return a new list). Raise ValueError when
   user_text is blank, max_tokens <= 0, or a history item's role is not "user"/"assistant".
2. extract_text(message): join the text of every block with type == "text" (skip thinking and
   tool_use blocks). Return "" when there is none.
3. ask(client, question, *, system=None): build a request (no history), call
   `client.messages.create(**request)`, raise RefusalError if stop_reason == "refusal",
   TruncatedError if stop_reason == "max_tokens", otherwise return the extracted text.
4. is_retryable(exc): True for rate limits / timeouts / connection errors and for HTTP status
   408, 409, 429 and >= 500 (anthropic.APIStatusError). False for other 4xx (400, 401, 403,
   404) and for unrelated exceptions such as ValueError.
5. call_with_retry(fn, *, max_attempts=4, base_delay=1.0, max_delay=30.0, sleep=time.sleep):
   call `fn()`. On a retryable error sleep min(base_delay * 2**attempt_index, max_delay) and try
   again (delays 1, 2, 4, ...). Non-retryable errors propagate immediately. After
   `max_attempts` failed attempts re-raise the last error. Return fn's result on success.

Run: uv run pytest t06_applied_ml_llm -k ex_06
"""

import time
from collections.abc import Callable
from typing import Any

import anthropic  # noqa: F401

MODEL = "claude-opus-5-5"


class RefusalError(RuntimeError):
    """The model declined to answer."""


class TruncatedError(RuntimeError):
    """The answer was cut off by max_tokens."""


def build_request(
    history: list[dict[str, Any]],
    user_text: str,
    *,
    system: str | None = None,
    model: str = MODEL,
    max_tokens: int = 1024,
) -> dict[str, Any]:
    raise NotImplementedError


def extract_text(message: Any) -> str:
    raise NotImplementedError


def ask(client: Any, question: str, *, system: str | None = None) -> str:
    raise NotImplementedError


def is_retryable(exc: BaseException) -> bool:
    raise NotImplementedError


def call_with_retry[T](
    fn: Callable[[], T],
    *,
    max_attempts: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    raise NotImplementedError
