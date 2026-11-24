# Prompt Caching and Structured Output
"""
Two features that make Claude usable inside real software: PROMPT CACHING (pay ~5% to re-read
a big prompt prefix) and STRUCTURED OUTPUT (get JSON you can trust, validated by pydantic).

PROMPT CACHING
- Caching is a PREFIX match. Render order is tools -> system -> messages; a byte change
  anywhere in the prefix invalidates everything after it. Put stable content first (system
  prompt, documents, few-shot examples) and volatile content (the user's question, timestamps)
  after the last breakpoint.
- Mark the end of the stable part with `cache_control={"type": "ephemeral"}` on a content
  block (optionally `"ttl": "1h"`; default 5 minutes). Max 4 breakpoints.
- The prefix must be long enough (512 tokens on Opus 5.5); shorter prefixes silently do
  not cache and there is no error.
- Verify with `usage`: `cache_creation_input_tokens` (written, ~1.25x price), then
  `cache_read_input_tokens` (read, ~0.05x on Opus 5.5) and `input_tokens` (uncached rest).
  Total prompt = the three added together. Reads of zero across repeats = a silent invalidator
  (timestamp or UUID in the system prompt, unsorted JSON, changing tool list).

STRUCTURED OUTPUT
- `client.messages.parse(..., output_format=MyModel)` constrains the reply to your pydantic
  model's JSON schema and returns `response.parsed_output` as a validated instance.
- Or send the schema yourself: `output_config={"format": {"type": "json_schema", "schema": ...}}`
  (`anthropic.transform_schema(Model)` adapts a pydantic schema), then `json.loads` and
  `Model.model_validate`. Always validate: a schema guarantees shape, not truth.

Offline by default (fake in-process server that simulates cache usage) unless ANTHROPIC_API_KEY
is set. Run: uv run python -m t06_applied_ml_llm.m_08_claude_prompt_caching_structured_output
"""

import json
import os
from typing import Literal

import anthropic
from pydantic import BaseModel, ValidationError

try:  # anthropic 1.x+ uses httpx2; older releases used httpx
    import httpx2 as httpx
except ImportError:  # pragma: no cover
    import httpx

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
# $ per million tokens for Opus 5.5 (from the Anthropic models table); cache read is 0.05x.
INPUT_PER_MTOK, OUTPUT_PER_MTOK = 4.00, 20.00
WRITE_MULT, READ_MULT = 1.25, 0.05

# A deliberately long, STABLE system prompt (a real one might be a handbook or codebase digest).
POLICY = (
    "Support policy: refunds within 30 days; escalate security issues to the on-call; be polite. "
)
SYSTEM_TEXT = "You triage customer-support tickets for Acme.\n" + POLICY * 120


class Ticket(BaseModel):
    category: Literal["billing", "bug", "security", "other"]
    urgency: int  # 1 (low) .. 5 (high)
    summary: str


# --- fake server: simulates cache creation/read and JSON replies --------------------------------
_cache_seen: set[str] = set()


def _fake_handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    system = body.get("system") or []
    blocks = [{"text": system}] if isinstance(system, str) else system
    prefix = "".join(b["text"] for b in blocks)
    system_tokens = len(prefix) // 4  # crude estimate: ~4 characters per token
    usage = {"input_tokens": 25, "output_tokens": 40}
    if any("cache_control" in b for b in blocks if isinstance(b, dict)):
        if prefix in _cache_seen:
            usage["cache_read_input_tokens"] = system_tokens
        else:
            _cache_seen.add(prefix)
            usage["cache_creation_input_tokens"] = system_tokens
    else:
        usage["input_tokens"] += system_tokens
    reply = (
        '{"category": "security", "urgency": 5, "summary": "Customer reports a leaked API key."}'
    )
    message = {
        "id": "msg_fake", "type": "message", "role": "assistant", "model": body["model"],
        "content": [{"type": "text", "text": reply}],
        "stop_reason": "end_turn", "stop_sequence": None, "usage": usage,
    }  # fmt: skip
    return httpx.Response(200, json=message)


def make_client() -> anthropic.Anthropic:
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("[live] ANTHROPIC_API_KEY found: making real API calls.")
        return anthropic.Anthropic(timeout=60.0)
    print("[offline] ANTHROPIC_API_KEY not set: using a fake in-process server (no network).")
    transport = httpx.MockTransport(_fake_handler)
    http_client = anthropic.DefaultHttpxClient(transport=transport)
    return anthropic.Anthropic(api_key="offline-demo-key", http_client=http_client)


