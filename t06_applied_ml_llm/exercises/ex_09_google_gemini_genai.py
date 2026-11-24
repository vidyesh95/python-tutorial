"""Exercise 09: Gemini helpers (logic only, no network).

Tested with real `google.genai.types` objects and a scripted fake `generate` function.

Tasks
1. build_contents(history, user_text): history is a list of (role, text) tuples where role is
   "user", "assistant" or "model". Return a list[types.Content] ending with the new user
   message. Gemini calls the assistant role "model", so map "assistant" -> "model". Raise
   ValueError for any other role.
2. extract_text(response): join the text of the first candidate's parts, skipping parts
   without text (e.g. function calls) and "thought" parts (part.thought is True). Return ""
   if there are no candidates or no text.
3. get_function_calls(response): list of (name, args_dict) for every function_call part of
   the first candidate, in order ([] if none). `args` may be None -> {}.
4. function_response_content(results): given [(name, value), ...] build ONE
   types.Content(role="user") whose parts are
   `types.Part.from_function_response(name=name, response={"result": value})`.
5. run_function_loop(generate, user_text, registry, *, max_turns=5): the manual loop.
   `generate(contents)` returns a GenerateContentResponse. Start with the user content, then
   repeat: call generate; if the reply has no function calls return extract_text(reply);
   otherwise append the model's content (candidates[0].content), run each call with
   `registry[name](**args)` (if a tool raises or is unknown use the value
   {"error": "<message>"}), and append function_response_content(results). Raise RuntimeError
   if the model still wants functions after max_turns calls to generate.

Run: uv run pytest t06_applied_ml_llm -k ex_09
"""

from collections.abc import Callable
from typing import Any

from google.genai import types


def build_contents(history: list[tuple[str, str]], user_text: str) -> list[types.Content]:
    raise NotImplementedError


def extract_text(response: types.GenerateContentResponse) -> str:
    raise NotImplementedError


def get_function_calls(response: types.GenerateContentResponse) -> list[tuple[str, dict[str, Any]]]:
    raise NotImplementedError


def function_response_content(results: list[tuple[str, Any]]) -> types.Content:
    raise NotImplementedError


def run_function_loop(
    generate: Callable[[list[types.Content]], types.GenerateContentResponse],
    user_text: str,
    registry: dict[str, Callable[..., Any]],
    *,
    max_turns: int = 5,
) -> str:
    raise NotImplementedError
