"""Reference solution for Exercise 23: Dependency scope."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.exceptions import DependencyScopeError
from fastapi.responses import StreamingResponse

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
    conn = Conn()
    log("conn open")
    try:
        yield conn
    finally:
        conn.closed = True
        log("conn close")


def get_tx(conn: Annotated[Conn, Depends(get_conn)]) -> Iterator[str]:
    log("tx begin")
    try:
        yield "tx-1"
    finally:
        log("tx end")


def stream_rows(conn: Conn) -> Iterator[bytes]:
    for row in conn.rows():
        log(f"row {row}" if not conn.closed else f"row {row} on CLOSED conn")
        yield f"{row}\n".encode()


@app.get("/report")
def report(
    conn: Annotated[Conn, Depends(get_conn, scope="function")], tasks: BackgroundTasks
) -> dict[str, list[int]]:
    log("handler")
    tasks.add_task(after_response)
    return {"rows": conn.rows()}


@app.get("/export")
def export(conn: Annotated[Conn, Depends(get_conn)]) -> StreamingResponse:
    # Default (request) scope: the generator reads conn after this function returns.
    log("handler")
    return StreamingResponse(stream_rows(conn))


@app.get("/transfer")
def transfer(
    tx: Annotated[str, Depends(get_tx, scope="function")], tasks: BackgroundTasks
) -> dict[str, str]:
    log("handler")
    tasks.add_task(after_response)
    return {"tx": tx}


def scope_violation() -> DependencyScopeError:
    def parent(c: Annotated[Conn, Depends(get_conn, scope="function")]) -> Iterator[int]:
        yield 1  # request-scoped by default

    bad_app = FastAPI()
    try:

        @bad_app.get("/bad")
        def bad(p: Annotated[int, Depends(parent)]) -> None: ...

    except DependencyScopeError as exc:
        return exc
    raise AssertionError("FastAPI should have rejected this route")
