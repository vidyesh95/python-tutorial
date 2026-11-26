# Request Body Limits, Form Limits and Strict Content-Type
"""
Three cheap defences that belong on every public API, all built into FastAPI 0.165:

1. TOTAL BODY SIZE: `max_body_size` (bytes) on `FastAPI(...)`, `APIRouter(...)`,
   `include_router(...)` or a single path operation. The most specific one wins, so a big
   upload route can RAISE the app default and a tiny route can lower it. `None` (the
   default) inherits; if nothing sets a limit the body is UNLIMITED; `0` allows only an
   empty body. FastAPI counts the bytes it actually reads, so a client that lies about (or
   omits) Content-Length, e.g. chunked transfer, is still stopped. Over the limit => 413.
   Everything in the body counts: JSON, form fields, file contents and multipart framing.

2. FORM / MULTIPART LIMITS: `form_limits={"max_fields": ..., "max_files": ...,
   "max_part_size": ...}` on the same places (each key inherits independently).
   Defaults: 1000 fields, 1000 files, 1 MiB per text field. `max_part_size` applies to
   text fields only; files are bounded by `max_body_size`. Over a form limit => 400.

3. STRICT CONTENT-TYPE (`strict_content_type`, default True, added in 0.132): a JSON body
   is only parsed as JSON when Content-Type is `application/json` or `application/*+json`.
   Missing or `text/plain` => the raw text is NOT parsed, validation fails => 422 (not 415).
   Set `strict_content_type=False` on `FastAPI(...)` or `APIRouter(...)` (NOT per route, and
   not on include_router) to accept a MISSING header as JSON (`text/plain` still fails).

Why it matters
- DoS: without a cap one client can make you buffer gigabytes (or 1M tiny form fields).
- CSRF: a browser page on evil.example can `fetch()` a Blob with NO Content-Type and no
  credentials WITHOUT a CORS preflight. If your API trusts the network (localhost,
  internal, no auth) that request would be accepted as JSON. Strict checking rejects it.
  Pairs with m_13 (CORS only helps if the browser sends a preflight).

Serve it live:  uv run fastapi dev t04_fastapi_backend/m_24_request_limits_strict_content_type.py
Run the offline demo:  uv run python -m t04_fastapi_backend.m_24_request_limits_strict_content_type

Common mistakes
- Checking `Content-Length` in a dependency: it can be absent or false. Use `max_body_size`.
- Forgetting multipart framing counts: a 10 KiB file needs a limit a bit above 10 KiB.
- Expecting 415 for a wrong Content-Type: FastAPI answers 422 (body not parsed as JSON).
- Setting a big global limit "to be safe", then forgetting the JSON routes need a small one.
- Turning `strict_content_type` off app-wide for one legacy client; use a dedicated router.
- Middleware that calls `await request.body()` runs under the APP limit, before the
  router's higher limit is known. Raise the app limit and lower it on other routes.

Production notes
- ALSO limit at the reverse proxy (nginx `client_max_body_size`, Caddy `request_body
  max_size`, ALB/API gateway limits): the proxy rejects before Python spends any CPU or
  memory, and also covers slow-body attacks (set proxy read timeouts too).
- Stream big uploads to object storage (presigned URLs, see m_09/m_18 style infra) rather
  than through the API; keep the API limit for small JSON.
- Log 413/400/422 rates per client; a spike is an attack or a broken integration.
"""

from typing import Annotated

from fastapi import APIRouter, FastAPI, Form, UploadFile
from fastapi.testclient import TestClient
from pydantic import BaseModel

KiB = 1024

# App-wide default: small. Fine for JSON APIs, far too small for uploads.
app = FastAPI(title="Limits", max_body_size=1 * KiB)

# Uploads get a bigger limit of their own (router level)...
uploads = APIRouter(prefix="/uploads", max_body_size=64 * KiB)

# (A single route can override its router too: see `/uploads/avatar` below.)

