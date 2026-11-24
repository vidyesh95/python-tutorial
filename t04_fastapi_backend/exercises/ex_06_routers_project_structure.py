"""Exercise 06: Routers and project structure.

Build a small app out of routers.

Tasks
1. make_router(resource, data): return an APIRouter with prefix f"/{resource}" and
   tags=[resource], exposing
       GET ""           -> list of the dict's values
       GET "/{item_id}" -> data[item_id] or HTTPException(404, f"{resource} not found")
   Note: the handlers must read `data` from the closure (they are defined inside the factory).
2. make_admin_router(): APIRouter(prefix="/admin", tags=["admin"]) protected at ROUTER level
   by `require_admin` (dependencies=[Depends(require_admin)]), with
       GET "/stats" -> {"books": len(BOOKS), "authors": len(AUTHORS)}
3. create_app(): FastAPI(title="Library"); mount both resource routers and the admin router
   under the prefix "/api/v1"; add `GET /health` -> {"status": "ok"} at the root.
4. routes_by_tag(app): return {tag: sorted paths} using `app.openapi()["paths"]` (each path
   item maps methods to operations that have a "tags" list). Untagged operations go under
   "untagged". Return tags in sorted order.

Run: uv run pytest t04_fastapi_backend -k ex_06
"""

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException  # noqa: F401

BOOKS = {1: "Dune", 2: "Emma"}
AUTHORS = {1: "Herbert", 2: "Austen", 3: "Le Guin"}


def require_admin(x_admin: Annotated[str | None, Header()] = None) -> None:
    if x_admin != "yes":
        raise HTTPException(status_code=403, detail="Admins only")


def make_router(resource: str, data: dict[int, str]) -> APIRouter:
    raise NotImplementedError


def make_admin_router() -> APIRouter:
    raise NotImplementedError


def create_app() -> FastAPI:
    raise NotImplementedError


def routes_by_tag(app: FastAPI) -> dict[str, list[str]]:
    raise NotImplementedError
