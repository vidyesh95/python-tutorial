"""Reference solution for Exercise 07: Claude streaming and tool use."""

import json
from collections.abc import Callable, Iterable
from typing import Any

MODEL = "claude-opus-5-5"


def collect_text(events: Iterable[Any]) -> str:
    return "".join(
        event.delta.text
        for event in events
        if event.type == "content_block_delta" and event.delta.type == "text_delta"
    )


def collect_tool_calls(events: Iterable[Any]) -> list[dict[str, Any]]:
    blocks: dict[int, dict[str, Any]] = {}
    fragments: dict[int, list[str]] = {}
    for event in events:
        if event.type == "content_block_start" and event.content_block.type == "tool_use":
            blocks[event.index] = {"id": event.content_block.id, "name": event.content_block.name}
            fragments[event.index] = []
        elif event.type == "content_block_delta" and event.delta.type == "input_json_delta":
            fragments[event.index].append(event.delta.partial_json)
    calls = []
    for index in sorted(blocks):
        raw = "".join(fragments[index])
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid tool input JSON for {blocks[index]['name']}: {exc}") from exc
        calls.append({**blocks[index], "input": parsed})
    return calls


def execute_tool_use(block: Any, registry: dict[str, Callable[..., Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "tool_result", "tool_use_id": block.id}
    tool = registry.get(block.name)
    if tool is None:
        return {**result, "content": f"unknown tool: {block.name}", "is_error": True}
    try:
        return {**result, "content": str(tool(**block.input)), "is_error": False}
    except Exception as exc:
        return {**result, "content": f"{type(exc).__name__}: {exc}", "is_error": True}


def run_tool_loop(
    client: Any,
    question: str,
    tools: list[dict[str, Any]],
    registry: dict[str, Callable[..., Any]],
    *,
    model: str = MODEL,
    max_turns: int = 5,
) -> str:
    messages: list[dict[str, Any]] = [{"role": "user", "content": question}]
    for _ in range(max_turns):
        response = client.messages.create(
            model=model, max_tokens=1024, tools=tools, messages=messages
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")
        results = [execute_tool_use(b, registry) for b in response.content if b.type == "tool_use"]
        messages.append({"role": "user", "content": results})
    raise RuntimeError(f"model still requesting tools after {max_turns} turns")


_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
}


def validate_tool_input(schema: dict[str, Any], data: dict[str, Any]) -> list[str]:
    properties = schema.get("properties", {})
    problems: list[str] = []
    for key in schema.get("required", []):
        if key not in data:
            problems.append(f"missing: {key}")
    for key, value in data.items():
        if key not in properties:
            if schema.get("additionalProperties") is False:
                problems.append(f"unexpected: {key}")
            continue
        expected = _TYPES.get(properties[key].get("type", ""), ())
        is_bool_pretending = isinstance(value, bool) and bool not in expected
        if expected and (is_bool_pretending or not isinstance(value, expected)):
            problems.append(f"wrong type: {key}")
    return sorted(problems)
