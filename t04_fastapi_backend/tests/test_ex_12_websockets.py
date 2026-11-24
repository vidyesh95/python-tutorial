import asyncio

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from _loader import load

ex = load("t04_fastapi_backend", "ex_12_websockets")


class FakeSocket:
    def __init__(self, fail: bool = False) -> None:
        self.accepted = False
        self.sent: list[str] = []
        self.fail = fail

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, text: str) -> None:
        if self.fail:
            raise RuntimeError("connection closed")
        self.sent.append(text)


def test_connect_accepts_and_tracks():
    manager, sock = ex.ConnectionManager(), FakeSocket()
    asyncio.run(manager.connect(sock))
    assert sock.accepted and manager.active == [sock]


def test_disconnect_is_idempotent():
    manager, sock = ex.ConnectionManager(), FakeSocket()
    asyncio.run(manager.connect(sock))
    manager.disconnect(sock)
    manager.disconnect(sock)  # unknown now: no error
    assert manager.active == []


def test_broadcast_reaches_everyone_and_drops_dead_sockets():
    manager = ex.ConnectionManager()
    good, bad = FakeSocket(), FakeSocket(fail=True)

    async def scenario():
        await manager.connect(good)
        await manager.connect(bad)
        await manager.broadcast("hi")

    asyncio.run(scenario())
    assert good.sent == ["hi"]
    assert manager.active == [good]


def test_chat_endpoint_two_clients():
    manager = ex.ConnectionManager()
    client = TestClient(ex.create_app(manager))
    with client.websocket_connect("/ws/ada") as ada:
        assert ada.receive_text() == "* ada joined"
        with client.websocket_connect("/ws/bob") as bob:
            assert ada.receive_text() == "* bob joined"
            assert bob.receive_text() == "* bob joined"
            ada.send_text("hello")
            assert bob.receive_text() == "ada: hello"
            assert ada.receive_text() == "ada: hello"
        assert ada.receive_text() == "* bob left"
        assert len(manager.active) == 1
