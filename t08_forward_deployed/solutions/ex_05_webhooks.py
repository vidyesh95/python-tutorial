"""Reference solution for exercise 05."""

import hashlib
import hmac
import json
import queue
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response


def sign(secret: str, timestamp: int, body: bytes) -> str:
    return hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()


def verify_signature(
    secret: str, header: str, body: bytes, *, now: float, tolerance: int = 300
) -> bool:
    try:
        pairs = [part.split("=", 1) for part in header.split(",")]
        timestamp = int(next(v for k, v in pairs if k.strip() == "t"))
        candidates = [v.strip() for k, v in pairs if k.strip() == "v1"]
    except ValueError, StopIteration:
        return False
    if abs(now - timestamp) > tolerance:
        return False
    expected = sign(secret, timestamp, body)
    matches = [hmac.compare_digest(expected, c) for c in candidates if c.isascii()]
    return any(matches)


class IdempotencyStore:
    def __init__(self, ttl: float, clock: Callable[[], float]) -> None:
        self._ttl, self._clock = ttl, clock
        self._expires: dict[str, float] = {}

    def claim(self, key: str) -> bool:
        now = self._clock()
        expiry = self._expires.get(key)
        if expiry is not None and expiry > now:
            return False
        self._expires[key] = now + self._ttl
        return True

    def release(self, key: str) -> None:
        self._expires.pop(key, None)


def deliver_with_retries(
    handler: Callable[[dict], None],
    event: dict,
    dead_letters: list[dict],
    max_attempts: int = 3,
    sleep: Callable[[float], None] = lambda s: None,
) -> bool:
    last: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            handler(event)
            return True
        except Exception as exc:
            last = exc
            if attempt < max_attempts:
                sleep(2 ** (attempt - 1))
    dead_letters.append({"event": event, "error": str(last), "attempts": max_attempts})
    return False


def build_receiver(
    secret: str,
    events: queue.Queue[dict[str, Any]],
    store: IdempotencyStore,
    now: Callable[[], float],
) -> FastAPI:
    app = FastAPI()

    @app.post("/webhooks")
    async def receive(request: Request) -> Response:
        body = await request.body()
        header = request.headers.get("x-signature", "")
        if not verify_signature(secret, header, body, now=now()):
            return Response(status_code=401)
        try:
            event = json.loads(body)
            event_id = event["id"]
        except ValueError, KeyError, TypeError:
            return Response(status_code=400)
        if not store.claim(event_id):
            return JSONResponse({"status": "duplicate"})
        try:
            events.put_nowait(event)
        except queue.Full:
            store.release(event_id)
            return Response(status_code=503)
        return JSONResponse({"status": "accepted"}, status_code=202)

    return app
