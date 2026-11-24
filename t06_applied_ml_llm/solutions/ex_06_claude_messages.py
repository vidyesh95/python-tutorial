"""Reference solution for Exercise 06: Claude Messages API."""

import time
from collections.abc import Callable
from typing import Any

import anthropic

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
    if not user_text.strip():
        raise ValueError("user_text must not be blank")
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    for item in history:
        if item.get("role") not in ("user", "assistant"):
            raise ValueError(f"bad role in history: {item.get('role')!r}")
    request: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [*history, {"role": "user", "content": user_text}],
    }
    if system:
        request["system"] = system
    return request


def extract_text(message: Any) -> str:
    return "".join(block.text for block in message.content if block.type == "text")


def ask(client: Any, question: str, *, system: str | None = None) -> str:
    message = client.messages.create(**build_request([], question, system=system))
    if message.stop_reason == "refusal":
        raise RefusalError("the model declined to answer")
    if message.stop_reason == "max_tokens":
        raise TruncatedError("answer truncated by max_tokens")
    return extract_text(message)


def is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, anthropic.APIConnectionError):  # includes APITimeoutError
        return True
    if isinstance(exc, anthropic.APIStatusError):
        return exc.status_code in (408, 409, 429) or exc.status_code >= 500
    return False


def call_with_retry[T](
    fn: Callable[[], T],
    *,
    max_attempts: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as exc:
            if not is_retryable(exc) or attempt == max_attempts - 1:
                raise
            sleep(min(base_delay * 2**attempt, max_delay))
    raise AssertionError("unreachable: max_attempts must be >= 1")
