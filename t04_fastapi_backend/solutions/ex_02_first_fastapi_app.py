"""Reference solution for Exercise 02: Your first FastAPI app."""

from fastapi import FastAPI, HTTPException

ITEMS: dict[int, str] = {1: "keyboard", 2: "mouse", 3: "monitor"}

app = FastAPI(title="Exercise 02")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, FastAPI"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/items/count")
async def count_items() -> dict[str, int]:
    return {"count": len(ITEMS)}


@app.get("/items/{item_id}")
def get_item(item_id: int) -> dict[str, int | str]:
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"id": item_id, "name": ITEMS[item_id]}
