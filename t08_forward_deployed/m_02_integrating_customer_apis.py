# Integrating Customer APIs
"""
Customer APIs are never as documented: slow, rate limited, inconsistent, and sometimes down.
Your client must be a small, boring, defensive layer so the rest of your code never sees that.

Client design (httpx)
- ONE `httpx.Client` per integration: `base_url`, shared headers, connection pooling.
- TIMEOUTS ALWAYS: httpx has none you can rely on for slow servers. Use
  `httpx.Timeout(10.0, connect=3.0)`; a hung call without a timeout hangs your worker forever.
- AUTH: put the credential in a header (`Authorization: Bearer ...`) from an env var / secret
  manager. Never log headers, never put keys in URLs (they land in access logs).
- TYPED RESPONSES: validate JSON into pydantic models at the boundary; `extra="ignore"` so the
  customer adding a field does not break you; fail loudly (with context) when required fields vanish.

Pagination patterns (ask which one the API uses on day 1)
- CURSOR:      response has `next_cursor`; send it back as `?cursor=`. Stable under inserts.
- OFFSET:      `?offset=&limit=`; simple, but rows shift if data changes mid-scan.
- LINK HEADER: `Link: <https://...?page=3>; rel="next"` (GitHub style). httpx parses it:
               `response.links["next"]["url"]`.
Always cap pages or loop until the "no next" signal; write the walk as a generator.

Rate limits and retries
- HTTP 429 means slow down; honor `Retry-After` (seconds OR an HTTP date).
- Retry only what is safe and likely transient: 429, 502/503/504, timeouts, connection errors.
  Never retry other 4xx: the request is wrong and will stay wrong.
- Exponential backoff WITH JITTER so a fleet of workers does not retry in lockstep.
  tenacity: `wait_exponential_jitter(initial=0.5, max=8)`.
- Bound total attempts and total time. Retrying forever turns an outage into a retry storm.

Idempotency
- A retried POST may create two orders. Send an `Idempotency-Key` header (a UUID you generate
  ONCE per logical operation and reuse across retries); a good API returns the first result again.
- GET/PUT/DELETE are idempotent by definition; POST needs the key (or a natural unique id).

Everything below runs against a mocked customer API using `respx` (no network).
Run: uv run python -m t08_forward_deployed.m_02_integrating_customer_apis
"""

import email.utils
import os
import time
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime

import httpx
import respx
import tenacity
from pydantic import BaseModel, ConfigDict

BASE_URL = "https://api.customer.test"


class Customer(BaseModel):
    model_config = ConfigDict(extra="ignore")  # tolerate new fields from the customer
    id: int
    name: str
    email: str | None = None


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


class Retryable(ApiError):
    def __init__(self, status: int, message: str, retry_after: float | None = None) -> None:
        super().__init__(status, message)
        self.retry_after = retry_after


# Example 1: Retry-After can be "120" or an HTTP date
def parse_retry_after(value: str | None, now: datetime | None = None) -> float | None:
    if not value:
        return None
    if value.strip().isdigit():
        return float(value)
    try:
        when = email.utils.parsedate_to_datetime(value)
    except TypeError, ValueError:
        return None
    return max(0.0, (when - (now or datetime.now(UTC))).total_seconds())


def _wait(sleep_cap: float) -> Callable[[tenacity.RetryCallState], float]:
    jitter = tenacity.wait_exponential_jitter(initial=0.5, max=sleep_cap)

    def wait(state: tenacity.RetryCallState) -> float:
        exc = state.outcome.exception() if state.outcome else None
        if isinstance(exc, Retryable) and exc.retry_after is not None:
            return min(exc.retry_after, sleep_cap)  # the server told us exactly how long
        return jitter(state)

    return wait


# Example 2: a client with timeouts, auth, retries, idempotency keys, typed output
class CustomerApi:
    def __init__(
        self,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.http = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            timeout=httpx.Timeout(10.0, connect=3.0),
            transport=transport,
        )
        self.sleeps: list[float] = []  # recorded so the demo can print the schedule
        self._sleep = sleep

    def _record_sleep(self, seconds: float) -> None:
        self.sleeps.append(round(seconds, 2))
        self._sleep(seconds)

    def request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        def attempt() -> httpx.Response:
            resp = self.http.request(method, path, **kwargs)  # type: ignore[arg-type]
            if resp.status_code in (429, 502, 503, 504):
                raise Retryable(
                    resp.status_code,
                    resp.reason_phrase,
                    parse_retry_after(resp.headers.get("retry-after")),
                )
            if resp.status_code >= 400:
                raise ApiError(resp.status_code, resp.text[:200])  # not retried
            return resp

        retrying = tenacity.Retrying(
            stop=tenacity.stop_after_attempt(4),
            wait=_wait(sleep_cap=8.0),
            retry=tenacity.retry_if_exception_type((Retryable, httpx.TransportError)),
            sleep=self._record_sleep,
            reraise=True,
        )
        return retrying(attempt)

    def get_customer(self, customer_id: int) -> Customer:
        return Customer.model_validate(self.request("GET", f"/customers/{customer_id}").json())

    def create_order(self, payload: dict) -> dict:
        key = str(uuid.uuid4())  # generated ONCE; every retry inside request() reuses it
        return self.request(
            "POST", "/orders", json=payload, headers={"Idempotency-Key": key}
        ).json()

    # Example 3: three pagination styles as generators
    def iter_cursor(self, path: str, page_size: int = 2) -> Iterator[Customer]:
        cursor: str | None = None
        while True:
            params = {"limit": page_size} | ({"cursor": cursor} if cursor else {})
            data = self.request("GET", path, params=params).json()
            yield from (Customer.model_validate(item) for item in data["items"])
            cursor = data.get("next_cursor")
            if not cursor:
                return

    def iter_offset(self, path: str, page_size: int = 2) -> Iterator[Customer]:
        offset = 0
        while True:
            rows = self.request("GET", path, params={"offset": offset, "limit": page_size}).json()
            yield from (Customer.model_validate(row) for row in rows)
            if len(rows) < page_size:  # a short page means we reached the end
                return
            offset += page_size

    def iter_link_header(self, path: str) -> Iterator[Customer]:
        url: str | None = path
        while url:
            resp = self.request("GET", url)
            yield from (Customer.model_validate(row) for row in resp.json())
            url = resp.links.get("next", {}).get("url")


