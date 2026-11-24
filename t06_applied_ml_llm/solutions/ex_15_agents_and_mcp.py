"""Reference solution for Exercise 15: Agent loop and guardrails."""

import inspect
from collections.abc import Callable
from dataclasses import dataclass

PY_TO_JSON = {int: "integer", float: "number", str: "string", bool: "boolean"}


@dataclass
class AgentResult:
    answer: str | None
    stop_reason: str
    steps: int
    trace: list[tuple[str, dict, str]]


def tool_spec_from_function(fn: Callable) -> dict:
    params = inspect.signature(fn).parameters
    return {
        "name": fn.__name__,
        "description": (inspect.getdoc(fn) or "").split("\n")[0],
        "input_schema": {
            "type": "object",
            "properties": {n: {"type": PY_TO_JSON[p.annotation]} for n, p in params.items()},
            "required": [n for n, p in params.items() if p.default is inspect.Parameter.empty],
        },
    }


def is_looping(calls: list[tuple[str, dict]], limit: int = 3) -> bool:
    if len(calls) < limit:
        return False
    tail = calls[-limit:]
    return all(c == tail[0] for c in tail)


def check_tool_call(
    name: str,
    args: dict,
    *,
    allowed: set[str] | None = None,
    dangerous: frozenset[str] = frozenset(),
    approve: Callable[[str, dict], bool] | None = None,
) -> str | None:
    if allowed is not None and name not in allowed:
        return f"tool '{name}' is not allowed"
    if name in dangerous and (approve is None or not approve(name, args)):
        return f"tool '{name}' requires approval"
    return None


def run_agent(
    task: str,
    model_fn: Callable[[list[dict]], dict],
    tools: dict[str, Callable],
    *,
    max_steps: int = 5,
    allowed: set[str] | None = None,
    dangerous: frozenset[str] = frozenset(),
    approve: Callable[[str, dict], bool] | None = None,
) -> AgentResult:
    messages: list[dict] = [{"role": "user", "content": task}]
    trace: list[tuple[str, dict, str]] = []
    calls_seen: list[tuple[str, dict]] = []
    for step in range(1, max_steps + 1):
        turn = model_fn(messages)
        if "final" in turn:
            return AgentResult(turn["final"], "final", step, trace)
        calls = turn.get("tool_calls", [])
        messages.append({"role": "assistant", "tool_calls": calls})
        for call in calls:
            name, args = call["name"], call.get("args", {})
            calls_seen.append((name, args))
            if is_looping(calls_seen):
                return AgentResult(None, "loop", step, trace)
            reason = check_tool_call(
                name, args, allowed=allowed, dangerous=dangerous, approve=approve
            )
            if reason is not None:
                observation = f"blocked: {reason}"
            elif name not in tools:
                observation = f"error: unknown tool '{name}'"
            else:
                try:
                    observation = str(tools[name](**args))
                except Exception as exc:
                    observation = f"error: {exc}"
            trace.append((name, args, observation))
            messages.append({"role": "tool", "name": name, "content": observation})
    return AgentResult(None, "max_steps", max_steps, trace)
