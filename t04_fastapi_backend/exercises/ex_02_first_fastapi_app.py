"""Exercise 02: Your first FastAPI app.

The app is already wired up below. Implement the four handler functions.

Tasks
1. read_root: GET /        -> {"message": "Hello, FastAPI"}
2. health:    GET /health  -> {"status": "ok"}
3. get_item:  GET /items/{item_id} -> {"id": item_id, "name": ITEMS[item_id]};
              raise HTTPException(404, "Item not found") for an unknown id.
4. count_items: GET /items/count (async) -> {"count": <number of ITEMS>}

Run: uv run pytest t04_fastapi_backend -k ex_02
"""

from fastapi import FastAPI, HTTPException  # noqa: F401  (HTTPException is for task 3)

ITEMS: dict[int, str] = {1: "keyboard", 2: "mouse", 3: "monitor"}

app = FastAPI(title="Exercise 02")


@app.get("/")
def read_root() -> dict[str, str]:
    raise NotImplementedError


@app.get("/health")
def health() -> dict[str, str]:
    raise NotImplementedError


# Note: "/items/count" is registered BEFORE "/items/{item_id}" on purpose. FastAPI matches
# routes in order, so a fixed path must come before a path with a parameter.
@app.get("/items/count")
async def count_items() -> dict[str, int]:
    raise NotImplementedError


@app.get("/items/{item_id}")
def get_item(item_id: int) -> dict[str, int | str]:
    raise NotImplementedError
