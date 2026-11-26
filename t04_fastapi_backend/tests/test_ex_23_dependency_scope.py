import pytest

pytest.importorskip("fastapi")
from fastapi.exceptions import DependencyScopeError
from fastapi.testclient import TestClient

from _loader import load

ex = load("t04_fastapi_backend", "ex_23_dependency_scope")
client = TestClient(ex.app)


@pytest.fixture(autouse=True)
def _reset():
    ex.EVENTS.clear()
    yield
    ex.EVENTS.clear()


def test_get_conn_generator_lifecycle():
    gen = ex.get_conn()
    conn = next(gen)
    assert isinstance(conn, ex.Conn) and not conn.closed
    assert ex.EVENTS == ["conn open"]
    with pytest.raises(StopIteration):
        next(gen)
    assert conn.closed
    assert ex.EVENTS == ["conn open", "conn close"]


def test_get_conn_closes_on_error():
    gen = ex.get_conn()
    conn = next(gen)
    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("boom"))
    assert conn.closed


def test_report_releases_conn_before_response():
    r = client.get("/report")
    assert r.json() == {"rows": [1, 2, 3]}
    assert ex.EVENTS == ["conn open", "handler", "conn close", "background"]


def test_export_streams_with_conn_still_open():
    r = client.get("/export")
    assert r.text == "1\n2\n3\n"
    assert ex.EVENTS == [
        "conn open",
        "handler",
        "row 1",
        "row 2",
        "row 3",
        "conn close",
    ]


def test_get_tx_generator_lifecycle():
    conn = ex.Conn()
    gen = ex.get_tx(conn)  # plain generator function: call it directly
    assert next(gen) == "tx-1"
    with pytest.raises(StopIteration):
        next(gen)
    assert ex.EVENTS == ["tx begin", "tx end"]


def test_transfer_tx_closes_before_request_scoped_conn():
    r = client.get("/transfer")
    assert r.json() == {"tx": "tx-1"}
    assert ex.EVENTS == [
        "conn open",
        "tx begin",
        "handler",
        "tx end",
        "background",
        "conn close",
    ]


def test_scope_violation_is_rejected_at_registration():
    err = ex.scope_violation()
    assert isinstance(err, DependencyScopeError)
    assert "cannot depend on dependencies with scope" in str(err)
