"""Exercise 15: Redis caching (use any redis-py compatible client; tests use fakeredis).

Tasks
1. product_key: build a namespaced, versioned cache key.
2. get_or_set: cache-aside with JSON serialization and a TTL; report hit or miss.
3. invalidate_prefix: delete every key that starts with a prefix (use SCAN, not KEYS).
4. allow_request: fixed-window rate limiter with INCR + EXPIRE.

The client is created with decode_responses=True, so GET returns `str` (or None).

Run: uv run pytest t04_fastapi_backend -k redis_caching
"""

import json  # noqa: F401  (handy for task 2)
from collections.abc import Callable
from typing import Any

import redis


def product_key(product_id: int, version: str = "v1") -> str:
    """Return f"shop:product:{version}:{product_id}"."""
    raise NotImplementedError


def get_or_set(r: redis.Redis, key: str, ttl: int, loader: Callable[[], Any]) -> tuple[Any, bool]:
    """Cache-aside. Return (value, was_hit).

    - If `key` exists: return its JSON-decoded value and True (loader is NOT called).
    - Otherwise call loader(), store json.dumps(value) with expiry `ttl` seconds, and
      return (value, False).
    """
    raise NotImplementedError


def invalidate_prefix(r: redis.Redis, prefix: str) -> int:
    """Delete all keys starting with `prefix` using scan_iter(match=...).

    Return how many keys were deleted (0 if none; do not call DEL with no keys).
    """
    raise NotImplementedError


def allow_request(r: redis.Redis, client_id: str, limit: int, window: int) -> bool:
    """Fixed-window rate limit. Key: f"ratelimit:{client_id}".

    INCR the key; when the new count is 1 set EXPIRE `window` seconds. Return True while
    count <= limit, else False.
    """
    raise NotImplementedError
