"""Reference solution for Exercise 05: Dependency injection."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query

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


def pagination_params(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> dict[str, int]:
    return {"skip": skip, "limit": limit}


def get_db() -> Iterator[FakeDB]:
    db = FakeDB()
    try:
        yield db
    finally:
        db.close()


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


class UserFilter:
    def __init__(self, q: str | None = None, active_only: bool = False) -> None:
        self.q = q
        self.active_only = active_only

    def matches(self, user: dict) -> bool:
        if self.q is not None and self.q.lower() not in user["name"].lower():
            return False
        return not self.active_only or bool(user["active"])


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
    return {"message": f"Hello, {user['name']}!"}
