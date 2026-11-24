# Webhooks
"""
A webhook is an HTTP POST the customer's system (or yours) sends when something happens, so you
do not have to poll. The receiver is a PUBLIC endpoint that anyone can call: treat every
request as hostile until proven otherwise.

Receiving, in this order
1. READ THE RAW BYTES (`await request.body()`). Verify the signature over exactly what was
   sent; re-serialized JSON will not match.
2. VERIFY THE SIGNATURE: HMAC-SHA256 of f"{timestamp}.{body}" with a shared secret, compared
   with `hmac.compare_digest` (constant time). Header shape (Stripe-like):
   `X-Signature: t=1700000000,v1=<hex>`. Allow several `v1=` values so you can rotate secrets.
3. CHECK THE TIMESTAMP is within a tolerance (e.g. 5 minutes) -> REPLAY PROTECTION. Without it
   an attacker who captured one valid request can resend it forever. The timestamp is part of
   what is signed, so it cannot be changed.
4. PARSE and validate the JSON (pydantic in real code); reject oversized bodies early.
5. DEDUPE by event id (idempotency): senders retry, so you WILL see the same event twice.
6. ACK FAST and HAND OFF to a queue; do the slow work in a worker. Senders time out after a few
   seconds and then retry (more duplicates). Reply 2xx only once the event is safely queued.

Status codes tell the sender what to do: 2xx = done, don't retry; 4xx = my fault, don't retry
(except 408/429); 5xx = try again later. Return 401 for a bad signature and never say WHY.

Processing: at-least-once delivery + idempotent handlers = effectively once. Failed events are
retried with backoff and after N attempts moved to a DEAD-LETTER list for a human (alert on it,
replay after the fix). Order is NOT guaranteed: use the event's version/timestamp, not arrival.

Sending webhooks (you are the vendor): sign each request, include a unique event id and
timestamp, set timeouts, retry 5xx/timeouts with exponential backoff, stop after a limit, and
give customers a way to see failed deliveries and rotate the secret.

Demo uses FastAPI's TestClient (in-process, no sockets) and `respx` for the sending side.
Run: uv run python -m t08_forward_deployed.m_05_webhooks
"""

import hashlib
import hmac
import json
import queue
import time
from collections.abc import Callable

import httpx
import respx
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

TOLERANCE_S = 300
MAX_BODY = 1_000_000


# Example 1: signing and verification
def sign(secret: str, timestamp: int, body: bytes) -> str:
    return hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()


def signature_header(secret: str, body: bytes, timestamp: int | None = None) -> str:
    ts = int(time.time()) if timestamp is None else timestamp
    return f"t={ts},v1={sign(secret, ts, body)}"


def verify(secret: str, header: str, body: bytes, now: float, tolerance: int = TOLERANCE_S) -> bool:
    """Never raises: any malformed input is simply 'not valid'."""
    try:
        parts = [p.split("=", 1) for p in header.split(",")]
        timestamp = int(next(v for k, v in parts if k.strip() == "t"))
        candidates = [v for k, v in parts if k.strip() == "v1"]
    except ValueError, StopIteration:
        return False
    if abs(now - timestamp) > tolerance:  # too old (replay) or from the future (clock attack)
        return False
    expected = sign(secret, timestamp, body)
    # check every candidate without short-circuiting on the first hit
    results = [
        hmac.compare_digest(expected, c) for c in candidates if c.isascii()
    ]  # str must be ASCII
    return any(results)


# Example 2: an idempotency store (use Redis SETNX / a DB unique key in production)
class IdempotencyStore:
    def __init__(self, ttl: float = 86_400, clock: Callable[[], float] = time.time) -> None:
        self._seen: dict[str, float] = {}
        self._ttl, self._clock = ttl, clock

    def claim(self, key: str) -> bool:
        """True the first time (caller should process); False for a duplicate."""
        now = self._clock()
        self._seen = {k: exp for k, exp in self._seen.items() if exp > now}  # drop expired
        if key in self._seen:
            return False
        self._seen[key] = now + self._ttl
        return True

    def release(self, key: str) -> None:  # processing failed: allow the retry through
        self._seen.pop(key, None)


# Example 3: the FastAPI receiver (verify -> parse -> dedupe -> enqueue -> 202)
def build_receiver(
    secret: str,
    events: queue.Queue[dict],
    store: IdempotencyStore,
    now: Callable[[], float] = time.time,
) -> FastAPI:
    app = FastAPI(title="webhook receiver")

    @app.post("/webhooks/orders")
    async def receive(request: Request) -> Response:
        body = await request.body()  # raw bytes, before any JSON parsing
        if len(body) > MAX_BODY:
            return Response(status_code=413)
        header = request.headers.get("x-signature", "")
        if not verify(secret, header, body, now()):
            return Response(status_code=401)  # same answer for every failure: no oracle
        try:
            event = json.loads(body)
            event_id = event["id"]
        except ValueError, KeyError, TypeError:
            return Response(status_code=400)
        if not store.claim(event_id):
            return Response(content='{"status":"duplicate"}', media_type="application/json")
        try:
            events.put_nowait(event)  # hand off; the worker does the real work
        except queue.Full:
            store.release(event_id)
            return Response(status_code=503, headers={"Retry-After": "5"})
        return Response(
            content='{"status":"accepted"}', status_code=202, media_type="application/json"
        )

    return app


