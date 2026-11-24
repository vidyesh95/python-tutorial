# Claude Messages API
"""
The Messages API is one HTTP endpoint (`POST /v1/messages`); the `anthropic` SDK wraps it.
You send a list of role-tagged messages and get back a `Message` made of CONTENT BLOCKS.

Core ideas:
- CLIENT: `anthropic.Anthropic()` reads ANTHROPIC_API_KEY from the environment. Never hardcode
  or print a key.
- REQUEST: `model`, `max_tokens` (a hard cap you must always set), `messages`, optional
  `system` (instructions live here, not in a user message).
- STATELESS: the API remembers nothing. For a multi-turn chat you resend the whole history
  (alternating `user` / `assistant`; the first message must be `user`).
- RESPONSE: `message.content` is a LIST of blocks (`text`, `thinking`, `tool_use`, ...). Check
  `block.type` before reading `.text`. `stop_reason` says why generation ended: `end_turn`,
  `max_tokens` (truncated!), `tool_use`, `refusal`, ...
- USAGE: `message.usage.input_tokens` / `output_tokens` is what you are billed for.
- MODEL: this track uses `claude-opus-5-5` (the current Opus, from Anthropic's model list).
  Opus 5.5 always thinks; depth is controlled with `output_config={"effort": ...}` (default
  `medium`), so we set `low` for cheap demos. Pick cheaper tiers (`claude-sonnet-5-5`,
  `claude-haiku-5-5`) when quality allows.
- ERRORS: typed exceptions (`RateLimitError`, `APIConnectionError`, `APIStatusError`, ...).

Offline by default: without ANTHROPIC_API_KEY the lesson runs the SAME code against an
in-process fake server (`httpx.MockTransport`) so you can see real request/response shapes.
With a key set, it makes real (small, low-effort) calls.

Run: uv run python -m t06_applied_ml_llm.m_06_anthropic_claude_messages
"""

import json
import os

import anthropic

try:  # anthropic 1.x+ uses httpx2; older releases used httpx
    import httpx2 as httpx
except ImportError:  # pragma: no cover
    import httpx

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")


# --- fake server: returns canned but correctly-shaped responses -------------------------------
def _fake_handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    last = body["messages"][-1]["content"]
    last_text = last if isinstance(last, str) else str(last)
    if "RATE_LIMIT" in last_text:  # lets the error-handling demo trigger a 429
        error = {"type": "error", "error": {"type": "rate_limit_error", "message": "slow down"}}
        return httpx.Response(429, json=error, headers={"retry-after": "2"})
    turns = len(body["messages"])
    message = {
        "id": "msg_fake_001",
        "type": "message",
        "role": "assistant",
        "model": body["model"],
        "content": [
            {"type": "text", "text": f"(fake reply to turn {turns}) You said: {last_text[:40]}"}
        ],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 12 * turns, "output_tokens": 18},
    }
    return httpx.Response(200, json=message, headers={"request-id": "req_fake_001"})


def fake_client(**options: object) -> anthropic.Anthropic:
    transport = httpx.MockTransport(_fake_handler)
    return anthropic.Anthropic(
        api_key="offline-demo-key",  # not a real key; the fake server ignores it
        http_client=anthropic.DefaultHttpxClient(transport=transport),
        **options,
    )


def make_client() -> anthropic.Anthropic:
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("[live] ANTHROPIC_API_KEY found: making real API calls.")
        return anthropic.Anthropic(timeout=60.0, max_retries=2)
    print("[offline] ANTHROPIC_API_KEY not set: using a fake in-process server (no network).")
    return fake_client()


def text_of(message: anthropic.types.Message) -> str:
    return "".join(b.text for b in message.content if b.type == "text")  # skip thinking/tool_use


