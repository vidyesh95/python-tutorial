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


# NOTE: the bare `yield` after `raise` only makes each stub an async generator, which FastAPI
# needs to see to set up streaming. Replace both lines with your real implementation.
async def stream_items(limit: int | None = None) -> AsyncIterable[Item]:
    """Yield the items from ITEMS (only the first `limit` when `limit` is not None)."""
    raise NotImplementedError
    yield


async def stream_job(
    total: int = 3,
    last_event_id: Annotated[int | None, Header()] = None,
) -> AsyncIterable[ServerSentEvent]:
    """Progress events for steps 1..total, resuming after `Last-Event-ID`, then "done"."""
    raise NotImplementedError
    yield


async def stream_chat(prompt: Prompt) -> AsyncIterable[ServerSentEvent]:
    """One "token" event per word in prompt.text, then ServerSentEvent(raw_data="[DONE]",
    event="done")."""
    raise NotImplementedError
    yield


def parse_sse(body: str) -> list[dict[str, str]]:
    """Parse an SSE body into one dict per frame (frames are separated by a blank line).

    - "name: value" lines become {name: value} (strip ONE space after the colon).
    - Lines starting with ":" are comments, stored under the key "comment".
    - Several "data" lines in one frame are joined with "\\n".
    - Keys appear only if present in the frame. Values stay strings (id and retry too).
    Example: 'event: a\\ndata: 1\\nid: 5\\n\\n: ping\\n\\n' ->
             [{"event": "a", "data": "1", "id": "5"}, {"comment": "ping"}]
    """
    raise NotImplementedError


def create_app() -> FastAPI:
    app = FastAPI()
    app.get("/items/stream")(stream_items)
    app.get("/jobs/events", response_class=EventSourceResponse)(stream_job)
    app.post("/chat/stream", response_class=EventSourceResponse)(stream_chat)
    return app
