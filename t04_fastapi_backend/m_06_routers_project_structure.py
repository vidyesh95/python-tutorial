# Routers and Project Structure
"""
One file stops scaling quickly. `APIRouter` is a mini-app: you declare routes on it with the
same decorators, then `app.include_router(router, prefix=..., tags=..., dependencies=...)`.

What a router can carry (set on `APIRouter(...)` or on `include_router(...)`):
- `prefix="/users"`: prepended to every route path ("/" inside -> "/users").
- `tags=["users"]`: groups endpoints in /docs.
- `dependencies=[Depends(...)]`: runs for every route (auth, rate limiting).
- `responses={404: {...}}`: documented extra responses.
Routers can include other routers (nest them), and the same router can be mounted under
several prefixes (e.g. "/v1" and "/v2").

Recommended layout for a real service (this lesson squeezes it into one file):

    myapp/
    +-- pyproject.toml
    +-- alembic/ + alembic.ini        # migrations (lesson 08)
    +-- src/myapp/
    |   +-- main.py                   # create app, include routers, lifespan
    |   +-- config.py                 # Settings (pydantic-settings, lesson 19)
    |   +-- database.py               # engine, SessionLocal, get_db dependency
    |   +-- dependencies.py           # get_current_user, pagination...
    |   +-- models/                   # SQLAlchemy ORM classes
    |   |   +-- user.py
    |   +-- schemas/                  # Pydantic request/response models
    |   |   +-- user.py
    |   +-- routers/                  # HTTP layer: parse, call service, return
    |   |   +-- users.py              # router = APIRouter(prefix="/users", tags=["users"])
    |   |   +-- items.py
    |   +-- services/                 # business logic, no FastAPI imports
    |       +-- users.py
    +-- tests/
        +-- conftest.py               # TestClient + dependency overrides
        +-- test_users.py

Rule of thumb: routers are thin (HTTP in/out), services hold the logic, models/schemas
describe data. Dependencies flow downward; nothing imports `main.py`.

Serve it live:  uv run fastapi dev t04_fastapi_backend/m_06_routers_project_structure.py
Run the offline demo: uv run python -m t04_fastapi_backend.m_06_routers_project_structure
"""

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

USERS = {1: "ada", 2: "grace"}
ITEMS = {1: "keyboard"}


# Example: a router for one resource (in a real project: routers/users.py)
users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("")  # -> GET /users (with the prefix applied)
def list_users() -> list[str]:
    return list(USERS.values())


@users_router.get("/{user_id}")
def get_user(user_id: int) -> dict[str, int | str]:
    if user_id not in USERS:
        raise HTTPException(404, "User not found")
    return {"id": user_id, "name": USERS[user_id]}


# Example: a second router (routers/items.py), mounted without its own prefix
items_router = APIRouter(tags=["items"])


@items_router.get("/items")
def list_items() -> list[str]:
    return list(ITEMS.values())


# Example: router-level dependency protects every route inside it
def require_admin(x_admin: Annotated[str | None, Header()] = None) -> None:
    if x_admin != "yes":
        raise HTTPException(403, "Admins only")


admin_router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@admin_router.get("/stats")
def stats() -> dict[str, int]:
    return {"users": len(USERS), "items": len(ITEMS)}


# Example: the app factory (main.py) assembles everything under a version prefix
def create_app() -> FastAPI:
    app = FastAPI(title="Structured App")
    api = APIRouter(prefix="/api/v1")  # nested: routers inside a router
    api.include_router(users_router)
    api.include_router(items_router)
    api.include_router(admin_router)
    app.include_router(api)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


"""
Common mistakes:
- Circular imports (routers import main, main imports routers). Routers must never import
  the app; the app imports routers.
- Forgetting `app.include_router(...)`: the routes silently don't exist (404).
- Putting prefix both on the router and in `include_router` and ending up with /api/api/...
- Fat routers: SQL, hashing and business rules inside handlers make them untestable.
- Trailing-slash surprises: define "" (not "/") for a collection under a prefix, so the
  URL is "/users" and not "/users/".

Production notes:
- Use an app factory (`create_app()`) so tests can build fresh, isolated apps.
- Version early (/api/v1); mount v2 side by side when you must break the contract.
- Unique `operation_id`s and tags give nicer generated client SDKs.
- Keep `main.py` boring: configuration, routers, middleware, exception handlers, lifespan.
"""

if __name__ == "__main__":
    client = TestClient(app)
    print(client.get("/api/v1/users").json())
    print(client.get("/api/v1/users/1").json())
    print(client.get("/api/v1/items").json())
    print(client.get("/api/v1/admin/stats").status_code)  # 403
    print(client.get("/api/v1/admin/stats", headers={"X-Admin": "yes"}).json())
    print(client.get("/health").json())
    # Inspect what got mounted via the OpenAPI schema (app.routes nests included routers)
    print(list(app.openapi()["paths"]))
