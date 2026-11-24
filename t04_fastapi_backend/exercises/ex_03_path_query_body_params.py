"""Exercise 03: Path, query, header and body parameters.

The app is wired up. Edit each handler's SIGNATURE (declare where parameters come from and
their validation rules) and implement its body.

Tasks
1. search: GET /search. `q` required, 2-20 chars. `limit` int 1..50, default 10.
   `tags` an optional repeatable query list (?tags=a&tags=b).
   Return {"q": q, "limit": limit, "tags": tags or []}.
2. get_order: GET /orders/{order_id}. order_id must be >= 1. Return {"order_id": order_id}.
3. create_item: POST /items. Body is an `Item`; `quantity` is a query param >= 1, default 1.
   Return {"name": item.name, "total": item.price * quantity}.
4. whoami: GET /whoami. Read the `X-User` header (default "anonymous").
   Return {"user": <value>}.
5. replace_item: PUT /items/{item_id}. Body is an `Item`.
   Return {"item_id": item_id, "name": item.name, "price": item.price}.

Hint: `Annotated[int, Query(ge=1, le=50)] = 10`, `Annotated[str | None, Header()] = None`.

Run: uv run pytest t04_fastapi_backend -k ex_03
"""

from typing import Annotated  # noqa: F401

from fastapi import FastAPI, Header, Path, Query  # noqa: F401
from pydantic import BaseModel

app = FastAPI(title="Exercise 03")


class Item(BaseModel):
    name: str
    price: float


@app.get("/search")
def search(q: str, limit: int = 10, tags: list[str] | None = None) -> dict[str, object]:
    raise NotImplementedError


@app.get("/orders/{order_id}")
def get_order(order_id: int) -> dict[str, int]:
    raise NotImplementedError


@app.post("/items")
def create_item(item: Item, quantity: int = 1) -> dict[str, object]:
    raise NotImplementedError


@app.get("/whoami")
def whoami(x_user: str | None = None) -> dict[str, str]:
    raise NotImplementedError


@app.put("/items/{item_id}")
def replace_item(item_id: int, item: Item) -> dict[str, object]:
    raise NotImplementedError
