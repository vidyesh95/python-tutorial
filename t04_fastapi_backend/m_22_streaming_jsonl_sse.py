# Streaming: JSON Lines and Server-Sent Events
"""
A normal response is built completely, then sent. A STREAM sends each item as soon as it is
produced, so the client can start working on item 1 while you compute item 2. FastAPI (0.134+
for JSONL, 0.135+ for SSE) turns an ordinary `yield` in a path operation into a stream.

JSON Lines (application/jsonl): one JSON object per line
    @app.get("/items/stream")
    async def stream_items() -> AsyncIterable[Item]:   # declare the item type
        for item in ITEMS:
            yield item                                 # yield instead of return

    {"name":"Plumbus","description":"..."}\\n{"name":"Portal Gun",...}\\n

  Contrast: `-> list[Item]` + `return items` builds the whole body first and sends one JSON
  array. Streaming starts sending at once and never holds all items in memory. With a return
  type, Pydantic validates/filters/serializes each item (fast, Rust side); without one,
  FastAPI falls back to jsonable_encoder. A plain `def` generator works too (-> Iterable[Item])
  and runs in the threadpool.

Server-Sent Events (text/event-stream): the same idea in a format browsers understand natively
(`new EventSource(url)`). Add `response_class=EventSourceResponse` and yield items or
`ServerSentEvent` objects. A frame is a few `field: value` lines ended by a blank line:
    ServerSentEvent(data=item, event="progress", id="3", retry=2000)
      -> event: progress / data: {...} / id: 3 / retry: 2000 / <blank>
  - `data` is ALWAYS JSON-encoded (even strings: "hi" is sent as `data: "hi"`). Use
    `raw_data="[DONE]"` for text that must not be encoded; `data` and `raw_data` are exclusive.
  - `event` names the event (EventSource.addEventListener(name, ...)); default is "message".
  - `id` is remembered by the browser and sent back as the `Last-Event-ID` header when it
    auto-reconnects, so declare `last_event_id: Annotated[int | None, Header()] = None` and
    resume after that id. `retry` is the reconnect delay in milliseconds.
  - `comment=` sends a `: text` line that clients ignore. FastAPI already sends `: ping` every
    15 s of silence and sets Cache-Control: no-cache and X-Accel-Buffering: no for you.
  - SSE works with any HTTP method (POST for chat prompts); browser EventSource only does GET.

SSE vs JSONL vs WebSockets (m_12)
- WebSocket: two-way, long-lived, custom protocol. Pick it when the client talks back a lot.
- SSE: one-way server push, auto-reconnect + resume built in, plain HTTP (proxies, auth, CORS).
  Pick it for notifications, progress, logs, LLM token streams to a browser.
- JSONL: one-way stream of records for programs (curl, httpx, data pipelines), no reconnect
  protocol. Pick it for exports and machine-to-machine feeds.

Serve it live: uv run fastapi dev t04_fastapi_backend/m_22_streaming_jsonl_sse.py
    curl -N http://127.0.0.1:8000/items/stream            # -N: do not buffer, see lines arrive
    curl -N http://127.0.0.1:8000/jobs/7/events
    curl -N -H "Last-Event-ID: 2" http://127.0.0.1:8000/jobs/7/events   # resume after id 2
    curl -N -X POST http://127.0.0.1:8000/chat/stream -H "content-type: application/json" \\
         -d '{"text": "hello streaming world"}'
Run the offline demo: uv run python -m t04_fastapi_backend.m_22_streaming_jsonl_sse

Dependencies with `yield` and streams
A `yield` dependency (m_05) stays open for the WHOLE stream by default (scope "request"): it
is cleaned up after the last item is sent, so the generator can use its DB session or client.
`Depends(dep, scope="function")` closes it as soon as the endpoint "returns", which for a
generator is BEFORE the first item is produced, so the generator would see a closed resource.
See m_23 for dependency scopes in depth; the demo below prints the order of events.

Common mistakes
- Returning a `list` (or building every item first) and calling it streaming.
- Parsing a JSONL body as one JSON document, or an SSE body as JSON. Parse line by line / frame
  by frame.
- Raising after the first item: the status code and headers are already sent, so the client
  sees a truncated stream, not a 500. Emit an error event/line yourself, and log.
- Blocking calls (time.sleep, sync I/O) inside an `async def` generator: use `await`.
- Forgetting that `Last-Event-ID` only helps if you assign `id`s and can replay from them.
- TestClient reads the whole body before returning; it checks content, not timing. Use
  `curl -N` (or a real client) to see items arrive incrementally.

Production notes
- Proxies and CDNs may buffer or time out. Keep `X-Accel-Buffering: no`, keep-alive comments,
  and generous idle timeouts; disable response compression buffering for streams.
- Every open stream holds a connection and a task. Cap concurrency, and stop the generator
  when the client disconnects (the cancellation arrives at your next `await`).
- Make ids monotonic and replayable (DB sequence, Redis stream) so resume is exact; fan out
  across workers with Redis pub/sub (m_15).
"""

