"""Exercise 12: WebSockets.

Tasks
1. ConnectionManager.connect: accept the socket and remember it.
2. ConnectionManager.disconnect: forget a socket (no error if unknown).
3. ConnectionManager.broadcast: send text to every socket; drop sockets whose send fails.
4. chat endpoint: announce joins/leaves and broadcast every received line as "name: text".

Run: uv run pytest t04_fastapi_backend -k websockets
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Call `await websocket.accept()` and add it to `self.active`."""
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove the socket from `self.active`. Unknown sockets are ignored."""
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: str) -> None:
        """`send_text(message)` to every active socket.

        If sending to one socket raises, remove that socket and keep going.
        """
        for ws in list(self.active):
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(ws)


def create_app(manager: ConnectionManager | None = None) -> FastAPI:
    app = FastAPI()
    mgr = manager or ConnectionManager()

    @app.websocket("/ws/{name}")
    async def chat(websocket: WebSocket, name: str) -> None:
        """Connect, broadcast f"* {name} joined", then loop: for each text received broadcast
        f"{name}: {text}". On WebSocketDisconnect, disconnect and broadcast f"* {name} left".
        """
        await mgr.connect(websocket)
        await mgr.broadcast(f"* {name} joined")
        try:
            while True:
                text = await websocket.receive_text()
                await mgr.broadcast(f"{name}: {text}")
        except WebSocketDisconnect:
            mgr.disconnect(websocket)
            await mgr.broadcast(f"* {name} left")

    return app
