import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from _loader import load

ex = load("t04_fastapi_backend", "ex_11_background_tasks")


@pytest.fixture(autouse=True)
def clean_state():
    for store in (ex.OUTBOX, ex.AUDIT, ex.FAILURES):
        store.clear()
    yield


def test_send_welcome_appends_message():
    ex.send_welcome("a@b.co")
    assert ex.OUTBOX == [{"to": "a@b.co", "subject": "Welcome"}]


def test_send_welcome_rejects_bad_address():
    with pytest.raises(ValueError):
        ex.send_welcome("nope")
    assert ex.OUTBOX == []


def test_safe_send_welcome_swallows_errors():
    ex.safe_send_welcome("nope")  # must not raise
    assert ex.OUTBOX == []
    assert len(ex.FAILURES) == 1 and ex.FAILURES[0].startswith("nope: ")


def test_write_audit():
    ex.write_audit("a@b.co")
    assert ex.AUDIT == ["registered:a@b.co"]


def test_register_returns_202_and_runs_jobs():
    client = TestClient(ex.app)
    r = client.post("/register", json={"email": "a@b.co"})
    assert r.status_code == 202
    assert r.json() == {"status": "accepted"}
    assert ex.AUDIT == ["registered:a@b.co"]
    assert ex.OUTBOX == [{"to": "a@b.co", "subject": "Welcome"}]


def test_register_with_bad_email_still_accepted_but_recorded():
    client = TestClient(ex.app)
    r = client.post("/register", json={"email": "nope"})
    assert r.status_code == 202
    assert ex.OUTBOX == []
    assert len(ex.FAILURES) == 1