# Example: the smallest request
def minimal(client: anthropic.Anthropic) -> None:
    message = client.messages.create(
        model=MODEL,
        max_tokens=300,
        output_config={"effort": "low"},  # Opus 5.5: less thinking = cheaper, faster
        messages=[
            {"role": "user", "content": "Explain what a vector embedding is in one sentence."}
        ],
    )
    print(text_of(message))
    print(
        "stop_reason:",
        message.stop_reason,
        "| usage:",
        message.usage.input_tokens,
        "in /",
        message.usage.output_tokens,
        "out",
    )


# Example: system prompt + multi-turn history (YOU keep the history)
def conversation(client: anthropic.Anthropic) -> None:
    system = "You are a terse Python tutor. Answer in at most two sentences."
    history: list[anthropic.types.MessageParam] = []
    for question in ["What is a list comprehension?", "Show me one for squares."]:
        history.append({"role": "user", "content": question})
        reply = client.messages.create(
            model=MODEL,
            max_tokens=300,
            system=system,
            messages=history,
            output_config={"effort": "low"},
        )
        history.append({"role": "assistant", "content": text_of(reply)})  # store text, not blocks
        print(f"Q: {question}\nA: {text_of(reply)}")
    print("history roles:", [m["role"] for m in history])


# Example: reading blocks and stop_reason defensively
def read_response(message: anthropic.types.Message) -> str:
    if message.stop_reason == "refusal":
        raise RuntimeError("model declined the request")
    if message.stop_reason == "max_tokens":
        raise RuntimeError("output truncated: raise max_tokens or ask for less")
    return text_of(message)


# Example: typed error handling (always against the fake server: it forces a 429)
def error_handling() -> None:
    client = fake_client(max_retries=0)  # max_retries=0 so we see the raw error immediately
    try:
        client.messages.create(
            model=MODEL, max_tokens=50, messages=[{"role": "user", "content": "RATE_LIMIT please"}]
        )
    except anthropic.RateLimitError as exc:  # most specific first
        print("429 caught; retry-after:", exc.response.headers.get("retry-after"), "s")
    except anthropic.APIStatusError as exc:  # any other non-2xx
        print("API error", exc.status_code)
    except anthropic.APIConnectionError:  # network down / DNS / timeout
        print("network problem")


"""
Common mistakes:
- Reading `message.content[0].text` blindly: the first block may be `thinking` or `tool_use`.
- Not checking `stop_reason == "max_tokens"` and shipping a truncated answer.
- Putting instructions in a user message instead of `system`; or putting untrusted user text
  in `system` (that is how prompt injection gets operator authority).
- Forgetting the API is stateless: the model "forgets" unless you resend the history.
- Prefilling the assistant turn: removed on current Claude models (400); use a system
  instruction or structured output (lesson 08) instead.
- Sending `temperature`/`top_p` to Opus 5.5: sampling parameters are rejected (400).
- Hardcoding the key, logging request headers, or committing `.env` files.

Production notes:
- COST: you pay per token in and out; Opus 5.5 is $4 / $20 per million tokens in/out. Use
  `client.messages.count_tokens(...)` before big prompts and route easy work to Sonnet/Haiku.
- LATENCY: output tokens dominate; lower `effort`, shorter `max_tokens`, and streaming
  (lesson 07) make apps feel faster. Large `max_tokens` without streaming can time out.
- RETRIES/RATE LIMITS: the SDK retries 408/409/429/5xx and connection errors (default 2) with
  backoff and honors `retry-after`; tune with `max_retries`; add your own backoff only beyond that.
- TIMEOUTS: default is 10 minutes. Set `timeout=` (seconds) per client or `with_options(timeout=...)`.
- OBSERVABILITY: log `message._request_id`, model, token usage and latency; never log keys.
- REFUSALS: Opus 5.5 can return `stop_reason == "refusal"`; production code should handle it
  (Anthropic also offers a server-side `fallbacks` beta to retry on another model).
"""

if __name__ == "__main__":
    api = make_client()
    minimal(api)
    conversation(api)
    print(
        read_response(
            api.messages.create(
                model=MODEL, max_tokens=100, messages=[{"role": "user", "content": "hi"}]
            )
        )
    )
    error_handling()
