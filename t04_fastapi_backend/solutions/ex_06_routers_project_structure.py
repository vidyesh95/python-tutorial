"""Reference solution for Exercise 06: Routers and project structure."""

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException

BOOKS = {1: "Dune", 2: "Emma"}
AUTHORS = {1: "Herbert", 2: "Austen", 3: "Le Guin"}


def require_admin(x_admin: Annotated[str | None, Header()] = None) -> None:
    if x_admin != "yes":
        raise HTTPException(status_code=403, detail="Admins only")


def make_router(resource: str, data: dict[int, str]) -> APIRouter:
    router = APIRouter(prefix=f"/{resource}", tags=[resource])

    @router.get("")
    def list_all() -> list[str]:
        return list(data.values())

    @router.get("/{item_id}")
    def get_one(item_id: int) -> str:
        if item_id not in data:
            raise HTTPException(status_code=404, detail=f"{resource} not found")
        return data[item_id]

    return router


def make_admin_router() -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

    @router.get("/stats")
    def stats() -> dict[str, int]:
        return {"books": len(BOOKS), "authors": len(AUTHORS)}

    return router


def create_app() -> FastAPI:
    app = FastAPI(title="Library")
    api = APIRouter(prefix="/api/v1")
    api.include_router(make_router("books", BOOKS))
    api.include_router(make_router("authors", AUTHORS))
    api.include_router(make_admin_router())
    app.include_router(api)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def routes_by_tag(app: FastAPI) -> dict[str, list[str]]:
    result: dict[str, set[str]] = {}
    for path, item in app.openapi()["paths"].items():
        for operation in item.values():
            for tag in operation.get("tags") or ["untagged"]:
                result.setdefault(tag, set()).add(path)
    return {tag: sorted(paths) for tag, paths in sorted(result.items())}