CUSTOMERS = [
    {"id": i, "name": f"Customer {i}", "email": f"c{i}@example.com", "tier": "gold"}
    for i in range(1, 6)
]


def mount_mock_api(router: respx.MockRouter) -> dict[str, int]:
    """A fake customer API with every behavior above. Returns counters for the demo."""
    seen = {"flaky": 0, "orders_created": 0}
    orders: dict[str, dict] = {}

    def cursor_page(request: httpx.Request) -> httpx.Response:
        start = int(request.url.params.get("cursor", "0"))
        limit = int(request.url.params["limit"])
        chunk = CUSTOMERS[start : start + limit]
        nxt = str(start + limit) if start + limit < len(CUSTOMERS) else None
        return httpx.Response(200, json={"items": chunk, "next_cursor": nxt})

    def offset_page(request: httpx.Request) -> httpx.Response:
        offset, limit = int(request.url.params["offset"]), int(request.url.params["limit"])
        return httpx.Response(200, json=CUSTOMERS[offset : offset + limit])

    def link_page(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        chunk = CUSTOMERS[(page - 1) * 2 : page * 2]
        headers = {"Link": f'<{BASE_URL}/links?page={page + 1}>; rel="next"'} if page < 3 else {}
        return httpx.Response(200, json=chunk, headers=headers)

    def flaky(request: httpx.Request) -> httpx.Response:
        seen["flaky"] += 1
        if seen["flaky"] == 1:
            return httpx.Response(429, headers={"Retry-After": "2"})
        if seen["flaky"] == 2:
            return httpx.Response(503)
        return httpx.Response(200, json=CUSTOMERS[0])

    def create_order(request: httpx.Request) -> httpx.Response:
        key = request.headers["Idempotency-Key"]
        if key not in orders:  # first time we see this key: do the work
            orders[key] = {"order_id": len(orders) + 1}
            seen["orders_created"] += 1
            return httpx.Response(503)  # ...but the response is lost (the classic failure)
        return httpx.Response(201, json=orders[key])  # same key: replay the stored result

    router.get("/customers/1").mock(side_effect=flaky)
    router.get("/cursor").mock(side_effect=cursor_page)
    router.get("/offset").mock(side_effect=offset_page)
    router.get("/links").mock(side_effect=link_page)
    router.post("/orders").mock(side_effect=create_order)
    router.get("/customers/404").mock(return_value=httpx.Response(404, json={"error": "nope"}))
    return seen


def run_demo() -> None:
    key = os.environ.get("CUSTOMER_API_KEY", "demo-key-not-secret")  # from env, never hardcoded
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        seen = mount_mock_api(router)
        api = CustomerApi(key, sleep=lambda s: None)  # no real sleeping in the demo

        print("retry-after parse:", parse_retry_after("3"), parse_retry_after("garbage"))
        print("429 -> 503 -> 200:", api.get_customer(1), "| backoff schedule:", api.sleeps)

        print("cursor:", [c.id for c in api.iter_cursor("/cursor")])
        print("offset:", [c.id for c in api.iter_offset("/offset")])
        print("link  :", [c.id for c in api.iter_link_header(f"{BASE_URL}/links")])

        order = api.create_order({"sku": "A-1", "qty": 3})
        print(
            "order after a lost response:", order, "| created server-side:", seen["orders_created"]
        )

        try:
            api.get_customer(404)
        except ApiError as exc:
            print("4xx is not retried:", exc)


"""
Common mistakes:
- No timeout (the default in many HTTP libs is none) or one timeout for connect and read.
- Retrying every exception, including 400/401/404: you just hammer a broken request.
- Backoff without jitter, or ignoring Retry-After: all workers wake at once.
- Retrying POST without an idempotency key: duplicate orders, double charges.
- Offset pagination while the data is changing: rows are skipped or repeated.
- Building URLs by string concatenation with user input; pass `params=` and let httpx encode.
- Logging full request headers or URLs that carry tokens.

In the field:
- Record the customer's real rate limit in the runbook and make concurrency configurable.
- Log method, path (no query secrets), status, attempt number, latency and a request id.
- Pin down behavior with contract tests against a sandbox; mock only what you must.
- Make the sync resumable: store the last cursor/updated_at so a crash does not restart a
  10-million-row backfill.
"""

if __name__ == "__main__":
    run_demo()