import asyncio
from collections.abc import AsyncIterable, AsyncIterator
from typing import Annotated

from fastapi import Depends, FastAPI, Header
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.testclient import TestClient
from pydantic import BaseModel

app = FastAPI(title="Streaming: JSONL and SSE")


class Item(BaseModel):
    name: str
    description: str | None = None


ITEMS = [
    Item(name="Plumbus", description="A multi-purpose household device."),
    Item(name="Portal Gun", description="A portal opening device."),
    Item(name="Meeseeks Box"),
]


# Example: the same data as one JSON array vs a JSONL stream
@app.get("/items")
async def list_items() -> list[Item]:
    return ITEMS  # the whole body exists before the first byte is sent


@app.get("/items/stream")
async def stream_items() -> AsyncIterable[Item]:
    for item in ITEMS:
        yield item  # content type application/jsonl, one object per line
        await asyncio.sleep(0)  # stand-in for "wait for the next row/token"


# Example: SSE with event names, ids, retry, a comment, and Last-Event-ID resume
@app.get("/jobs/{job_id}/events", response_class=EventSourceResponse)
async def job_events(
    job_id: int,
    last_event_id: Annotated[int | None, Header()] = None,  # header "Last-Event-ID"
) -> AsyncIterable[ServerSentEvent]:
    yield ServerSentEvent(comment=f"job {job_id}", retry=2000)  # not delivered to listeners
    for step in range(1, 4):
        if last_event_id is not None and step <= last_event_id:
            continue  # the client already has this one
        yield ServerSentEvent(
            data={"job": job_id, "percent": step * 33}, event="progress", id=str(step)
        )
    yield ServerSentEvent(raw_data="[DONE]", event="done")  # raw: not JSON-encoded


# Example: SSE over POST (LLM-style token stream) with a plain-object `yield`
class Prompt(BaseModel):
    text: str


@app.post("/chat/stream", response_class=EventSourceResponse)
async def chat_stream(prompt: Prompt) -> AsyncIterable[ServerSentEvent]:
    for word in prompt.text.split():
        yield ServerSentEvent(data=word, event="token")  # sent as: data: "word"
    yield ServerSentEvent(raw_data="[DONE]", event="done")


@app.get("/ticks", response_class=EventSourceResponse)
async def ticks() -> AsyncIterable[Item]:
    for item in ITEMS[:2]:
        yield item  # plain objects become `data: {json}` frames, no event/id


# Example: when does a `yield` dependency clean up while streaming?
TRACE: list[str] = []


async def resource(label: str) -> AsyncIterator[str]:
    TRACE.append(f"{label}: open")
    yield label
    TRACE.append(f"{label}: close")


async def request_scoped() -> AsyncIterator[str]:
    async for value in resource("request-scope"):
        yield value


async def function_scoped() -> AsyncIterator[str]:
    async for value in resource("function-scope"):
        yield value


@app.get("/scopes")
async def scopes(
    a: Annotated[str, Depends(request_scoped)],  # default scope="request"
    b: Annotated[str, Depends(function_scoped, scope="function")],
) -> AsyncIterable[Item]:
    TRACE.append("generator: start")
    yield ITEMS[0]
    TRACE.append("generator: end")


def parse_frames(body: str) -> list[dict[str, str]]:
    """Tiny SSE reader: one dict per blank-line separated frame (see ex_22 for a task)."""
    frames = []
    for block in body.strip("\n").split("\n\n"):
        frame: dict[str, str] = {}
        for line in block.split("\n"):
            name, _, value = line.partition(": ")
            frame[name or "comment"] = value
        frames.append(frame)
    return frames


if __name__ == "__main__":
    with TestClient(app) as client:
        r = client.get("/items")
        print("list    :", r.headers["content-type"], "->", r.text)

        with client.stream("GET", "/items/stream") as r:
            print("jsonl   :", r.headers["content-type"])
            for line in r.iter_lines():  # one JSON object per line
                print("   line :", line)

        with client.stream("GET", "/jobs/7/events") as r:
            print("sse     :", r.headers["content-type"], r.headers["cache-control"])
            for frame in parse_frames(r.read().decode()):
                print("   frame:", frame)

        r = client.get("/jobs/7/events", headers={"Last-Event-ID": "2"})
        print("resume  :", [f.get("id") for f in parse_frames(r.text) if "id" in f])

        r = client.post("/chat/stream", json={"text": "hi there"})
        print("chat    :", repr(r.text))
        print("ticks   :", client.get("/ticks").text.count("data: "), "plain-object frames")

        client.get("/scopes")
        print("cleanup order:")
        for entry in TRACE:
            print("   ", entry)
