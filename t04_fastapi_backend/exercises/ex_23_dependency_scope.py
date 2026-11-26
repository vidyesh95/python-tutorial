"""Exercise 23: Dependency scope (when does cleanup run?).

The routes exist; you implement the dependencies and choose the right scope for each handler.
The tests check the EXACT order of EVENTS.

Tasks
1. get_conn: a YIELD dependency. Create a Conn, log "conn open", yield it, and in a
   `finally` set conn.closed = True and log "conn close".
2. report (GET /report): the handler only needs the rows it reads immediately, so release
   the connection BEFORE the response is sent. Declare conn with scope="function".
   Body: log "handler", schedule after_response as a background task, return
   {"rows": conn.rows()}.
   Expected events: conn open, handler, conn close, background.
3. export (GET /export): return a StreamingResponse over the generator `stream_rows(conn)`
   (already written; it logs "row N" and reads conn lazily). The generator runs AFTER the
   handler returns, so conn must keep the DEFAULT (request) scope. Log "handler" first.
   Expected events: conn open, handler, row 1, row 2, row 3, conn close.
4. get_tx: a YIELD dependency that depends on get_conn (default scope). Log "tx begin",
   yield "tx-1", and in `finally` log "tx end".
5. transfer (GET /transfer): depend on get_tx with scope="function". Body: log "handler",
   schedule after_response, return {"tx": tx}.
   Expected events: conn open, tx begin, handler, tx end, background, conn close
   (the request-scoped conn outlives the function-scoped tx).
6. scope_violation: build a NEW FastAPI app and try to register a route whose request-scoped
   (default) YIELD dependency depends on a function-scoped yield dependency. FastAPI raises
   DependencyScopeError at registration time. Return that exception instance.

Run: uv run pytest t04_fastapi_backend -k ex_23
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.exceptions import DependencyScopeError
from fastapi.responses import StreamingResponse  # noqa: F401

app = FastAPI(title="Exercise 23")

EVENTS: list[str] = []  # append-only log; the tests assert its exact order


def log(event: str) -> None:
    EVENTS.append(event)


class Conn:
    def __init__(self) -> None:
        self.closed = False

    def rows(self) -> list[int]:
        return [1, 2, 3]


def after_response() -> None:
    log("background")


def get_conn() -> Iterator[Conn]:
    raise NotImplementedError


def get_tx(conn: Annotated[Conn, Depends(get_conn)]) -> Iterator[str]:
    raise NotImplementedError


def stream_rows(conn: Conn) -> Iterator[bytes]:
    for row in conn.rows():
        log(f"row {row}" if not conn.closed else f"row {row} on CLOSED conn")
        yield f"{row}\n".encode()


@app.get("/report")
def report(conn: Annotated[Conn, Depends(get_conn)], tasks: BackgroundTasks):
    raise NotImplementedError


@app.get("/export")
def export(conn: Annotated[Conn, Depends(get_conn)]):
    raise NotImplementedError


@app.get("/transfer")
def transfer(tx: Annotated[str, Depends(get_tx)], tasks: BackgroundTasks):
    raise NotImplementedError


def scope_violation() -> DependencyScopeError:
    raise NotImplementedError
