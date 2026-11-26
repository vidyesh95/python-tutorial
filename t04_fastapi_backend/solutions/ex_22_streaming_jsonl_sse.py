"""Exercise 22: Streaming with JSON Lines and Server-Sent Events.

Tasks
1. stream_items: JSONL stream. Yield each Item from ITEMS (first `limit` items if given).
2. stream_job: SSE progress stream with resume. Yield a ServerSentEvent for steps 1..total
   (event="progress", id=str(step), data={"step": step, "total": total}), skipping steps up to
   and including the `Last-Event-ID` header, then a final ServerSentEvent(raw_data="[DONE]",
   event="done").
3. stream_chat: SSE over POST. One ServerSentEvent(data=word, event="token") per word of the
   prompt text, then the same "done" event as in task 2.
4. parse_sse: client side. Turn an SSE body into a list of frame dicts (see docstring).

Run: uv run pytest t04_fastapi_backend -k ex_22
"""

from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import FastAPI, Header
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel


class Item(BaseModel):
    name: str
    description: str | None = None


class Prompt(BaseModel):
    text: str


ITEMS = [
    Item(name="Plumbus", description="A multi-purpose household device."),
    Item(name="Portal Gun", description="A portal opening device."),
    Item(name="Meeseeks Box"),
]


async def stream_items(limit: int | None = None) -> AsyncIterable[Item]:
    """Yield the items from ITEMS (only the first `limit` when `limit` is not None)."""
    for item in ITEMS[:limit]:
        yield item


async def stream_job(
    total: int = 3,
    last_event_id: Annotated[int | None, Header()] = None,
) -> AsyncIterable[ServerSentEvent]:
    """Progress events for steps 1..total, resuming after `Last-Event-ID`, then "done"."""
    for step in range(1, total + 1):
        if last_event_id is not None and step <= last_event_id:
            continue
        yield ServerSentEvent(data={"step": step, "total": total}, event="progress", id=str(step))
    yield ServerSentEvent(raw_data="[DONE]", event="done")


async def stream_chat(prompt: Prompt) -> AsyncIterable[ServerSentEvent]:
    """One "token" event per word in prompt.text, then ServerSentEvent(raw_data="[DONE]",
    event="done")."""
    for word in prompt.text.split():
        yield ServerSentEvent(data=word, event="token")
    yield ServerSentEvent(raw_data="[DONE]", event="done")


def parse_sse(body: str) -> list[dict[str, str]]:
    """Parse an SSE body into one dict per frame (frames are separated by a blank line).

    - "name: value" lines become {name: value} (strip ONE space after the colon).
    - Lines starting with ":" are comments, stored under the key "comment".
    - Several "data" lines in one frame are joined with "\\n".
    - Keys appear only if present in the frame. Values stay strings (id and retry too).
    Example: 'event: a\\ndata: 1\\nid: 5\\n\\n: ping\\n\\n' ->
             [{"event": "a", "data": "1", "id": "5"}, {"comment": "ping"}]
    """
    frames: list[dict[str, str]] = []
    for block in body.replace("\r\n", "\n").split("\n\n"):
        frame: dict[str, str] = {}
        for line in block.split("\n"):
            if not line:
                continue
            if line.startswith(":"):
                name, value = "comment", line[1:].removeprefix(" ")
            else:
                name, _, value = line.partition(":")
                value = value.removeprefix(" ")
            frame[name] = f"{frame[name]}\n{value}" if name == "data" and name in frame else value
        if frame:
            frames.append(frame)
    return frames


def create_app() -> FastAPI:
    app = FastAPI()
    app.get("/items/stream")(stream_items)
    app.get("/jobs/events", response_class=EventSourceResponse)(stream_job)
    app.post("/chat/stream", response_class=EventSourceResponse)(stream_chat)
    return app
