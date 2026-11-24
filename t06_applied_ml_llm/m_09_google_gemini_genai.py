# Google Gemini with the google-genai SDK
"""
`google-genai` is Google's unified SDK for the Gemini API. The shape differs from Anthropic's:
one `Client` exposes `client.models.generate_content(model=, contents=, config=)`; settings
(system prompt, temperature, tools, JSON schema) go in a `types.GenerateContentConfig`.

Core ideas:
- CLIENT: `genai.Client(api_key=os.environ["GEMINI_API_KEY"])`. `HttpOptions` sets timeouts
  (milliseconds!), retries, or a custom httpx client.
- CONTENTS: a string, or a list of `types.Content(role="user"|"model", parts=[Part(text=...)])`.
  Gemini calls the assistant role "model" (not "assistant").
- RESPONSE: `response.text` (text parts joined), `response.candidates[0].content.parts`,
  `response.usage_metadata` (prompt/candidates/total token counts).
- CHAT: `client.chats.create(...)` keeps the history for you (`chat.send_message`); under the
  hood it resends the history like any stateless API.
- STREAMING: `generate_content_stream(...)` yields partial responses; join their `.text`.
- FUNCTION CALLING: pass Python functions as `tools=[fn]` and the SDK builds the schema from
  type hints + docstring, calls your function when the model asks, and sends the result back
  (automatic function calling). Disable that to run the loop manually.
- STRUCTURED OUTPUT: `response_mime_type="application/json"` + `response_schema=PydanticModel`
  gives JSON constrained to the schema, and `response.parsed` is a model instance.
- MODEL NAME: kept in the `GEMINI_MODEL` constant; override with the env var of the same name.
  The default is the model id used in the installed SDK's own docs (`gemini-3.8-flash`).

Offline by default (fake in-process server) unless GEMINI_API_KEY is set.
Run: uv run python -m t06_applied_ml_llm.m_09_google_gemini_genai
"""

import json
import os
from typing import Any

import httpx
from google import genai
from google.genai import types
from pydantic import BaseModel

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")


class Recipe(BaseModel):
    name: str
    minutes: int
    ingredients: list[str]


def get_weather(city: str) -> dict[str, Any]:
    """Get the current weather for a city.

    Args:
        city: City name, e.g. "Paris".
    """
    return {"city": city, "temp_c": 18, "sky": "cloudy"}


# --- fake server: scripted Gemini-shaped JSON -------------------------------------------------
def _candidate(parts: list[dict[str, Any]]) -> dict[str, Any]:
    return {"content": {"role": "model", "parts": parts}, "finishReason": "STOP"}


def _fake_handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    usage = {"promptTokenCount": 20, "candidatesTokenCount": 12, "totalTokenCount": 32}
    contents = body.get("contents", [])
    if "alt=sse" in str(request.url):  # streaming: one JSON chunk per event
        chunks = ["Gemini ", "streams ", "chunks."]
        data = "".join(
            "data: " + json.dumps({"candidates": [_candidate([{"text": c}])]}) + "\r\n\r\n"
            for c in chunks
        )
        return httpx.Response(
            200, headers={"content-type": "text/event-stream"}, content=data.encode()
        )
    answered = any("functionResponse" in p for c in contents for p in c.get("parts", []))
    if body.get("tools") and not answered:  # model asks us to run get_weather
        call = {"functionCall": {"name": "get_weather", "args": {"city": "Paris"}}}
        parts = [call]
    elif body.get("generationConfig", {}).get("responseSchema") or body.get(
        "generationConfig", {}
    ).get("responseJsonSchema"):
        recipe = {"name": "Omelette", "minutes": 10, "ingredients": ["eggs", "butter", "salt"]}
        parts = [{"text": json.dumps(recipe)}]
    elif answered:
        parts = [{"text": "It is 18 C and cloudy in Paris."}]
    else:
        parts = [{"text": f"(fake) turn {len(contents)} reply"}]
    return httpx.Response(200, json={"candidates": [_candidate(parts)], "usageMetadata": usage})


def make_client() -> genai.Client:
    if os.environ.get("GEMINI_API_KEY"):
        print("[live] GEMINI_API_KEY found: making real API calls.")
        options = types.HttpOptions(timeout=60_000, retryOptions=types.HttpRetryOptions(attempts=3))
        return genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=options)
    print("[offline] GEMINI_API_KEY not set: using a fake in-process server (no network).")
    http = httpx.Client(transport=httpx.MockTransport(_fake_handler))
    return genai.Client(
        api_key="offline-demo-key", http_options=types.HttpOptions(httpxClient=http)
    )


