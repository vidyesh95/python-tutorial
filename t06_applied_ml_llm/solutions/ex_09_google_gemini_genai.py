"""Reference solution for Exercise 09: Gemini helpers."""

from collections.abc import Callable
from typing import Any

from google.genai import types


def build_contents(history: list[tuple[str, str]], user_text: str) -> list[types.Content]:
    contents: list[types.Content] = []
    for role, text in [*history, ("user", user_text)]:
        if role == "assistant":
            role = "model"
        if role not in ("user", "model"):
            raise ValueError(f"unknown role: {role!r}")
        contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
    return contents


def _parts(response: types.GenerateContentResponse) -> list[types.Part]:
    if not response.candidates or not response.candidates[0].content:
        return []
    return response.candidates[0].content.parts or []


def extract_text(response: types.GenerateContentResponse) -> str:
    return "".join(p.text for p in _parts(response) if p.text and not p.thought)


def get_function_calls(response: types.GenerateContentResponse) -> list[tuple[str, dict[str, Any]]]:
    return [
        (p.function_call.name or "", dict(p.function_call.args or {}))
        for p in _parts(response)
        if p.function_call
    ]


def function_response_content(results: list[tuple[str, Any]]) -> types.Content:
    parts = [
        types.Part.from_function_response(name=name, response={"result": value})
        for name, value in results
    ]
    return types.Content(role="user", parts=parts)


def run_function_loop(
    generate: Callable[[list[types.Content]], types.GenerateContentResponse],
    user_text: str,
    registry: dict[str, Callable[..., Any]],
    *,
    max_turns: int = 5,
) -> str:
    contents = build_contents([], user_text)
    for _ in range(max_turns):
        response = generate(contents)
        calls = get_function_calls(response)
        if not calls:
            return extract_text(response)
        assert response.candidates and response.candidates[0].content
        contents.append(response.candidates[0].content)
        results: list[tuple[str, Any]] = []
        for name, args in calls:
            try:
                results.append((name, registry[name](**args)))
            except Exception as exc:
                results.append((name, {"error": str(exc) or type(exc).__name__}))
        contents.append(function_response_content(results))
    raise RuntimeError(f"model still requesting functions after {max_turns} turns")
