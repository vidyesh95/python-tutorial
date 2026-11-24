"""Exercise 12: WebSockets.

Tasks
1. ConnectionManager.connect: accept the socket and remember it.
2. ConnectionManager.disconnect: forget a socket (no error if unknown).
3. ConnectionManager.broadcast: send text to every socket; drop sockets whose send fails.
4. chat endpoint: announce joins/leaves and broadcast every received line as "name: text".

Run: uv run pytest t04_fastapi_backend -k websockets
"""

from fastapi import FastAPI, WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Call `await websocket.accept()` and add it to `self.active`."""
        raise NotImplementedError

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove the socket from `self.active`. Unknown sockets are ignored."""
        raise NotImplementedError

    async def broadcast(self, message: str) -> None:
        """`send_text(message)` to every active socket.

        If sending to one socket raises, remove that socket and keep going.
        """
        raise NotImplementedError


def create_app(manager: ConnectionManager | None = None) -> FastAPI:
    app = FastAPI()
    mgr = manager or ConnectionManager()  # noqa: F841  (used by your chat handler)

    @app.websocket("/ws/{name}")
    async def chat(websocket: WebSocket, name: str) -> None:
        """Connect, broadcast f"* {name} joined", then loop: for each text received broadcast
        f"{name}: {text}". On WebSocketDisconnect, disconnect and broadcast f"* {name} left".
        """
        raise NotImplementedError

    return app
