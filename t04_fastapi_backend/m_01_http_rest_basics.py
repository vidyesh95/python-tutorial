# HTTP and REST Basics
"""
HTTP is a request/response protocol. A request has a METHOD, a PATH, HEADERS and an
optional BODY. A response has a STATUS CODE, HEADERS and an optional BODY.

Methods (what you want to do with a resource):
    GET     read            safe, idempotent
    POST    create / action not idempotent (two POSTs -> two resources)
    PUT     replace         idempotent (same PUT twice == once)
    PATCH   partial update  usually not guaranteed idempotent
    DELETE  remove          idempotent (second call: already gone)
- "Safe" = no side effects. "Idempotent" = repeating it leaves the same final state.
  Idempotency is what makes retries after a network timeout safe.

Status code families:
    1xx info | 2xx success (200 OK, 201 Created, 204 No Content)
    3xx redirect (301, 304) | 4xx client error (400, 401, 403, 404, 409, 422, 429)
    5xx server error (500, 502, 503)

REST resource design:
- URLs name THINGS (nouns, plural): /books, /books/42 - not /getBook or /createBook.
- The method is the verb. Nest only when ownership is real: /authors/3/books.
- Return 201 + a `Location` header on create; 204 (no body) on delete.
- JSON bodies, `Content-Type: application/json`, `Authorization: Bearer <token>`.

This lesson shows both sides without a network:
- the SERVER side: a tiny FastAPI app (details in the next lessons)
- the CLIENT side: httpx with `MockTransport`, a fake server living inside the process

Run it:         uv run python -m t04_fastapi_backend.m_01_http_rest_basics
Serve it live:  uv run fastapi dev t04_fastapi_backend/m_01_http_rest_basics.py
"""

from http import HTTPStatus
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient

# Example: HTTPStatus gives names + phrases to numeric codes
print(HTTPStatus(404).phrase, HTTPStatus.CREATED.value, HTTPStatus.NO_CONTENT.is_success)

# Example: a tiny REST API for the "books" resource (in-memory store)
app = FastAPI(title="Books")
books: dict[int, dict[str, Any]] = {}
next_id = 1


@app.post("/books", status_code=201)  # POST creates -> 201 Created
def create_book(book: dict[str, Any], response: Response) -> dict[str, Any]:
    global next_id
    book_id, next_id = next_id, next_id + 1
    books[book_id] = {"id": book_id, **book}
    response.headers["Location"] = f"/books/{book_id}"  # where the new thing lives
    return books[book_id]


@app.get("/books/{book_id}")  # GET reads -> 200, or 404 if missing
def read_book(book_id: int) -> dict[str, Any]:
    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")
    return books[book_id]


@app.put("/books/{book_id}")  # PUT replaces: calling it twice == calling it once
def replace_book(book_id: int, book: dict[str, Any]) -> dict[str, Any]:
    books[book_id] = {"id": book_id, **book}
    return books[book_id]


@app.delete("/books/{book_id}", status_code=204)  # 204 = success, empty body
def delete_book(book_id: int) -> None:
    books.pop(book_id, None)  # idempotent: deleting twice is not an error here


# Example: client side with httpx and a MockTransport (no real network)
def fake_server(request: httpx.Request) -> httpx.Response:
    """Runs instead of a real server. Inspect the request, build a response."""
    if request.method == "GET" and request.url.path == "/ping":
        return httpx.Response(200, json={"pong": True}, headers={"X-Request-Id": "abc123"})
    if request.headers.get("Authorization") != "Bearer secret":
        return httpx.Response(401, json={"detail": "Not authenticated"})
    return httpx.Response(404, json={"detail": "Not found"})


def demo_client() -> None:
    with httpx.Client(transport=httpx.MockTransport(fake_server), base_url="http://api") as c:
        r = c.get("/ping", params={"verbose": 1})
        print(r.status_code, r.json(), r.headers["x-request-id"])  # header names: case-insensitive
        print(c.get("/private").status_code)  # 401: no credentials
        print(c.get("/private", headers={"Authorization": "Bearer secret"}).status_code)  # 404


"""
Common mistakes:
- Using GET for actions with side effects (crawlers and prefetchers will trigger them).
- Returning 200 with {"error": ...} instead of a real 4xx/5xx status.
- Mixing up 401 (who are you? - not authenticated) and 403 (I know you; not allowed).
- Verbs in URLs (/createBook) or singular/plural inconsistency (/book vs /books).
- Retrying a POST blindly after a timeout -> duplicate records. Use an idempotency key.
- Forgetting `Content-Type`; servers then can't parse your body.

Production notes:
- Prefer 422 for validation errors (FastAPI default) and 409 for conflicts (duplicates).
- Add timeouts to every client call: httpx.Client(timeout=5.0). The default is None-ish
  in many libraries, which hangs forever.
- Paginate collections (?limit=&offset= or cursors); never return unbounded lists.
- Version the API (/v1/...) before clients depend on it.
- Use `curl -i -X POST localhost:8000/books -H 'content-type: application/json' -d '{}'`
  to see raw status line + headers while debugging.
"""

if __name__ == "__main__":
    demo_client()

    client = TestClient(app)  # an httpx.Client wired straight to the ASGI app
    created = client.post("/books", json={"title": "Dune"})
    print(created.status_code, created.headers["location"], created.json())
    print(client.get("/books/1").json())
    print(client.put("/books/1", json={"title": "Dune Messiah"}).json())
    print(client.put("/books/1", json={"title": "Dune Messiah"}).json())  # same result: idempotent
    print(client.delete("/books/1").status_code, client.delete("/books/1").status_code)  # 204 204
    print(client.get("/books/1").status_code, client.get("/books/1").json())  # 404
