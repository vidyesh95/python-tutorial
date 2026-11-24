# Path, Query and Body Parameters
"""
FastAPI decides where each function parameter comes from by looking at its type hint:

- Name appears in the path ("/items/{item_id}")          -> PATH parameter (required)
- Scalar type (int, str, bool, Enum...) not in the path  -> QUERY parameter (?limit=5)
- Pydantic model (or `Body()`)                           -> JSON request BODY
- `list[...]` needs an explicit `Query()` to be a query list (?tag=a&tag=b)
- `Header()` / `Cookie()` read headers and cookies

Add validation with `Path`, `Query`, `Body`, `Header` - use the modern `Annotated` style:
    limit: Annotated[int, Query(ge=1, le=100)] = 10
- A default makes a query parameter optional; no default makes it required.
- `str | None = None` means optional with no value.
- Constraints: ge/gt/le/lt (numbers), min_length/max_length/pattern (strings).
- Failed validation -> automatic 422 response listing every problem (see next lesson).
- Body models are covered in depth in lesson 04; here just enough to combine all sources.

Serve it live:  uv run fastapi dev t04_fastapi_backend/m_03_path_query_body_params.py
Run the offline demo: uv run python -m t04_fastapi_backend.m_03_path_query_body_params
"""

from enum import StrEnum
from typing import Annotated

from fastapi import FastAPI, Header, Path, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel

app = FastAPI(title="Parameters")


# Example: path parameter with validation
@app.get("/items/{item_id}")
def read_item(item_id: Annotated[int, Path(ge=1, description="Database id")]) -> dict[str, int]:
    return {"item_id": item_id}


# Example: a fixed set of allowed path values via Enum (invalid value -> 422)
class Color(StrEnum):
    red = "red"
    blue = "blue"


@app.get("/colors/{color}")
def read_color(color: Color) -> dict[str, str]:
    return {"color": color.value}


# Example: a path that may contain slashes
@app.get("/files/{file_path:path}")
def read_file(file_path: str) -> dict[str, str]:
    return {"file_path": file_path}


# Example: query parameters - defaults, optional, constraints, repeatable list
@app.get("/search")
def search(
    q: Annotated[str, Query(min_length=2, max_length=50)],  # required
    limit: Annotated[int, Query(ge=1, le=100)] = 10,  # optional, default 10
    offset: int = 0,  # plain default, no extra rules
    tags: Annotated[list[str] | None, Query()] = None,  # ?tags=a&tags=b
    in_stock: bool = False,  # "true", "1", "yes", "on" all parse as True
) -> dict[str, object]:
    return {"q": q, "limit": limit, "offset": offset, "tags": tags, "in_stock": in_stock}


# Example: headers (underscores become hyphens: user_agent <-> User-Agent)
@app.get("/whoami")
def whoami(
    user_agent: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
) -> dict[str, str | None]:
    return {"user_agent": user_agent, "x_request_id": x_request_id}


# Example: path + query + body in one handler
class Item(BaseModel):
    name: str
    price: float


@app.put("/shop/{shop_id}/items")
def put_item(shop_id: int, item: Item, notify: bool = False) -> dict[str, object]:
    # shop_id -> path, item -> body (it's a model), notify -> query
    return {"shop_id": shop_id, "item": item.model_dump(), "notify": notify}


"""
Common mistakes:
- Expecting `list[str]` to be a query parameter without `Query()`: it becomes a body.
- Mutable defaults like `tags: list = []` - use `None` and Query(); never share mutable state.
- Declaring a catch-all route (`/items/{item_id}`) before a fixed one (`/items/count`):
  the first matching route wins, so the fixed path is never reached.
- Sending a body on GET and expecting every client/proxy to forward it. Use query params.
- Putting secrets (tokens, passwords) in query strings - they end up in logs and history.

Production notes:
- Always bound numeric and string inputs (`le=100`, `max_length`) to protect your database
  from huge `limit` values and giant strings.
- Prefer a `limit`/`offset` or cursor pair on every list endpoint.
- Header parameters are case-insensitive in HTTP; FastAPI converts underscores for you.
- For many related query params, use a Pydantic model: `Annotated[Filters, Query()]`.
"""

if __name__ == "__main__":
    client = TestClient(app)
    print(client.get("/items/5").json())
    print(client.get("/items/0").status_code)  # 422: ge=1 violated
    print(client.get("/colors/red").json(), client.get("/colors/green").status_code)
    print(client.get("/files/docs/readme.md").json())
    r = client.get("/search", params={"q": "py", "tags": ["a", "b"], "in_stock": "true"})
    print(r.json())
    print(client.get("/search", params={"q": "p"}).json()["detail"][0]["msg"])
    print(client.get("/whoami", headers={"X-Request-Id": "r-1"}).json())
    r = client.put("/shop/3/items", params={"notify": "1"}, json={"name": "pen", "price": 1.5})
    print(r.json())