def request_cost(usage: anthropic.types.Usage) -> float:
    """Dollar cost of one request, honoring cache write/read multipliers."""
    cache_write = usage.cache_creation_input_tokens or 0
    cache_read = usage.cache_read_input_tokens or 0
    input_side = usage.input_tokens + cache_write * WRITE_MULT + cache_read * READ_MULT
    return (input_side * INPUT_PER_MTOK + usage.output_tokens * OUTPUT_PER_MTOK) / 1_000_000


# Example: cache_control on the stable system block; the changing question comes AFTER it
def caching_demo(client: anthropic.Anthropic) -> None:
    system = [{"type": "text", "text": SYSTEM_TEXT, "cache_control": {"type": "ephemeral"}}]
    for ticket in ["I think my API key was leaked on GitHub!", "Where is my invoice?"]:
        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            output_config={"effort": "low"},
            system=system,
            messages=[{"role": "user", "content": ticket}],
        )
        u = response.usage
        print(
            f"write={u.cache_creation_input_tokens} read={u.cache_read_input_tokens} "
            f"uncached={u.input_tokens} -> ${request_cost(u):.5f}"
        )


# Example: structured output with messages.parse + a pydantic model
def parse_demo(client: anthropic.Anthropic) -> Ticket:
    response = client.messages.parse(
        model=MODEL,
        max_tokens=300,
        output_config={"effort": "low"},
        system=SYSTEM_TEXT,
        messages=[{"role": "user", "content": "I think my API key was leaked on GitHub!"}],
        output_format=Ticket,  # schema is sent for you; reply is validated into a Ticket
    )
    ticket = response.parsed_output
    assert ticket is not None
    print(type(ticket).__name__, ticket.model_dump())
    return ticket


# Example: raw schema + manual validation (works everywhere, and shows what parse() does)
def raw_schema_demo(client: anthropic.Anthropic) -> None:
    schema = anthropic.transform_schema(Ticket)  # make a pydantic schema API-compatible
    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
        system=SYSTEM_TEXT,
        messages=[{"role": "user", "content": "Classify: I was double charged."}],
    )
    text = next(b.text for b in response.content if b.type == "text")
    try:
        print("validated:", Ticket.model_validate_json(text))
    except ValidationError as exc:  # e.g. urgency not an int, category not in the Literal
        print("model returned bad data:", exc.error_count(), "errors")


# Example: what a validation failure looks like (no API needed)
def validation_demo() -> None:
    bad = json.loads('{"category": "weather", "urgency": "very", "summary": "x"}')
    try:
        Ticket.model_validate(bad)
    except ValidationError as exc:
        print([f"{e['loc'][0]}: {e['type']}" for e in exc.errors()])


"""
Common mistakes:
- A timestamp, request ID or user name in the cached prefix: it changes every call, so the
  cache never hits. Keep volatile data after the breakpoint.
- Prefix below the minimum size (512 tokens on Opus 5.5): no error, just no caching.
- Putting `cache_control` on the user's changing question (a pure write surcharge).
- Assuming schema-valid JSON is correct JSON: still validate ranges, enums, business rules.
- Asking for JSON in the prompt only ("respond in JSON") and calling `json.loads` blindly.
- Prefilling `{` to force JSON: prefill is removed on current models; use structured outputs.

Production notes:
- COST: a 5-minute cache write costs 1.25x, a read ~0.05x on Opus 5.5, so two requests inside
  the TTL already win. Use `ttl: "1h"` (write 2x) only for bursty traffic with gaps >5 min.
- LATENCY: cache hits also cut time-to-first-token on long prompts.
- Re-check `usage.cache_read_input_tokens` after any prompt-assembly change; the failure mode
  is a silently higher bill. Add a test asserting the second identical call reads from cache.
- Cache entries are per workspace and per model; switching model or tools resets them.
- Structured outputs: on a `ValidationError` retry once with the error message fed back, then
  fail loudly or fall back. Cap retries; every retry costs money.
- Large outputs and `max_tokens`: check `stop_reason == "max_tokens"` before parsing, since
  truncated JSON will not validate.
"""

if __name__ == "__main__":
    api = make_client()
    caching_demo(api)
    parse_demo(api)
    raw_schema_demo(api)
    validation_demo()
