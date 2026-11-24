import json
import queue

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from _loader import load  # noqa: E402

ex = load("t08_forward_deployed", "ex_05_webhooks")
SECRET = "whsec_test"
NOW = 1_700_000_000
BODY = b'{"id":"evt_1","type":"order.created"}'


def header(ts=NOW, secret=SECRET, body=BODY):
    return f"t={ts},v1={ex.sign(secret, ts, body)}"


def test_sign_is_hex_hmac_of_timestamp_dot_body():
    import hashlib
    import hmac

    expected = hmac.new(b"k", b"123." + b"{}", hashlib.sha256).hexdigest()
    assert ex.sign("k", 123, b"{}") == expected


def test_verify_accepts_valid_and_within_tolerance():
    assert ex.verify_signature(SECRET, header(), BODY, now=NOW)
    assert ex.verify_signature(SECRET, header(NOW - 299), BODY, now=NOW)
    assert ex.verify_signature(SECRET, header(NOW + 299), BODY, now=NOW)


def test_verify_rejects_replay_future_tamper_and_wrong_secret():
    assert not ex.verify_signature(SECRET, header(NOW - 301), BODY, now=NOW)  # replay
    assert not ex.verify_signature(SECRET, header(NOW + 301), BODY, now=NOW)  # from the future
    assert not ex.verify_signature(SECRET, header(), BODY + b" ", now=NOW)  # tampered
    assert not ex.verify_signature(SECRET, header(secret="other"), BODY, now=NOW)
    assert ex.verify_signature(SECRET, header(NOW - 301), BODY, now=NOW, tolerance=600)


def test_verify_supports_rotation_with_multiple_v1():
    old = ex.sign("old-secret", NOW, BODY)
    new = ex.sign(SECRET, NOW, BODY)
    assert ex.verify_signature(SECRET, f"t={NOW},v1={old},v1={new}", BODY, now=NOW)
    assert not ex.verify_signature(SECRET, f"t={NOW},v1={old}", BODY, now=NOW)


@pytest.mark.parametrize(
    "bad", ["", "garbage", "t=abc,v1=00", f"v1={'0' * 64}", f"t={NOW}", f"t={NOW},v1=", "t=1,v1=é"]
)
def test_verify_never_raises_on_malformed_headers(bad):
    assert ex.verify_signature(SECRET, bad, BODY, now=NOW) is False


def test_idempotency_store_ttl_and_release():
    clock = {"t": 0.0}
    store = ex.IdempotencyStore(ttl=10, clock=lambda: clock["t"])
    assert store.claim("a") is True
    assert store.claim("a") is False
    assert store.claim("b") is True
    clock["t"] = 9.9
    assert store.claim("a") is False
    clock["t"] = 10.1
    assert store.claim("a") is True  # expired, claimable again
    store.release("b")
    assert store.claim("b") is True
    store.release("never-seen")  # no error


def test_deliver_with_retries_success_after_failures_and_backoff():
    calls, sleeps, dead = [], [], []

    def handler(event):
        calls.append(event)
        if len(calls) < 3:
            raise ConnectionError("boom")

    assert ex.deliver_with_retries(handler, {"id": 1}, dead, max_attempts=4, sleep=sleeps.append)
    assert len(calls) == 3 and sleeps == [1, 2] and dead == []


def test_deliver_with_retries_dead_letters_after_max_attempts():
    sleeps, dead = [], []

    def handler(event):
        raise ValueError("poison")

    assert (
        ex.deliver_with_retries(handler, {"id": 7}, dead, max_attempts=3, sleep=sleeps.append)
        is False
    )
    assert sleeps == [1, 2]  # no sleep after the last attempt
    assert dead == [{"event": {"id": 7}, "error": "poison", "attempts": 3}]


def make_receiver():
    events: queue.Queue = queue.Queue(maxsize=2)
    store = ex.IdempotencyStore(ttl=3600, clock=lambda: NOW)
    app = ex.build_receiver(SECRET, events, store, now=lambda: NOW)
    return TestClient(app), events


def post(client, body=BODY, hdr=None):
    return client.post("/webhooks", content=body, headers={"X-Signature": hdr or header(body=body)})


def test_receiver_accepts_valid_event_and_enqueues():
    client, events = make_receiver()
    resp = post(client)
    assert resp.status_code == 202 and resp.json() == {"status": "accepted"}
    assert events.get_nowait()["id"] == "evt_1"


def test_receiver_rejects_bad_signature_and_replay_without_enqueue():
    client, events = make_receiver()
    assert post(client, hdr=header(secret="wrong")).status_code == 401
    assert post(client, hdr=header(ts=NOW - 1000)).status_code == 401
    assert client.post("/webhooks", content=BODY).status_code == 401
    assert events.empty()


def test_receiver_dedupes_and_validates_payload():
    client, events = make_receiver()
    assert post(client).status_code == 202
    dup = post(client)
    assert dup.status_code == 200 and dup.json() == {"status": "duplicate"}
    assert events.qsize() == 1
    assert post(client, body=b"not json").status_code == 400
    assert post(client, body=json.dumps({"type": "no id"}).encode()).status_code == 400


def test_receiver_releases_id_when_queue_is_full():
    client, events = make_receiver()
    for i in range(2):
        assert post(client, body=json.dumps({"id": f"e{i}"}).encode()).status_code == 202
    full = json.dumps({"id": "e2"}).encode()
    assert post(client, body=full).status_code == 503
    events.get_nowait()  # make room, then the sender's retry must be accepted (id was released)
    assert post(client, body=full).status_code == 202
