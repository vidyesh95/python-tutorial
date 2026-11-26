# Dependency Injection
"""
A DEPENDENCY is a callable FastAPI runs BEFORE your handler; its return value is passed in.
    def handler(x: Annotated[Thing, Depends(get_thing)]): ...

Why: share logic (pagination, auth, DB sessions, settings) without copy-paste, and swap
real pieces for fakes in tests.

Kinds of dependency:
- FUNCTION: `def common_params(skip: int = 0, limit: int = 10) -> dict`. Its own parameters
  are parsed exactly like handler parameters (query, header, body...).
- CLASS: `Depends(Pagination)` - FastAPI calls the class; its `__init__` params are inputs.
- YIELD (generator): code before `yield` = setup, the yielded value is injected, code after
  `yield` (in `finally`) = cleanup that runs after the response. Perfect for DB sessions.
  See m_23 for `Depends(scope=...)` (when cleanup runs).
- SUB-DEPENDENCY: a dependency can itself depend on others; FastAPI resolves the graph.
- Non-value dependencies: `@app.get(..., dependencies=[Depends(check_key)])` runs for its
  side effect (auth check) and ignores the return value.

Per-request cache: if the same dependency appears twice in one request, it runs ONCE
(`Depends(dep, use_cache=False)` opts out).

Testing: `app.dependency_overrides[real_dep] = fake_dep` swaps a dependency (clear it after).

Serve it live:  uv run fastapi dev t04_fastapi_backend/m_05_dependency_injection.py
Run the offline demo: uv run python -m t04_fastapi_backend.m_05_dependency_injection
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

app = FastAPI(title="Dependencies")

EVENTS: list[str] = []  # lets the demo show the dependency lifecycle


# Example: function dependency (reusable pagination)
def pagination(skip: int = 0, limit: int = 10) -> dict[str, int]:
    return {"skip": skip, "limit": min(limit, 100)}  # clamp instead of trusting the client


# Example: class dependency - same idea, with behavior attached
class Search:
    def __init__(self, q: str | None = None, active: bool = True) -> None:
        self.q = q
        self.active = active


# Example: yield dependency = setup + guaranteed cleanup (think: DB session per request)
class FakeSession:
    def close(self) -> None:
        EVENTS.append("session closed")


def get_session() -> Iterator[FakeSession]:
    session = FakeSession()
    EVENTS.append("session opened")
    try:
        yield session  # handler runs here
    finally:
        session.close()  # runs even if the handler raised


# Example: sub-dependency chain: get_current_user -> needs the token header
def get_token(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    return authorization.removeprefix("Bearer ")


def get_current_user(token: Annotated[str, Depends(get_token)]) -> dict[str, str]:
    return {"name": "ada" if token == "ada-token" else "guest"}


# Annotated aliases keep signatures short and are reusable everywhere
Page = Annotated[dict[str, int], Depends(pagination)]
Session = Annotated[FakeSession, Depends(get_session)]
CurrentUser = Annotated[dict[str, str], Depends(get_current_user)]


@app.get("/items")
def list_items(page: Page, search: Annotated[Search, Depends()], session: Session):
    # `Depends()` with no argument uses the annotation's class (Search) as the dependency
    return {"page": page, "q": search.q, "active": search.active}


@app.get("/me")
def me(user: CurrentUser) -> dict[str, str]:
    return user


def require_admin_key(x_admin_key: Annotated[str | None, Header()] = None) -> None:
    if x_admin_key != "letmein":
        raise HTTPException(403, "Bad admin key")


@app.get("/admin", dependencies=[Depends(require_admin_key)])  # side-effect only
def admin() -> dict[str, str]:
    return {"secret": "42"}


"""
Common mistakes:
- Calling the dependency yourself: `Depends(get_db())` instead of `Depends(get_db)`.
- Doing cleanup after `return` in a regular function - use `yield` + `finally`.
- Forgetting to clear `app.dependency_overrides` after a test (it leaks into other tests).
- Heavy global state hidden in dependencies; keep them small, pure, and easy to fake.
- Using a dependency just to hold a constant: plain imports/settings are simpler.

Production notes:
- One DB session per request via a yield dependency is the standard pattern (lesson 07).
- Put cross-cutting checks (auth, rate limiting) on a router: `APIRouter(dependencies=[...])`
  or `FastAPI(dependencies=[...])` so no endpoint can forget them.
- Exceptions raised in a yield dependency's cleanup run AFTER the response was sent;
  they can't change the status code. Commit explicitly in the handler/service layer.
- `lru_cache` a settings factory (`get_settings`) so env parsing happens once.
"""

if __name__ == "__main__":
    client = TestClient(app)
    print(client.get("/items", params={"limit": 500, "q": "py"}).json())
    print(EVENTS)  # ['session opened', 'session closed']
    print(client.get("/me").status_code)  # 401 from the sub-dependency
    print(client.get("/me", headers={"Authorization": "Bearer ada-token"}).json())
    print(
        client.get("/admin").status_code,
        client.get("/admin", headers={"X-Admin-Key": "letmein"}).json(),
    )

    # Override: pretend someone is logged in, skipping the token entirely
    app.dependency_overrides[get_current_user] = lambda: {"name": "test-user"}
    print(client.get("/me").json())
    app.dependency_overrides.clear()
    print(client.get("/me").status_code)  # real dependency again -> 401