# A legacy client that cannot send Content-Type: opt that one router out of strict mode.
legacy = APIRouter(prefix="/legacy", strict_content_type=False)


class Item(BaseModel):
    name: str


@app.post("/items")
def create_item(item: Item) -> Item:
    return item  # JSON: Content-Type must be application/json; body <= 1 KiB


@uploads.post("/")
def upload(file: UploadFile) -> dict[str, object]:
    return {"filename": file.filename, "size": file.size}  # body <= 64 KiB


@uploads.post("/avatar", max_body_size=512)
def upload_avatar(file: UploadFile) -> dict[str, object]:
    return {"filename": file.filename, "size": file.size}  # body <= 512 bytes


@app.post("/notes", form_limits={"max_fields": 2, "max_part_size": 20})
def create_note(title: Annotated[str, Form()], body: Annotated[str, Form()] = "") -> dict[str, str]:
    return {"title": title, "body": body}  # <= 2 fields, each text field <= 20 bytes


@legacy.post("/items")
def create_item_legacy(item: Item) -> Item:
    return item  # a missing Content-Type is accepted here


app.include_router(uploads)
app.include_router(legacy)


if __name__ == "__main__":
    client = TestClient(app)
    ct_none = {"content-type": ""}  # httpx: omit the header entirely
    raw = b'{"name": "pen"}'

    print("--- JSON size (app limit 1 KiB)")
    print("small json       :", client.post("/items", json={"name": "pen"}).status_code)
    big = client.post("/items", json={"name": "x" * 2000})
    print("2000-char json   :", big.status_code, big.text)
    chunked = iter([b'{"name": "', b"x" * 2000, b'"}'])  # no Content-Length header
    r = client.post("/items", content=chunked, headers={"content-type": "application/json"})
    print("chunked 2000 char:", r.status_code, r.text, "(counted while reading)")

    print("--- uploads (router limit 64 KiB, /avatar 512 bytes)")
    print(
        "10 KiB file      :",
        client.post("/uploads/", files={"file": ("a.bin", b"x" * 10 * KiB)}).status_code,
    )
    print(
        "100 KiB file     :",
        client.post("/uploads/", files={"file": ("a.bin", b"x" * 100 * KiB)}).status_code,
    )
    print(
        "avatar 100 bytes :",
        client.post("/uploads/avatar", files={"file": ("a.png", b"x" * 100)}).status_code,
    )
    print(
        "avatar 1 KiB     :",
        client.post("/uploads/avatar", files={"file": ("a.png", b"x" * KiB)}).status_code,
    )

    print("--- form limits (2 fields, 20 bytes each)")
    print(
        "2 fields         :", client.post("/notes", data={"title": "hi", "body": "yo"}).status_code
    )
    r = client.post("/notes", data={"title": "hi", "body": "yo", "extra": "z"})
    print("3 fields         :", r.status_code, r.json()["detail"])
    r = client.post("/notes", data={"title": "t" * 50})
    print("50-byte field    :", r.status_code, r.json()["detail"])

    print("--- strict Content-Type")
    print(
        "application/json :",
        client.post(
            "/items", content=raw, headers={"content-type": "application/json"}
        ).status_code,
    )
    print(
        "vnd.api+json     :",
        client.post(
            "/items", content=raw, headers={"content-type": "application/vnd.api+json"}
        ).status_code,
    )
    print(
        "no Content-Type  :",
        client.post("/items", content=raw, headers=ct_none).status_code,
        "(strict: 422, not 415)",
    )
    print(
        "text/plain       :",
        client.post("/items", content=raw, headers={"content-type": "text/plain"}).status_code,
    )
    print(
        "legacy, no CT    :", client.post("/legacy/items", content=raw, headers=ct_none).status_code
    )
    print(
        "legacy, text/plain:",
        client.post(
            "/legacy/items", content=raw, headers={"content-type": "text/plain"}
        ).status_code,
    )
