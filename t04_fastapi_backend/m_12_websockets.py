# WebSockets
"""
HTTP is request/response. A WebSocket is a long-lived, two-way connection: after one HTTP
"upgrade" handshake, either side can send messages at any time (chat, live dashboards,
notifications, collaborative editing).

    @app.websocket("/ws/{name}")
    async def chat(websocket: WebSocket, name: str):
        await websocket.accept()                  # complete the handshake
        try:
            while True:
                text = await websocket.receive_text()   # or receive_json()/receive_bytes()
                await websocket.send_text(f"echo: {text}")
        except WebSocketDisconnect:               # raised when the client goes away
            ...

A ConnectionManager keeps the set of live sockets so one client's message can be BROADCAST to
all of them. Message formats: text, bytes, or JSON (`send_json` / `receive_json`).

Run live:  uv run fastapi dev t04_fastapi_backend/m_12_websockets.py
Try it:    uvx websockets ws://127.0.0.1:8000/ws/ada   (or browser JS: new WebSocket(url))

Common mistakes
- Forgetting `accept()` (the client sees a failed handshake / 403).
- Not catching `WebSocketDisconnect`, so every normal disconnect logs a stack trace.
- Leaving dead sockets in the manager: the next broadcast raises. Remove on disconnect and
  drop sockets whose send fails.
- Blocking the event loop (sync I/O, CPU work) inside the handler: it freezes ALL sockets.
- Authenticating with a header the browser WebSocket API cannot set. Use a short-lived token
  in the query string or a first "auth" message, and validate BEFORE accept (close 1008).

Production notes
- The manager below lives in one process. With several workers/instances a message only
  reaches sockets on the same process; fan out through Redis pub/sub (m_15) or a broker.
- Sockets are stateful and long-lived: set idle timeouts, ping/pong keepalives, message size
  limits, and a per-connection rate limit. Close with a meaningful code (1008 policy, 1011).
- Load balancers need sticky-free WebSocket support and generous idle timeouts.
- For one-way server push, Server-Sent Events are often simpler than WebSockets.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient


# Example: a connection manager that broadcasts to everyone
class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: str) -> None:
        for ws in list(self.active):  # copy: we may remove while iterating
            try:
                await ws.send_text(message)
            except Exception:  # dead socket: forget it and keep going
                self.disconnect(ws)


app = FastAPI(title="WebSockets")
manager = ConnectionManager()


@app.websocket("/ws/{name}")
async def chat(websocket: WebSocket, name: str) -> None:
    await manager.connect(websocket)
    await manager.broadcast(f"* {name} joined")
    try:
        while True:
            text = await websocket.receive_text()
            await manager.broadcast(f"{name}: {text}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"* {name} left")


# Example: JSON messages and rejecting a client before accepting
@app.websocket("/ws-json")
async def json_echo(websocket: WebSocket, token: str = "") -> None:
    if token != "secret":
        await websocket.close(code=1008)  # policy violation: handshake refused
        return
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            await websocket.send_json({"received": data, "keys": sorted(data)})
    except WebSocketDisconnect:
        pass


@app.get("/")
def index() -> dict[str, int]:
    return {"connections": len(manager.active)}


if __name__ == "__main__":
    client = TestClient(app)

    # Two clients in one chat room
    with client.websocket_connect("/ws/ada") as ada:
        print("ada sees:", ada.receive_text())
        with client.websocket_connect("/ws/bob") as bob:
            print("ada sees:", ada.receive_text())  # bob's join is broadcast
            print("bob sees:", bob.receive_text())
            ada.send_text("hello bob")
            print("bob sees:", bob.receive_text())
            print("ada sees:", ada.receive_text())  # sender gets the broadcast too
        print("ada sees:", ada.receive_text())  # bob left (disconnect handled)

    # JSON endpoint, with and without the token
    with client.websocket_connect("/ws-json?token=secret") as ws:
        ws.send_json({"b": 1, "a": 2})
        print(ws.receive_json())
    try:
        with client.websocket_connect("/ws-json?token=wrong"):
            pass
    except WebSocketDisconnect as exc:
        print("rejected with close code", exc.code)
