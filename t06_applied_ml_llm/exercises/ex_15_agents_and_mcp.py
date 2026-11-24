"""Exercise 15: Agent loop and guardrails (scripted fake model, no network).

The model is a function `model_fn(messages) -> dict` returning EITHER
    {"final": "answer text"}                                   (stop)
or  {"tool_calls": [{"name": "add", "args": {"a": 1, "b": 2}}, ...]}   (keep going)

Tasks
1. tool_spec_from_function(fn): build a tool definition from a typed function:
   {"name": fn.__name__, "description": <first line of the docstring or "">,
    "input_schema": {"type": "object", "properties": {param: {"type": T}}, "required": [...]}}
   with T = "integer"/"number"/"string"/"boolean" for int/float/str/bool annotations;
   `required` lists parameters WITHOUT defaults (in signature order).
2. is_looping(calls, limit=3): `calls` is a list of (name, args) tuples. True when the last
   `limit` calls are identical (same name AND args) and there are at least `limit` of them.
3. check_tool_call(name, args, *, allowed=None, dangerous=frozenset(), approve=None):
   return None when the call may run, otherwise a reason string:
   - `allowed` is not None and name not in it  -> f"tool '{name}' is not allowed"
   - name in `dangerous` and (approve is None or not approve(name, args))
                                               -> f"tool '{name}' requires approval"
4. run_agent(task, model_fn, tools, *, max_steps=5, allowed=None, dangerous=frozenset(),
   approve=None) -> AgentResult. `tools` maps name -> callable(**args).
   messages starts as [{"role": "user", "content": task}]. For step 1..max_steps:
   - turn = model_fn(messages). If it has "final": return AgentResult(final, "final", step, trace).
   - append {"role": "assistant", "tool_calls": calls} to messages; then for each call:
       * record (name, args) and if is_looping(all recorded calls) return
         AgentResult(None, "loop", step, trace)
       * observation: the check_tool_call reason as f"blocked: {reason}"; or
         f"error: unknown tool '{name}'"; or f"error: {exc}" if the tool raises; otherwise
         str(result)
       * trace.append((name, args, observation)); append
         {"role": "tool", "name": name, "content": observation} to messages
   After max_steps without a final answer: AgentResult(None, "max_steps", max_steps, trace).

Run: uv run pytest t06_applied_ml_llm -k ex_15
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class AgentResult:
    answer: str | None
    stop_reason: str  # "final" | "max_steps" | "loop"
    steps: int
    trace: list[tuple[str, dict, str]]


def tool_spec_from_function(fn: Callable) -> dict:
    raise NotImplementedError


def is_looping(calls: list[tuple[str, dict]], limit: int = 3) -> bool:
    raise NotImplementedError


def check_tool_call(
    name: str,
    args: dict,
    *,
    allowed: set[str] | None = None,
    dangerous: frozenset[str] = frozenset(),
    approve: Callable[[str, dict], bool] | None = None,
) -> str | None:
    raise NotImplementedError


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
    raise NotImplementedError
