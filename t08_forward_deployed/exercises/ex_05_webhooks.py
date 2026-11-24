"""Exercise 05: webhook signing/verification, an idempotency store, retries and a receiver.

Tasks
1. sign + verify_signature: HMAC-SHA256 with timestamp tolerance (replay protection).
2. IdempotencyStore: claim/release with a TTL.
3. deliver_with_retries: retry a failing handler, then dead-letter the event.
4. build_receiver: a FastAPI app that verifies, dedupes and enqueues.

Signature header format: "t=<unix seconds>,v1=<hex>[,v1=<hex>...]".
The signed payload is  f"{timestamp}.".encode() + raw_body.

Run: uv run pytest t08_forward_deployed -k ex_05
"""

import hashlib  # noqa: F401  (used by the solution)
import hmac  # noqa: F401
import json  # noqa: F401
import queue
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI


def sign(secret: str, timestamp: int, body: bytes) -> str:
    """Hex HMAC-SHA256 (key = secret utf-8) over f"{timestamp}.".encode() + body."""
    raise NotImplementedError


def verify_signature(
    secret: str, header: str, body: bytes, *, now: float, tolerance: int = 300
) -> bool:
    """True only if the header carries a timestamp within `tolerance` seconds of `now` (in
    EITHER direction) and at least one `v1` value equal to the expected signature.

    Requirements: compare with hmac.compare_digest; accept several v1 values (secret rotation);
    never raise: a malformed/empty header, a non-integer timestamp, or non-hex junk is just False.
    """
    raise NotImplementedError


class IdempotencyStore:
    """Remember keys for `ttl` seconds. `clock()` returns the current time in seconds."""

    def __init__(self, ttl: float, clock: Callable[[], float]) -> None:
        raise NotImplementedError

    def claim(self, key: str) -> bool:
        """True if `key` is new (or its previous claim expired): record it and return True.
        False if it is still remembered.
        """
        raise NotImplementedError

    def release(self, key: str) -> None:
        """Forget `key` so a retry can claim it again (no error if unknown)."""
        raise NotImplementedError


def deliver_with_retries(
    handler: Callable[[dict], None],
    event: dict,
    dead_letters: list[dict],
    max_attempts: int = 3,
    sleep: Callable[[float], None] = lambda s: None,
) -> bool:
    """Call handler(event) until it returns without raising (return True).

    Between failed attempts call sleep(2 ** (attempt - 1)) with attempt starting at 1 (so
    1, 2, 4, ...); do NOT sleep after the last attempt. If every attempt fails append
    {"event": event, "error": str(last_exception), "attempts": max_attempts} to
    `dead_letters` and return False.
    """
    raise NotImplementedError


def build_receiver(
    secret: str,
    events: queue.Queue[dict[str, Any]],
    store: IdempotencyStore,
    now: Callable[[], float],
) -> FastAPI:
    """FastAPI app with POST /webhooks. Steps, in order:

    1. raw body = await request.body(); signature from header "X-Signature".
    2. verify_signature(..., now=now()) fails -> 401 (empty body, same for every failure).
    3. body is not a JSON object with an "id" key -> 400.
    4. store.claim(event["id"]) is False -> 200 with JSON {"status": "duplicate"}.
    5. events.put_nowait(event); if the queue is full release the id and return 503.
    6. otherwise 202 with JSON {"status": "accepted"}.
    """
    raise NotImplementedError
