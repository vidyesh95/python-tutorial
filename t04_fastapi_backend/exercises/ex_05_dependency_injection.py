"""Exercise 05: Dependency injection.

The app and its routes are wired. Implement the dependencies and the `greet` handler.

Tasks
1. pagination_params: a dependency with query params `skip` (int >= 0, default 0) and
   `limit` (int 1..50, default 10). Return {"skip": skip, "limit": limit}.
2. get_db: a YIELD dependency. Create a `FakeDB()`, yield it, and ALWAYS call `.close()`
   afterwards (use try/finally).
3. require_api_key: read the `X-API-Key` header; raise HTTPException(401, "Invalid API key")
   unless it equals API_KEY. (Used on /admin via `dependencies=[...]`.)
4. UserFilter: a CLASS dependency. `__init__(self, q: str | None = None, active_only: bool = False)`
   stores both; `matches(user)` is True when q (case-insensitive) is a substring of
   user["name"] (or q is None) AND (not active_only or user["active"]).
5. greet: GET /greet -> {"message": f"Hello, {user['name']}!"} using the injected user.
   The test overrides `get_current_user`, so use the dependency, don't hardcode it.

Run: uv run pytest t04_fastapi_backend -k ex_05
"""

from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException  # noqa: F401

app = FastAPI(title="Exercise 05")

API_KEY = "s3cret"
ITEMS = list(range(1, 31))
USERS = [
    {"name": "Ada", "active": True},
    {"name": "Adam", "active": False},
    {"name": "Grace", "active": True},
]
EVENTS: list[str] = []


class FakeDB:
    closed = False

    def close(self) -> None:
        self.closed = True
        EVENTS.append("db closed")


def pagination_params(skip: int = 0, limit: int = 10) -> dict[str, int]:
    raise NotImplementedError


def get_db():
    raise NotImplementedError


def require_api_key(x_api_key: str | None = None) -> None:
    raise NotImplementedError


class UserFilter:
    def __init__(self, q: str | None = None, active_only: bool = False) -> None:
        raise NotImplementedError

    def matches(self, user: dict) -> bool:
        raise NotImplementedError


def get_current_user() -> dict[str, str]:
    return {"name": "world"}


Page = Annotated[dict[str, int], Depends(pagination_params)]
CurrentUser = Annotated[dict[str, str], Depends(get_current_user)]


@app.get("/items")
def list_items(page: Page) -> dict[str, object]:
    start = page["skip"]
    return {"page": page, "items": ITEMS[start : start + page["limit"]]}


@app.get("/db-check")
def db_check(db: Annotated[FakeDB, Depends(get_db)]) -> dict[str, bool]:
    return {"closed_during_request": db.closed}


@app.get("/admin", dependencies=[Depends(require_api_key)])
def admin() -> dict[str, str]:
    return {"secret": "42"}


@app.get("/users")
def list_users(f: Annotated[UserFilter, Depends()]) -> list[str]:
    return [u["name"] for u in USERS if f.matches(u)]


@app.get("/greet")
def greet(user: CurrentUser) -> dict[str, str]:
    raise NotImplementedError
