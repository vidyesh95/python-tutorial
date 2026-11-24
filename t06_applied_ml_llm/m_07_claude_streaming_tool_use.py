# Claude Streaming and Tool Use
"""
STREAMING sends the answer as server-sent events while it is generated, so users see the first
words in ~1 second instead of waiting for the whole reply. TOOL USE lets Claude ask YOUR code
to do things (math, database lookups, API calls); Claude never runs code itself, it only
returns a structured request.

Streaming events, in order: `message_start`, then per content block `content_block_start` ->
`content_block_delta`* -> `content_block_stop`, then `message_delta` (stop_reason, usage) and
`message_stop`. `client.messages.stream(...)` is the helper: iterate `stream.text_stream` for
plain text, iterate `stream` for events, and call `stream.get_final_message()` for the
accumulated `Message`.

The manual tool-use loop (you own it):
1. Send `tools=[{name, description, input_schema}]` plus the user message.
2. If `stop_reason == "tool_use"`, the reply contains one or more `tool_use` blocks
   (`id`, `name`, `input`). Run each tool yourself.
3. Append the assistant message EXACTLY as received, then ONE user message holding ALL
   `tool_result` blocks (matching `tool_use_id`; `is_error: True` on failure).
4. Call the API again. Repeat until `stop_reason` is not `tool_use`. Cap the turns.

The SDK also ships a beta TOOL RUNNER (`@anthropic.beta_tool` + `client.beta.messages.tool_runner`)
that runs this loop for you; write the manual loop once so you understand what it automates.
On Opus 5.5 you cannot force a tool (`tool_choice` any/tool returns 400): keep `auto`, set
`strict: True` on tools for schema-valid arguments, and say in the prompt when a tool is needed.

Offline by default (fake in-process server) unless ANTHROPIC_API_KEY is set.
Run: uv run python -m t06_applied_ml_llm.m_07_claude_streaming_tool_use
"""

import ast
import json
import operator
import os
from collections.abc import Callable
from typing import Any

import anthropic

try:  # anthropic 1.x+ uses httpx2; older releases used httpx
    import httpx2 as httpx
except ImportError:  # pragma: no cover
    import httpx

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
QUESTION = "What is 17 * 23, and what is the capital of France? Use the tools."


# --- two local tools -------------------------------------------------------------------------
_OPS: dict[type, Callable[..., float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def calculator(expression: str) -> str:
    """Safely evaluate arithmetic. Never `eval()` model-provided text."""

    def walk(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](walk(node.operand))
        raise ValueError("unsupported expression")

    return str(walk(ast.parse(expression, mode="eval").body))


def capital_of(country: str) -> str:
    capitals = {"france": "Paris", "japan": "Tokyo", "kenya": "Nairobi"}
    return capitals.get(country.strip().lower()) or f"unknown country: {country}"


REGISTRY: dict[str, Callable[..., str]] = {"calculator": calculator, "capital_of": capital_of}
TOOLS: list[dict[str, Any]] = [
    {
        "name": "calculator",
        "description": "Evaluate an arithmetic expression such as '17 * 23'.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
            "additionalProperties": False,
        },
    },
    {
        "name": "capital_of",
        "description": "Look up the capital city of a country.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"country": {"type": "string"}},
            "required": ["country"],
            "additionalProperties": False,
        },
    },
]


# --- fake server: scripted streaming + tool-use responses -------------------------------------
def _message(content: list[dict[str, Any]], stop_reason: str | None) -> dict[str, Any]:
    return {
        "id": "msg_fake",
        "type": "message",
        "role": "assistant",
        "model": MODEL,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 50, "output_tokens": 20},
    }


def _stream(
    start: dict[str, Any], deltas: list[dict[str, Any]], stop_reason: str
) -> httpx.Response:
    """Build the exact server-sent-event sequence the real API emits for one content block."""
    events: list[tuple[str, dict[str, Any]]] = [
        ("message_start", {"type": "message_start", "message": _message([], None)}),
        (
            "content_block_start",
            {"type": "content_block_start", "index": 0, "content_block": start},
        ),
    ]
    for delta in deltas:
        events.append(
            ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": delta})
        )
    final = {"stop_reason": stop_reason, "stop_sequence": None}
    events += [
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        ("message_delta", {"type": "message_delta", "delta": final, "usage": {"output_tokens": 8}}),
        ("message_stop", {"type": "message_stop"}),
    ]
    data = "".join(f"event: {name}\ndata: {json.dumps(payload)}\n\n" for name, payload in events)
    return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=data.encode())


