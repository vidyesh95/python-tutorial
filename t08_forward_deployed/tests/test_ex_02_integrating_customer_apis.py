from datetime import UTC, datetime

import pytest

httpx = pytest.importorskip("httpx")
respx = pytest.importorskip("respx")

from _loader import load  # noqa: E402

ex = load("t08_forward_deployed", "ex_02_integrating_customer_apis")
BASE = "https://api.test"


@pytest.fixture
def api():
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        client = httpx.Client(base_url=BASE)
        yield router, client
        client.close()


def test_parse_retry_after_seconds_and_garbage():
    assert ex.parse_retry_after("120") == 120.0
    assert ex.parse_retry_after(None) is None
    assert ex.parse_retry_after("") is None
    assert ex.parse_retry_after("soon") is None


def test_parse_retry_after_http_date():
    now = datetime(2015, 10, 21, 7, 27, 50, tzinfo=UTC)
    assert ex.parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT", now=now) == 10.0
    assert ex.parse_retry_after("Wed, 21 Oct 2015 07:00:00 GMT", now=now) == 0.0  # in the past


def test_backoff_schedule():
    assert ex.backoff_schedule(4) == [0.5, 1.0, 2.0]
    assert ex.backoff_schedule(1) == []
    assert ex.backoff_schedule(0) == []
    assert ex.backoff_schedule(8, base=1, cap=4) == [1, 2, 4, 4, 4, 4, 4]


def test_backoff_schedule_honors_retry_after_but_respects_cap():
    assert ex.backoff_schedule(3, retry_after=5) == [5, 5]
    assert ex.backoff_schedule(3, retry_after=60, cap=8) == [8, 8]
    assert ex.backoff_schedule(3, retry_after=0.1) == [0.5, 1.0]


def test_paginate_cursor_walks_all_pages_and_keeps_params(api):
    router, client = api
    pages = {
        None: {"items": [{"id": 1}, {"id": 2}], "next_cursor": "c2"},
        "c2": {"items": [{"id": 3}], "next_cursor": "c3"},
        "c3": {"items": [{"id": 4}], "next_cursor": None},
    }

    def handler(request):
        assert request.url.params["limit"] == "2"
        return httpx.Response(200, json=pages[request.url.params.get("cursor")])

    route = router.get("/items").mock(side_effect=handler)
    items = list(ex.paginate_cursor(client, "/items", {"limit": 2}))
    assert [i["id"] for i in items] == [1, 2, 3, 4]
    assert route.call_count == 3


def test_paginate_cursor_is_lazy(api):
    router, client = api
    route = router.get("/items").mock(
        return_value=httpx.Response(200, json={"items": [{"id": 1}], "next_cursor": "more"})
    )
    gen = ex.paginate_cursor(client, "/items")
    assert next(gen) == {"id": 1}
    assert route.call_count == 1  # page 2 has not been requested yet


def test_paginate_link_header(api):
    router, client = api
    router.get("/rows", params={"page": "1"}).mock(
        return_value=httpx.Response(
            200, json=[{"n": 1}], headers={"Link": f'<{BASE}/rows?page=2>; rel="next"'}
        )
    )
    router.get("/rows", params={"page": "2"}).mock(
        return_value=httpx.Response(
            200,
            json=[{"n": 2}],
            headers={"Link": f'<{BASE}/rows?page=1>; rel="prev", <{BASE}/rows?page=3>; rel="next"'},
        )
    )
    router.get("/rows", params={"page": "3"}).mock(
        return_value=httpx.Response(
            200, json=[{"n": 3}], headers={"Link": f'<{BASE}/rows?page=2>; rel="prev"'}
        )
    )
    assert ex.paginate_link_header(client, "/rows?page=1") == [{"n": 1}, {"n": 2}, {"n": 3}]


def test_get_with_retry_recovers_and_uses_retry_after(api):
    router, client = api
    router.get("/x").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "3"}),
            httpx.Response(503),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    sleeps: list[float] = []
    assert ex.get_with_retry(client, "/x", max_attempts=3, sleep=sleeps.append) == {"ok": True}
    assert sleeps == [3.0, 1.0]  # Retry-After first, then the backoff for the 2nd retry


def test_get_with_retry_gives_up_after_max_attempts(api):
    router, client = api
    route = router.get("/x").mock(return_value=httpx.Response(503))
    with pytest.raises(ex.ApiError) as err:
        ex.get_with_retry(client, "/x", max_attempts=3)
    assert err.value.status == 503
    assert route.call_count == 3


def test_get_with_retry_does_not_retry_client_errors(api):
    router, client = api
    route = router.get("/x").mock(return_value=httpx.Response(404))
    sleeps: list[float] = []
    with pytest.raises(ex.ApiError) as err:
        ex.get_with_retry(client, "/x", sleep=sleeps.append)
    assert err.value.status == 404
    assert route.call_count == 1 and sleeps == []
