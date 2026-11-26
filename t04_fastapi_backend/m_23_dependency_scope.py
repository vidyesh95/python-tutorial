# Dependency Scope: When Does Cleanup Run?
"""
A `yield` dependency has two halves: SETUP (before `yield`) and CLEANUP (after it). The
question this lesson answers is WHEN the cleanup half runs. `Depends(..., scope=...)` picks:

    conn: Annotated[Conn, Depends(get_conn)]                    # scope="request" (default)
    conn: Annotated[Conn, Depends(get_conn, scope="function")]  # early exit

- "request" (default): cleanup runs AFTER the response was sent (and after any background
  tasks - observed on FastAPI 0.165). The resource lives for the whole request/response cycle.
- "function": cleanup runs right after the handler function returns, BEFORE the response is
  sent. The resource lives only "around" your handler.

Why "function" matters: a DB connection or lock held by a "request" dependency stays checked
out while a big JSON body is serialized, a slow client downloads, or a background task runs.
Under load that starves the pool. If the handler has already read everything it needs, release
the resource early.

Why "request" is the default: the response may still need the resource. A StreamingResponse
pulls rows lazily AFTER the handler returned; with scope="function" the connection is already
closed by then (the demo shows the stream seeing a closed connection).

Sub-dependency rules (enforced when the route is registered, not at request time):
- A request-scoped yield dependency may only depend on request-scoped ones. Depending on a
  function-scoped one raises `DependencyScopeError` immediately.
- A function-scoped dependency may depend on both. Cleanup runs in reverse order of setup,
  so the function-scoped one closes first and can still use its request-scoped child.

Exceptions: anything the handler raises (including HTTPException) is thrown into the
generator at the `yield`, in both scopes. Catch it only to log or roll back, then re-raise
(plain `raise`). Swallowing it gives the client a bare 500 with nothing in the server log.

Serve it live:  uv run fastapi dev t04_fastapi_backend/m_23_dependency_scope.py
Run the offline demo: uv run python -m t04_fastapi_backend.m_23_dependency_scope
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.exceptions import DependencyScopeError
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

app = FastAPI(title="Dependency scope")

# Append-only log: the single source of truth for "what ran when" in this lesson.
EVENTS: list[str] = []


def log(event: str) -> None:
    EVENTS.append(event)


# Example: a fake connection and a yield dependency that logs its whole life
class Conn:
    def __init__(self) -> None:
        self.closed = False

    def rows(self) -> list[int]:
        return [1, 2, 3]


def get_conn() -> Iterator[Conn]:
    conn = Conn()
    log("conn open")
    try:
        yield conn
    except Exception as exc:  # see what the handler raised, then let it continue
        log(f"conn saw {type(exc).__name__}")
        raise  # ALWAYS re-raise, or the error vanishes and the client gets a bare 500
    finally:
        conn.closed = True
        log("conn close")


# The SAME function used with two scopes: only the Depends(...) call site differs.
RequestConn = Annotated[Conn, Depends(get_conn)]  # default scope="request"
EarlyConn = Annotated[Conn, Depends(get_conn, scope="function")]


def after_response() -> None:
    log("background task (response already sent)")


# Example: default scope - conn stays open through the response and background tasks
@app.get("/request-scope")
def request_scope(conn: RequestConn, tasks: BackgroundTasks) -> dict[str, list[int]]:
    log("handler")
    tasks.add_task(after_response)
    return {"rows": conn.rows()}


# Example: function scope - conn is released BEFORE the response goes out
@app.get("/function-scope")
def function_scope(conn: EarlyConn, tasks: BackgroundTasks) -> dict[str, list[int]]:
    log("handler")
    tasks.add_task(after_response)
    return {"rows": conn.rows()}


def stream_rows(conn: Conn) -> Iterator[bytes]:
    for row in conn.rows():
        log(f"stream row {row} (conn {'closed' if conn.closed else 'open'})")
        yield f"{row}\n".encode()


# Example: streaming NEEDS request scope - the generator runs after the handler returned
@app.get("/stream-request")
def stream_request(conn: RequestConn) -> StreamingResponse:
    log("handler")
    return StreamingResponse(stream_rows(conn))


# Example: the classic mistake - function scope + lazy stream = reading a closed resource
@app.get("/stream-function")
def stream_function(conn: EarlyConn) -> StreamingResponse:
    log("handler")
    return StreamingResponse(stream_rows(conn))


# Example: a function-scoped dependency built on a request-scoped one
def get_tx(conn: RequestConn) -> Iterator[str]:
    log("tx begin")
    try:
        yield "tx-1"
    finally:
        log("tx end")  # runs while conn is still open


@app.get("/nested")
def nested(
    tx: Annotated[str, Depends(get_tx, scope="function")], tasks: BackgroundTasks
) -> dict[str, str]:
    log("handler")
    tasks.add_task(after_response)
    return {"tx": tx}


# Example: errors reach the dependency in BOTH scopes
@app.get("/fail/request")
def fail_request(conn: RequestConn) -> None:
    raise HTTPException(404, "nope")


@app.get("/fail/function")
def fail_function(conn: EarlyConn) -> None:
    raise HTTPException(404, "nope")


# Example: the sub-dependency rule is checked at registration time
def request_scope_violation() -> DependencyScopeError | None:
    def parent(c: Annotated[Conn, Depends(get_conn, scope="function")]) -> Iterator[int]:
        yield 1  # a request-scoped (default) yield dependency...

    bad_app = FastAPI()
    try:

        @bad_app.get("/bad")  # ...cannot depend on a function-scoped one
        def bad(p: Annotated[int, Depends(parent)]) -> None: ...

    except DependencyScopeError as exc:
        return exc
    return None


"""
Common mistakes:
- Using scope="function" with StreamingResponse / FileResponse / lazy iterators that touch the
  resource: it is already closed when the body is produced.
- Leaving the default scope on a long-lived download or a handler that schedules slow
  background tasks: the DB connection stays checked out the whole time.
- `except SomeError:` in a yield dependency without re-raising (see the docs' "Britney" case).
- Expecting cleanup errors to change the status code: cleanup runs after (or around) the
  response is built; request-scope cleanup errors happen after it was already sent.
- Assuming a request-scoped dependency can build on a function-scoped one. It cannot.

Production notes:
- Safe default: leave "request" alone. Switch to "function" deliberately, for pooled
  resources (DB sessions, locks, semaphores) in handlers that return fully-built data and
  then spend noticeable time serializing, streaming from elsewhere, or running background work.
- With function scope, commit/rollback happens before the client sees the response, so a
  commit failure can still become a proper 5xx instead of "200 sent, then it failed".
- `Depends(..., max_concurrency=N)` counts a call until the code after `yield` finishes, so
  scope decides how long a slot is occupied.
- Order is observable, so test it: an append-only event list (as here) catches regressions.
"""


def run(path: str) -> list[str]:
    """Hit one route with a fresh log and return the events it produced."""
    EVENTS.clear()
    TestClient(app).get(path)
    return list(EVENTS)


if __name__ == "__main__":
    for route in (
        "/request-scope",
        "/function-scope",
        "/stream-request",
        "/stream-function",
        "/nested",
        "/fail/request",
        "/fail/function",
    ):
        print(f"{route:18}", run(route))
    print("registration:", request_scope_violation())