def _fake_handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    last = body["messages"][-1]["content"]
    has_result = isinstance(last, list) and any(b.get("type") == "tool_result" for b in last)
    if body.get("stream") and body.get("tools"):  # streamed tool call: JSON arrives in fragments
        start = {"type": "tool_use", "id": "toolu_1", "name": "calculator", "input": {}}
        pieces = ['{"expres', 'sion": "17', ' * 23"}']
        return _stream(
            start, [{"type": "input_json_delta", "partial_json": p} for p in pieces], "tool_use"
        )
    if body.get("stream"):  # plain streamed text
        words = ["Streaming ", "shows ", "tokens ", "as ", "they ", "arrive."]
        start = {"type": "text", "text": ""}
        return _stream(start, [{"type": "text_delta", "text": w} for w in words], "end_turn")
    if not has_result:  # first turn: ask for BOTH tools in one message (parallel tool use)
        blocks = [
            {
                "type": "tool_use",
                "id": "toolu_a",
                "name": "calculator",
                "input": {"expression": "17 * 23"},
            },
            {
                "type": "tool_use",
                "id": "toolu_b",
                "name": "capital_of",
                "input": {"country": "France"},
            },
        ]
        return httpx.Response(200, json=_message(blocks, "tool_use"))
    results = [b["content"] for b in last]  # second turn: summarize the tool results
    return httpx.Response(
        200, json=_message([{"type": "text", "text": f"Results: {results}"}], "end_turn")
    )


def make_client() -> anthropic.Anthropic:
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("[live] ANTHROPIC_API_KEY found: making real API calls.")
        return anthropic.Anthropic(timeout=60.0)
    print("[offline] ANTHROPIC_API_KEY not set: using a fake in-process server (no network).")
    transport = httpx.MockTransport(_fake_handler)
    return anthropic.Anthropic(
        api_key="offline-demo-key", http_client=anthropic.DefaultHttpxClient(transport=transport)
    )


# Example: streaming text, then inspecting raw events
def streaming_demo(client: anthropic.Anthropic) -> None:
    request: dict[str, Any] = {
        "model": MODEL,
        "max_tokens": 300,
        "output_config": {"effort": "low"},
        "messages": [{"role": "user", "content": "Say one sentence about streaming."}],
    }
    with client.messages.stream(**request) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        final = stream.get_final_message()  # full Message, assembled by the SDK
    print(f"\n[stop_reason={final.stop_reason}, output_tokens={final.usage.output_tokens}]")
    with client.messages.stream(**request) as stream:
        print("event types:", sorted({event.type for event in stream}))


# Example: a streamed tool call arrives as JSON fragments (eager_input_streaming)
def streaming_tool_demo(client: anthropic.Anthropic) -> None:
    tool = {k: v for k, v in TOOLS[0].items() if k != "strict"} | {"eager_input_streaming": True}
    with client.messages.stream(
        model=MODEL,
        max_tokens=300,
        tools=[tool],
        messages=[{"role": "user", "content": "What is 17 * 23? Use the calculator tool."}],
    ) as stream:
        fragments = [e.partial_json for e in stream if e.type == "input_json"]
        final = stream.get_final_message()
    print("json fragments:", fragments)
    # With eager streaming the server does NOT validate the JSON: validate before running tools.
    print("final tool input:", [b.input for b in final.content if b.type == "tool_use"])


# Example: the full manual tool-use loop
def run_tool_loop(client: anthropic.Anthropic, question: str, max_turns: int = 6) -> str:
    messages: list[anthropic.types.MessageParam] = [{"role": "user", "content": question}]
    for turn in range(1, max_turns + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
            output_config={"effort": "low"},
        )
        messages.append({"role": "assistant", "content": response.content})  # unchanged
        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")
        results: list[anthropic.types.ToolResultBlockParam] = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                output, is_error = REGISTRY[block.name](**block.input), False
            except Exception as exc:  # report tool failures TO the model; don't crash the loop
                output, is_error = f"{type(exc).__name__}: {exc}", True
            print(f"  turn {turn}: {block.name}({block.input}) -> {output}")
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                    "is_error": is_error,
                }
            )
        messages.append({"role": "user", "content": results})  # ALL results in ONE message
    raise RuntimeError(f"no final answer after {max_turns} turns")


"""
Common mistakes:
- Running tool calls but replying with several separate user messages: send one message with
  every `tool_result` (splitting teaches the model to stop calling tools in parallel).
- Dropping the assistant `tool_use` message from history, or editing it: the API rejects
  results that do not match a preceding `tool_use` id.
- `eval()`/`exec()` or shelling out with model-provided arguments. Validate and sandbox.
- No turn limit: a confused model can loop forever and burn money. Cap iterations.
- Trusting streamed tool JSON before the block finishes (partial_json is incomplete until
  `content_block_stop`); never act on fragments.
- Treating tool results as trusted instructions: web pages or DB rows can contain prompt injection.

Production notes:
- COST/LATENCY: each loop turn re-sends the whole history (cache it, lesson 08) and adds a
  round trip; run independent tool calls concurrently (`asyncio.gather`/threads).
- Stream anything user-facing; non-streaming requests with big `max_tokens` risk timeouts.
- Set per-tool timeouts, return short results (truncate huge outputs), and return errors with
  `is_error: True` plus a helpful message so the model can recover.
- RETRIES: a dropped stream cannot resume; retry the whole request. Keep side-effecting tools
  idempotent (use an idempotency key) because a retry may repeat a call.
- Log tool name, arguments (redacted), duration and result size for every call.
"""

if __name__ == "__main__":
    api = make_client()
    streaming_demo(api)
    streaming_tool_demo(api)
    print("Final answer:", run_tool_loop(api, QUESTION))
