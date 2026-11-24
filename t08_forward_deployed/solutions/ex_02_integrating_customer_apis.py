"""Reference solution for exercise 02."""

import email.utils
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any

import httpx


class ApiError(Exception):
    def __init__(self, status: int, message: str = "") -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


def parse_retry_after(value: str | None, now: datetime | None = None) -> float | None:
    if not value or not value.strip():
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        when = email.utils.parsedate_to_datetime(value)
    except TypeError, ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - (now or datetime.now(UTC))).total_seconds())


def backoff_schedule(
    attempts: int, base: float = 0.5, cap: float = 8.0, retry_after: float | None = None
) -> list[float]:
    delays = []
    for i in range(max(attempts - 1, 0)):
        delay = min(cap, base * 2**i)
        if retry_after is not None:
            delay = min(cap, max(delay, retry_after))
        delays.append(delay)
    return delays


def paginate_cursor(
    client: httpx.Client, path: str, params: dict[str, Any] | None = None
) -> Iterator[dict]:
    cursor: str | None = None
    while True:
        query = dict(params or {})
        if cursor:
            query["cursor"] = cursor
        resp = client.get(path, params=query)
        resp.raise_for_status()
        body = resp.json()
        yield from body["items"]
        cursor = body.get("next_cursor")
        if not cursor:
            return


def paginate_link_header(client: httpx.Client, path: str) -> list[dict]:
    rows: list[dict] = []
    url: str | None = path
    while url:
        resp = client.get(url)
        resp.raise_for_status()
        rows.extend(resp.json())
        url = resp.links.get("next", {}).get("url")
    return rows


def get_with_retry(
    client: httpx.Client,
    path: str,
    max_attempts: int = 3,
    sleep: Callable[[float], None] = lambda s: None,
) -> Any:
    delays = backoff_schedule(max_attempts + 1)  # plenty of entries; we index per retry
    for attempt in range(max_attempts):
        resp = client.get(path)
        if resp.status_code < 400:
            return resp.json()
        if resp.status_code not in (429, 502, 503, 504):
            raise ApiError(resp.status_code, resp.text[:100])
        if attempt == max_attempts - 1:
            raise ApiError(resp.status_code, "retries exhausted")
        wait = parse_retry_after(resp.headers.get("retry-after"))
        sleep(wait if wait is not None else delays[attempt])
    raise ApiError(0, "unreachable")  # pragma: no cover
