"""Exercise 24: Request body limits, form limits and strict Content-Type.

Tasks
1. create_app: app-level `max_body_size` and `strict_content_type`, a JSON route
   POST /items, and include the routers from tasks 2-4.
2. build_uploads_router: router at /uploads with its OWN (bigger) `max_body_size`;
   POST /uploads/ returns {"filename": ..., "size": ...}.
3. build_notes_router: POST /notes (Form `title`) with `form_limits` for `max_fields`
   and `max_part_size`.
4. build_legacy_router: router at /legacy that ALWAYS accepts a missing Content-Type
   (`strict_content_type=False`); POST /legacy/items takes the same JSON as /items.

Status codes to expect: body too large 413, form limit exceeded 400, JSON sent without
a JSON Content-Type 422.

Run: uv run pytest t04_fastapi_backend -k request_limits
"""

from typing import Annotated

from fastapi import APIRouter, FastAPI, Form, UploadFile
from pydantic import BaseModel


class Item(BaseModel):
    name: str


def build_uploads_router(max_upload_bytes: int) -> APIRouter:
    """APIRouter(prefix="/uploads", max_body_size=max_upload_bytes) with POST "/".

    The handler takes `file: UploadFile` and returns {"filename": file.filename,
    "size": file.size}.
    """
    router = APIRouter(prefix="/uploads", max_body_size=max_upload_bytes)

    @router.post("/")
    def upload(file: UploadFile) -> dict[str, object]:
        return {"filename": file.filename, "size": file.size}

    return router


def build_notes_router(max_fields: int, max_part_size: int) -> APIRouter:
    """APIRouter with POST /notes taking a required Form `title` and an optional Form
    `body` (default ""). Pass form_limits={"max_fields": ..., "max_part_size": ...} to
    the router. Return {"title": ..., "body": ...}.
    """
    router = APIRouter(form_limits={"max_fields": max_fields, "max_part_size": max_part_size})

    @router.post("/notes")
    def create_note(
        title: Annotated[str, Form()], body: Annotated[str, Form()] = ""
    ) -> dict[str, str]:
        return {"title": title, "body": body}

    return router


def build_legacy_router() -> APIRouter:
    """APIRouter(prefix="/legacy", strict_content_type=False) with POST /items that
    takes an `Item` and returns it.
    """
    router = APIRouter(prefix="/legacy", strict_content_type=False)

    @router.post("/items")
    def create_item_legacy(item: Item) -> Item:
        return item

    return router


def create_app(
    max_json_bytes: int = 1024,
    max_upload_bytes: int = 64 * 1024,
    strict: bool = True,
    max_fields: int = 2,
    max_part_size: int = 20,
) -> FastAPI:
    """FastAPI(max_body_size=max_json_bytes, strict_content_type=strict) with
    POST /items (takes `Item`, returns it), plus the three routers above included.
    """
    app = FastAPI(max_body_size=max_json_bytes, strict_content_type=strict)

    @app.post("/items")
    def create_item(item: Item) -> Item:
        return item

    app.include_router(build_uploads_router(max_upload_bytes))
    app.include_router(build_notes_router(max_fields, max_part_size))
    app.include_router(build_legacy_router())
    return app
