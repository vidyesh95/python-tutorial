"""Exercise 02: pagination, Retry-After and retry/backoff against a mocked customer API.

`client` is an `httpx.Client` (tests mount `respx` routes behind it; no network).

Tasks
1. parse_retry_after: seconds or HTTP-date -> float seconds.
2. backoff_schedule: deterministic exponential delays, capped, honoring Retry-After.
3. paginate_cursor: walk a cursor-paginated endpoint as a generator.
4. paginate_link_header: follow `Link: <...>; rel="next"` headers.
5. get_with_retry: retry 429/5xx with backoff, never retry other 4xx.

Run: uv run pytest t08_forward_deployed -k ex_02
"""

from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Any

import httpx  # noqa: F401  (used by the solution)


class ApiError(Exception):
    """Raised for non-retryable errors and when retries are exhausted."""

    def __init__(self, status: int, message: str = "") -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


def parse_retry_after(value: str | None, now: datetime | None = None) -> float | None:
    """Parse a Retry-After header.

    - None / "" / unparseable -> None
    - digits ("120") -> that many seconds as a float
    - HTTP date ("Wed, 21 Oct 2015 07:28:00 GMT") -> seconds from `now` (a timezone-aware
      datetime; default: current UTC time), never negative.
    Hint: email.utils.parsedate_to_datetime handles the date form.
    """
    raise NotImplementedError


def backoff_schedule(
    attempts: int, base: float = 0.5, cap: float = 8.0, retry_after: float | None = None
) -> list[float]:
    """Delays to wait between `attempts` tries (so attempts - 1 delays; attempts <= 1 -> []).

    delay_i = min(cap, base * 2**i) for i = 0, 1, ...
    If `retry_after` is given, each delay becomes min(cap, max(delay_i, retry_after)).
    Example: backoff_schedule(4) == [0.5, 1.0, 2.0]
    """
    raise NotImplementedError


def paginate_cursor(
    client: httpx.Client, path: str, params: dict[str, Any] | None = None
) -> Iterator[dict]:
    """Yield every item from a cursor-paginated endpoint.

    Each response is {"items": [...], "next_cursor": "abc" | null}. Pass the cursor back as the
    `cursor` query parameter (keep any other `params`). Stop when next_cursor is null/missing.
    Must be lazy: do not request page 2 until the consumer has pulled the last item of page 1.
    """
    raise NotImplementedError


def paginate_link_header(client: httpx.Client, path: str) -> list[dict]:
    """GET `path`, then keep following the `rel="next"` link until there is none.
    Each response body is a JSON list; return all rows concatenated, in order.
    Hint: httpx exposes parsed headers as `response.links["next"]["url"]`.
    """
    raise NotImplementedError


def get_with_retry(
    client: httpx.Client,
    path: str,
    max_attempts: int = 3,
    sleep: Callable[[float], None] = lambda s: None,
) -> Any:
    """GET `path` and return the decoded JSON body.

    - 429, 502, 503, 504: retry up to `max_attempts` total attempts. Before each retry call
      sleep(delay), where delay is the Retry-After value when present, else element i of
      backoff_schedule(...) (base 0.5, cap 8) for the i-th retry (0-based). So the second
      retry (i=1) without Retry-After waits 1.0.
    - Other status >= 400: raise ApiError immediately (no retry, no sleep).
    - After the last attempt fails raise ApiError with the final status.
    """
    raise NotImplementedError
