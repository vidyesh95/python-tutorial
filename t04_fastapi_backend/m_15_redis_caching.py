# Redis Caching
"""
Redis is an in-memory key-value store: very fast reads, optional expiry (TTL) per key.
The most common use in an API is a CACHE in front of a slower source (database, remote API).

Cache-aside (lazy loading), the default pattern:
    1. look in Redis            -> HIT: return it
    2. MISS: load from the DB
    3. store in Redis with a TTL, return it
    On every WRITE: update the DB, then delete (invalidate) the cached key.

Commands used here: `GET`, `SET key value EX seconds`, `DEL`, `TTL`, `INCR`, `SCAN` (via
`scan_iter`). Redis stores bytes/strings; serialize Python dicts with JSON.
`decode_responses=True` makes the client return `str` instead of `bytes`.

Key design: `<app>:<entity>:<version>:<id>`, e.g. `shop:product:v1:42`. The version lets you
change the cached shape without stale data; the prefix lets you invalidate a family of keys.

By default this lesson uses `fakeredis` (an in-memory Redis stand-in, no server needed).
Set REDIS_URL=redis://localhost:6379/0 to use a real Redis instead (e.g. `docker compose up
redis` from m_18).

Run live:  uv run fastapi dev t04_fastapi_backend/m_15_redis_caching.py

Common mistakes
- No TTL: keys live forever and memory grows without bound.
- Forgetting to invalidate on writes, or invalidating BEFORE the DB commit (a reader can
  re-cache the old value in between). Write DB first, then delete the key.
- Caching per-user data under a shared key (leaks data between users). Put the user id in
  the key.
- `KEYS *` in production: it blocks Redis. Use `SCAN` (`scan_iter`).
- Treating the cache as the source of truth. It must be safe to lose at any time.
- Caching `None` misses never (cache penetration) or all keys expiring together (stampede).

Production notes
- Add jitter to TTLs (e.g. ttl + random 0-10%) to avoid synchronized expiry stampedes; use a
  short lock or "serve stale while revalidating" for very hot keys.
- Configure `maxmemory` and an eviction policy (`allkeys-lru`) so Redis degrades gracefully.
- If Redis is down, fall back to the database and log a warning; don't take the API down.
- Track the hit rate (hits / (hits + misses)); a cache with a low hit rate is just latency.
- Use `redis.asyncio.Redis` in `async def` endpoints so Redis calls never block the loop.
  This lesson uses the sync client in plain `def` endpoints (FastAPI runs them in a thread).
"""

import json
import os
import time
from collections.abc import Callable
from typing import Annotated, Any

import fakeredis
import redis
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

app = FastAPI(title="Redis caching")
TTL_SECONDS = 60

_fake_server = fakeredis.FakeServer()


def get_redis() -> redis.Redis:
    """Dependency: real Redis if REDIS_URL is set, otherwise an in-memory fake."""
    if url := os.getenv("REDIS_URL"):
        return redis.Redis.from_url(url, decode_responses=True)
    return fakeredis.FakeRedis(server=_fake_server, decode_responses=True)


RedisDep = Annotated[redis.Redis, Depends(get_redis)]

# The "database": slow, authoritative. DB_HITS lets us see how often we really went there.
PRODUCTS: dict[int, dict[str, Any]] = {1: {"id": 1, "name": "keyboard", "price": 49}}
DB_HITS = 0


def load_product(product_id: int) -> dict[str, Any] | None:
    global DB_HITS
    DB_HITS += 1
    time.sleep(0.01)  # pretend this is a slow query
    return PRODUCTS.get(product_id)


def product_key(product_id: int, version: str = "v1") -> str:
    return f"shop:product:{version}:{product_id}"


# Example: cache-aside with a TTL
def cached_product(r: redis.Redis, product_id: int) -> tuple[dict[str, Any] | None, str]:
    key = product_key(product_id)
    raw = r.get(key)
    if raw is not None:
        return json.loads(str(raw)), "cache"
    product = load_product(product_id)
    if product is not None:  # don't cache misses here; see "cache penetration" above
        r.set(key, json.dumps(product), ex=TTL_SECONDS)
    return product, "db"


class ProductUpdate(BaseModel):
    price: int


@app.get("/products/{product_id}")
def get_product(product_id: int, r: RedisDep) -> dict[str, Any]:
    product, source = cached_product(r, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="no such product")
    return {**product, "source": source}


# Example: invalidate on write (DB first, then delete the key)
@app.put("/products/{product_id}")
def update_product(product_id: int, body: ProductUpdate, r: RedisDep) -> dict[str, Any]:
    if product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="no such product")
    PRODUCTS[product_id]["price"] = body.price  # 1. commit to the source of truth
    r.delete(product_key(product_id))  # 2. then invalidate
    return PRODUCTS[product_id]


# Example: delete a whole family of keys with SCAN (never KEYS)
def invalidate_prefix(r: redis.Redis, prefix: str) -> int:
    keys = list(r.scan_iter(match=f"{prefix}*"))
    return int(r.delete(*keys)) if keys else 0


# Example: fixed-window rate limit with INCR + EXPIRE
def allow_request(r: redis.Redis, client_id: str, limit: int = 3, window: int = 60) -> bool:
    key = f"shop:ratelimit:{client_id}"
    count = int(r.incr(key))
    if count == 1:
        r.expire(key, window)  # first hit starts the window
    return count <= limit


def get_or_set(r: redis.Redis, key: str, ttl: int, loader: Callable[[], Any]) -> Any:
    """Generic helper: the same cache-aside pattern for any JSON-serializable loader."""
    if (raw := r.get(key)) is not None:
        return json.loads(str(raw))
    value = loader()
    r.set(key, json.dumps(value), ex=ttl)
    return value


if __name__ == "__main__":
    r = get_redis()
    r.flushdb()
    client = TestClient(app)

    print(client.get("/products/1").json())  # MISS -> db
    print(client.get("/products/1").json())  # HIT  -> cache
    print("db hits so far:", DB_HITS, "| ttl:", r.ttl(product_key(1)), "seconds")

    print(client.put("/products/1", json={"price": 59}).json())  # invalidates the key
    print(client.get("/products/1").json())  # MISS again, fresh price
    print("db hits so far:", DB_HITS)

    r.set("shop:product:v1:2", "{}")
    print("deleted by prefix:", invalidate_prefix(r, "shop:product:"))
    print("rate limit:", [allow_request(r, "ip-1") for _ in range(5)])
