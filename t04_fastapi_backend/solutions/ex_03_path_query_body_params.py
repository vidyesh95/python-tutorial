"""Reference solution for Exercise 03: Path, query, header and body parameters."""

from typing import Annotated

from fastapi import FastAPI, Header, Path, Query
from pydantic import BaseModel

app = FastAPI(title="Exercise 03")


class Item(BaseModel):
    name: str
    price: float


@app.get("/search")
def search(
    q: Annotated[str, Query(min_length=2, max_length=20)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    tags: Annotated[list[str] | None, Query()] = None,
) -> dict[str, object]:
    return {"q": q, "limit": limit, "tags": tags or []}


@app.get("/orders/{order_id}")
def get_order(order_id: Annotated[int, Path(ge=1)]) -> dict[str, int]:
    return {"order_id": order_id}


@app.post("/items")
def create_item(item: Item, quantity: Annotated[int, Query(ge=1)] = 1) -> dict[str, object]:
    return {"name": item.name, "total": item.price * quantity}


@app.get("/whoami")
def whoami(x_user: Annotated[str, Header()] = "anonymous") -> dict[str, str]:
    return {"user": x_user}


@app.put("/items/{item_id}")
def replace_item(item_id: int, item: Item) -> dict[str, object]:
    return {"item_id": item_id, "name": item.name, "price": item.price}