# Example 4: worker with retries and a dead-letter list
def process_event(
    event: dict,
    handler: Callable[[dict], None],
    dead_letters: list[dict],
    max_attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    for attempt in range(1, max_attempts + 1):
        try:
            handler(event)
            return True
        except Exception as exc:  # a poison event must not kill the worker
            if attempt == max_attempts:
                dead_letters.append({"event": event, "error": repr(exc), "attempts": attempt})
                return False
            sleep(2 ** (attempt - 1))  # 1s, 2s, 4s ...
    return False  # pragma: no cover


# Example 5: sending webhooks to a customer, with retries
def send_webhook(
    http: httpx.Client,
    url: str,
    secret: str,
    event: dict,
    max_attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    body = json.dumps(event, separators=(",", ":"), sort_keys=True).encode()
    for attempt in range(1, max_attempts + 1):
        headers = {
            "Content-Type": "application/json",
            "X-Signature": signature_header(secret, body),
        }
        try:  # re-sign each attempt so the timestamp stays fresh
            resp = http.post(url, content=body, headers=headers, timeout=5.0)
            if resp.status_code < 300:
                return attempt
            if resp.status_code < 500 and resp.status_code not in (408, 429):
                raise RuntimeError(f"customer rejected the webhook: HTTP {resp.status_code}")
        except httpx.TransportError:
            pass  # timeout / connection error: retry
        if attempt < max_attempts:
            sleep(2 ** (attempt - 1))
    raise RuntimeError(f"gave up after {max_attempts} attempts")


def run_demo() -> None:
    secret = "whsec_demo_only"  # in real code: from env / secret manager
    events: queue.Queue[dict] = queue.Queue()
    store = IdempotencyStore()
    client = TestClient(build_receiver(secret, events, store))

    body = json.dumps({"id": "evt_1", "type": "order.created", "data": {"order": 42}}).encode()

    def post(header: str, payload: bytes = body) -> str:
        r = client.post("/webhooks/orders", content=payload, headers={"X-Signature": header})
        return f"{r.status_code} {r.text}".strip()

    print("valid          ->", post(signature_header(secret, body)))
    print("duplicate      ->", post(signature_header(secret, body)))
    print("tampered body  ->", post(signature_header(secret, body), body.replace(b"42", b"43")))
    print("wrong secret   ->", post(signature_header("whsec_other", body)))
    print("replayed (10m) ->", post(signature_header(secret, body, int(time.time()) - 600)))
    print("no signature   ->", post(""))

    dead: list[dict] = []
    attempts = {"n": 0}

    def flaky_handler(event: dict) -> None:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ConnectionError("downstream timeout")

    ok = process_event(events.get_nowait(), flaky_handler, dead, sleep=lambda s: None)
    print("worker: ok =", ok, "after", attempts["n"], "attempts; dead letters:", len(dead))
    poison = {"id": "evt_2"}
    process_event(poison, lambda e: 1 / 0, dead, sleep=lambda s: None)
    print("poison event dead-lettered:", dead[0]["error"], "| attempts:", dead[0]["attempts"])

    with respx.mock() as router:
        router.post("https://customer.test/hooks").mock(
            side_effect=[httpx.Response(503), httpx.Response(200)]
        )
        n = send_webhook(
            httpx.Client(),
            "https://customer.test/hooks",
            secret,
            {"id": "evt_9"},
            sleep=lambda s: None,
        )
        print("sent webhook, delivered on attempt", n)


"""
Common mistakes:
- Verifying a signature over re-serialized JSON (`json.dumps(request.json())`) instead of the
  raw body; or comparing signatures with `==`.
- No timestamp tolerance (replay), or checking the timestamp but not including it in the MAC.
- Doing slow work inline, so the sender times out and retries into duplicates.
- Not deduping: the same `order.created` charges the customer twice.
- Leaking why a request failed ("bad timestamp" vs "bad signature") or echoing the body back.
- Trusting the event payload blindly: for sensitive actions re-fetch the object via the API.
- Logging the signature header or secret; storing the secret in git.

Production notes:
- Keep the secret in a secret manager; support two active secrets for rotation.
- Persist events BEFORE acknowledging (queue/DB), alert on dead-letter depth, and provide a
  replay tool. Return 503 + Retry-After when you are overloaded rather than dropping events.
- Put the endpoint behind TLS and a WAF/rate limit; optionally allowlist the sender's IPs
  (defense in depth, not a replacement for signatures).
- Track delivery lag and failure rate per customer; expose recent deliveries in a dashboard.
"""

if __name__ == "__main__":
    run_demo()
