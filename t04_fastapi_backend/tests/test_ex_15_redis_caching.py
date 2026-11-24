import pytest

fakeredis = pytest.importorskip("fakeredis")

from _loader import load  # noqa: E402

ex = load("t04_fastapi_backend", "ex_15_redis_caching")


@pytest.fixture
def r():
    # A private FakeServer per test: no shared state between tests.
    return fakeredis.FakeRedis(server=fakeredis.FakeServer(), decode_responses=True)


def test_product_key():
    assert ex.product_key(42) == "shop:product:v1:42"
    assert ex.product_key(42, "v2") == "shop:product:v2:42"


def test_get_or_set_miss_then_hit(r):
    calls = []

    def loader():
        calls.append(1)
        return {"id": 1, "tags": ["a", "b"]}

    assert ex.get_or_set(r, "k", 30, loader) == ({"id": 1, "tags": ["a", "b"]}, False)
    assert ex.get_or_set(r, "k", 30, loader) == ({"id": 1, "tags": ["a", "b"]}, True)
    assert len(calls) == 1


def test_get_or_set_sets_ttl_and_json(r):
    ex.get_or_set(r, "k", 30, lambda: {"x": 1})
    assert 0 < r.ttl("k") <= 30
    assert r.get("k") == '{"x": 1}'


def test_get_or_set_recomputes_after_expiry(r):
    ex.get_or_set(r, "k", 30, lambda: 1)
    r.delete("k")  # simulate expiry / invalidation
    assert ex.get_or_set(r, "k", 30, lambda: 2) == (2, False)


def test_invalidate_prefix(r):
    for key in ("shop:product:v1:1", "shop:product:v1:2", "shop:order:v1:1"):
        r.set(key, "x")
    assert ex.invalidate_prefix(r, "shop:product:") == 2
    assert sorted(r.keys("*")) == ["shop:order:v1:1"]
    assert ex.invalidate_prefix(r, "nothing:") == 0


def test_allow_request_limits_and_sets_window(r):
    results = [ex.allow_request(r, "ip-1", 3, 60) for _ in range(5)]
    assert results == [True, True, True, False, False]
    assert 0 < r.ttl("ratelimit:ip-1") <= 60
    assert ex.allow_request(r, "ip-2", 3, 60) is True  # separate client, separate counter