# Example: generate_content with a config
def generate_demo(client: genai.Client) -> None:
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents="Explain embeddings in one sentence.",
        config=types.GenerateContentConfig(
            system_instruction="You are a terse tutor.", max_output_tokens=200, temperature=0.2
        ),
    )
    print(response.text)
    usage = response.usage_metadata
    assert usage is not None
    print(
        "tokens in/out/total:",
        usage.prompt_token_count,
        usage.candidates_token_count,
        usage.total_token_count,
    )


# Example: chat (history managed by the SDK) and streaming
def chat_and_stream_demo(client: genai.Client) -> None:
    chat = client.chats.create(model=GEMINI_MODEL)
    chat.send_message("My name is Ada.")
    print(chat.send_message("What is my name?").text)
    print("history roles:", [c.role for c in chat.get_history()])  # user, model, user, model
    pieces = [
        chunk.text or ""
        for chunk in client.models.generate_content_stream(
            model=GEMINI_MODEL, contents="Stream please"
        )
    ]
    print("streamed:", "".join(pieces))


# Example: automatic function calling (AFC) via a chat: the SDK runs get_weather for us
def function_calling_demo(client: genai.Client) -> None:
    config = types.GenerateContentConfig(tools=[get_weather])  # schema built from hints+docstring
    chat = client.chats.create(model=GEMINI_MODEL, config=config)
    print(chat.send_message("What's the weather in Paris?").text)


# Example: the manual loop (disable AFC, inspect function_call parts, send function_response)
def manual_function_calling(client: genai.Client) -> str:
    config = types.GenerateContentConfig(
        tools=[get_weather],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text="Weather in Paris?")])
    ]
    for _ in range(5):  # cap the loop
        response = client.models.generate_content(
            model=GEMINI_MODEL, contents=contents, config=config
        )
        assert response.candidates and response.candidates[0].content
        model_content = response.candidates[0].content
        contents.append(model_content)
        calls = [p.function_call for p in model_content.parts or [] if p.function_call]
        if not calls:
            return response.text or ""
        results = [
            types.Part.from_function_response(
                name=c.name or "", response={"result": get_weather(**(c.args or {}))}
            )
            for c in calls
        ]
        contents.append(types.Content(role="user", parts=results))
    raise RuntimeError("too many tool turns")


# Example: structured output with a pydantic schema
def structured_demo(client: genai.Client) -> Recipe:
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents="Give me a quick omelette recipe.",
        config=types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=Recipe
        ),
    )
    recipe = response.parsed
    assert isinstance(recipe, Recipe)  # parsed is already a validated pydantic instance
    print(recipe)
    return recipe


"""
Common mistakes:
- Using role "assistant" in `contents`; Gemini wants "model".
- `HttpOptions(timeout=60)` meaning seconds: it is MILLISECONDS (60 -> 60 ms, instant failure).
- Reading `response.text` when the reply has only function-call parts: it is None/empty.
- Trusting `response.parsed` without checking it is not None (blocked or truncated replies).
- Hardcoding the model id in many places; keep it in one constant (here: GEMINI_MODEL).
- Expecting a function-calling loop to stop by itself: cap the turns.

Production notes:
- COST: billed per input/output token (thinking tokens count as output on thinking models);
  `usage_metadata` gives counts. Use a smaller "flash" tier for high-volume work.
- LATENCY: stream user-facing text; keep `max_output_tokens` tight.
- RETRIES/RATE LIMITS: `HttpRetryOptions(attempts=...)` retries transient errors; 429s mean you
  hit per-minute quotas, so add jittered backoff and a client-side concurrency limit.
- Safety filters can block a response (`finish_reason`, `prompt_feedback`): handle empty text.
- Keys come from env vars or a secret manager; for Vertex AI use `genai.Client(vertexai=True, ...)`
  with Google Cloud credentials instead of an API key.
"""

if __name__ == "__main__":
    api = make_client()
    generate_demo(api)
    chat_and_stream_demo(api)
    function_calling_demo(api)
    print("manual:", manual_function_calling(api))
    structured_demo(api)
