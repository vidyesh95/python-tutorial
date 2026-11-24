# Provider Abstraction Layer
"""
Your application should depend on a tiny interface, not on one vendor's SDK. Then you can swap
Claude, Gemini or a local model by configuration, fail over when a provider is down, compare
providers in evals (m_16), and test everything with a fake. This is the seam the capstone uses.

The interface (a `typing.Protocol`: structural typing, no inheritance needed):
    class LLMClient(Protocol):
        def complete(self, messages, *, system=None, max_tokens=1024) -> Completion: ...
        def stream(self, messages, *, system=None, max_tokens=1024) -> Iterator[str]: ...
`messages` is a list of {"role": "user"|"assistant", "content": str}. `Completion` is OUR
normalized result: text, model, provider, token usage, latency, cost.

Adapters translate to each provider's wire format and map their errors to two of ours:
`RetryableError` (rate limit, overload, network, timeout) and `LLMError` (bad request, auth).
- ClaudeClient        anthropic SDK        (model `claude-opus-5-5`, override with CLAUDE_MODEL)
- GeminiClient        google-genai SDK     (model `gemini-3.8-flash`, override with GEMINI_MODEL)
- OpenAICompatClient  httpx to /v1/chat/completions: Ollama (m_11), vLLM (m_12), many hosts

Decorators implement the same interface by wrapping another client (the "decorator pattern"):
- RetryingClient   exponential backoff + jitter for RetryableError only
- FallbackClient   try providers in order; raise AllProvidersFailed with every error
- CostTracker      add up tokens and dollars across calls
Compose them:  FallbackClient([Retrying(Claude), Retrying(Gemini), Ollama])

TIMEOUTS belong on the underlying SDK/HTTP client (`timeout=`). Turn the SDK's own retries OFF
(`max_retries=0`) when you wrap it in RetryingClient, otherwise retries multiply (3 x 3 = 9).

`FakeLLM` replays scripted replies/errors: the backbone of fast, deterministic tests.
Everything below runs offline: real SDK clients are pointed at mock transports/fake objects
(never a real key). Run: uv run python -m t06_applied_ml_llm.m_18_provider_abstraction_layer
"""

import json
import os
import random
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Protocol

import httpx

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# $ per million tokens (input, output). Claude prices from Anthropic's model table; local models
# are free (unknown models count as $0 here). Prices change: re-check the providers' pricing
# pages before relying on these numbers.
PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "gemini-3.8-flash": (0.75, 3.75),  # introductory rate through 2026-12-31 (ai.google.dev)
}
Messages = list[dict[str, str]]


@dataclass
class Completion:
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0

    @property
    def cost_usd(self) -> float:
        price_in, price_out = PRICES.get(self.model, (0.0, 0.0))
        return (self.input_tokens * price_in + self.output_tokens * price_out) / 1_000_000


class LLMError(Exception):
    """Non-retryable failure (bad request, auth, refusal)."""


class RetryableError(LLMError):
    """Transient failure: rate limit, overload, timeout, network."""


class AllProvidersFailed(LLMError):
    def __init__(self, errors: list[Exception]) -> None:
        super().__init__("; ".join(f"{type(e).__name__}: {e}" for e in errors))
        self.errors = errors


class LLMClient(Protocol):
    name: str

    def complete(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Completion: ...

    def stream(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Iterator[str]: ...


def status_is_retryable(code: int) -> bool:
    return code in (408, 409, 429) or code >= 500


# Example: Claude adapter (takes an injected anthropic client so tests can fake it)
class ClaudeClient:
    name = "claude"

    def __init__(self, client, model: str = CLAUDE_MODEL) -> None:
        self.client, self.model = client, model

    def _kwargs(self, messages: Messages, system: str | None, max_tokens: int) -> dict:
        kwargs = {"model": self.model, "max_tokens": max_tokens, "messages": messages}
        return kwargs | ({"system": system} if system else {})

    def complete(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Completion:
        import anthropic

        start = time.perf_counter()
        try:
            resp = self.client.messages.create(**self._kwargs(messages, system, max_tokens))
        except anthropic.APIStatusError as exc:
            raise (RetryableError if status_is_retryable(exc.status_code) else LLMError)(
                str(exc)
            ) from exc
        except anthropic.APIConnectionError as exc:  # includes timeouts
            raise RetryableError(str(exc)) from exc
        if resp.stop_reason == "refusal":
            raise LLMError("model refused")
        text = "".join(b.text for b in resp.content if b.type == "text")
        usage = resp.usage
        return Completion(
            text,
            resp.model,
            self.name,
            usage.input_tokens,
            usage.output_tokens,
            time.perf_counter() - start,
        )

    def stream(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Iterator[str]:
        with self.client.messages.stream(**self._kwargs(messages, system, max_tokens)) as stream:
            yield from stream.text_stream


# Example: Gemini adapter (roles are "user"/"model", not "assistant")
class GeminiClient:
    name = "gemini"

    def __init__(self, client, model: str = GEMINI_MODEL) -> None:
        self.client, self.model = client, model

    def _request(self, messages: Messages, system: str | None, max_tokens: int) -> dict:
        from google.genai import types

        contents = [
            types.Content(
                role="model" if m["role"] == "assistant" else "user",
                parts=[types.Part(text=m["content"])],
            )
            for m in messages
        ]
        config = types.GenerateContentConfig(
            system_instruction=system, max_output_tokens=max_tokens
        )
        return {"model": self.model, "contents": contents, "config": config}

    def complete(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Completion:
        from google.genai import errors

        start = time.perf_counter()
        try:
            resp = self.client.models.generate_content(
                **self._request(messages, system, max_tokens)
            )
        except errors.APIError as exc:
            raise (RetryableError if status_is_retryable(exc.code) else LLMError)(str(exc)) from exc
        usage = resp.usage_metadata
        return Completion(
            resp.text or "",
            self.model,
            self.name,
            getattr(usage, "prompt_token_count", 0) or 0,
            getattr(usage, "candidates_token_count", 0) or 0,
            time.perf_counter() - start,
        )

    def stream(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Iterator[str]:
        for chunk in self.client.models.generate_content_stream(
            **self._request(messages, system, max_tokens)
        ):
            if chunk.text:
                yield chunk.text


# Example: OpenAI-compatible adapter (Ollama at :11434/v1, vLLM, hosted gateways)
class OpenAICompatClient:
    def __init__(self, http: httpx.Client, model: str, name: str = "openai-compat") -> None:
        self.http, self.model, self.name = http, model, name

    def _body(self, messages: Messages, system: str | None, max_tokens: int, stream: bool) -> dict:
        msgs = ([{"role": "system", "content": system}] if system else []) + messages
        return {"model": self.model, "messages": msgs, "max_tokens": max_tokens, "stream": stream}

    def complete(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Completion:
        start = time.perf_counter()
        try:
            resp = self.http.post(
                "/chat/completions", json=self._body(messages, system, max_tokens, False)
            )
        except httpx.TransportError as exc:  # timeouts and connection errors
            raise RetryableError(str(exc)) from exc
        if resp.status_code >= 400:
            raise (RetryableError if status_is_retryable(resp.status_code) else LLMError)(
                f"HTTP {resp.status_code}"
            )
        data = resp.json()
        usage = data.get("usage", {})
        return Completion(
            data["choices"][0]["message"]["content"],
            self.model,
            self.name,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            time.perf_counter() - start,
        )

    def stream(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Iterator[str]:
        with self.http.stream(
            "POST", "/chat/completions", json=self._body(messages, system, max_tokens, True)
        ) as resp:
            if resp.status_code >= 400:
                raise (RetryableError if status_is_retryable(resp.status_code) else LLMError)(
                    f"HTTP {resp.status_code}"
                )
            for line in resp.iter_lines():
                if not line.startswith("data:") or line.endswith("[DONE]"):
                    continue
                delta = json.loads(line.removeprefix("data:"))["choices"][0]["delta"].get("content")
                if delta:
                    yield delta


# Example: FakeLLM for tests: items are reply strings or exceptions to raise
class FakeLLM:
    def __init__(
        self, script: list[str | Exception], name: str = "fake", model: str = "fake-1"
    ) -> None:
        self.script, self.name, self.model = list(script), name, model
        self.calls: list[Messages] = []

    def _next(self, messages: Messages) -> str:
        self.calls.append(messages)
        item = self.script.pop(0) if self.script else "ok"
        if isinstance(item, Exception):
            raise item
        return item

    def complete(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Completion:
        text = self._next(messages)
        return Completion(
            text,
            self.model,
            self.name,
            sum(len(m["content"].split()) for m in messages),
            len(text.split()),
        )

    def stream(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Iterator[str]:
        yield from (w + " " for w in self._next(messages).split())


# Example: decorators that add behaviour to ANY client
def backoff_delay(
    attempt: int, base: float = 0.5, cap: float = 8.0, rng: random.Random | None = None
) -> float:
    """Exponential backoff with 'equal jitter' so many clients do not retry in lockstep."""
    ceiling = min(cap, base * 2**attempt)
    return ceiling / 2 + (rng or random).random() * ceiling / 2


class RetryingClient:
    def __init__(
        self,
        inner: LLMClient,
        max_attempts: int = 3,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        self.inner, self.max_attempts, self.sleep, self.rng = inner, max_attempts, sleep, rng
        self.name = inner.name

    def complete(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Completion:
        for attempt in range(self.max_attempts):
            try:
                return self.inner.complete(messages, system=system, max_tokens=max_tokens)
            except RetryableError:
                if attempt == self.max_attempts - 1:
                    raise
                self.sleep(backoff_delay(attempt, rng=self.rng))
        raise AssertionError("unreachable")

    def stream(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Iterator[str]:
        return self.inner.stream(
            messages, system=system, max_tokens=max_tokens
        )  # only safe to retry BEFORE the first chunk


class FallbackClient:
    name = "fallback"

    def __init__(self, providers: list[LLMClient]) -> None:
        self.providers = providers
        self.last_used: str | None = None

    def complete(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Completion:
        errors: list[Exception] = []
        for provider in self.providers:
            try:
                result = provider.complete(messages, system=system, max_tokens=max_tokens)
                self.last_used = provider.name
                return result
            except LLMError as exc:  # a 400 from one provider may still work on another
                errors.append(exc)
        raise AllProvidersFailed(errors)

    def stream(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Iterator[str]:
        errors: list[Exception] = []
        for provider in self.providers:
            try:
                it = provider.stream(messages, system=system, max_tokens=max_tokens)
                first = next(it)  # fail over only if nothing was emitted yet
            except StopIteration:
                return
            except LLMError as exc:
                errors.append(exc)
                continue
            self.last_used = provider.name
            yield first
            yield from it
            return
        raise AllProvidersFailed(errors)


class CostTracker:
    def __init__(self, inner: LLMClient) -> None:
        self.inner, self.name = inner, inner.name
        self.calls, self.input_tokens, self.output_tokens, self.cost_usd = 0, 0, 0, 0.0

    def complete(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Completion:
        result = self.inner.complete(messages, system=system, max_tokens=max_tokens)
        self.calls += 1
        self.input_tokens += result.input_tokens
        self.output_tokens += result.output_tokens
        self.cost_usd += result.cost_usd
        return result

    def stream(
        self, messages: Messages, *, system: str | None = None, max_tokens: int = 1024
    ) -> Iterator[str]:
        return self.inner.stream(
            messages, system=system, max_tokens=max_tokens
        )  # streamed usage needs provider-specific handling


# Example: a shared CONTRACT test every adapter must pass
def check_contract(client: LLMClient, *, streaming: bool = True) -> list[str]:
    problems = []
    result = client.complete(
        [{"role": "user", "content": "ping"}], system="Be brief.", max_tokens=50
    )
    if not isinstance(result, Completion) or not result.text:
        problems.append("complete() must return a non-empty Completion")
    elif not result.model or (result.provider != client.name and client.name != "fallback"):
        problems.append("Completion needs model and provider")
    if streaming:
        chunks = list(client.stream([{"role": "user", "content": "ping"}], max_tokens=50))
        if not chunks or not all(isinstance(c, str) for c in chunks):
            problems.append("stream() must yield str chunks")
    return problems


# Example: fakes for each provider so the demo runs offline
def fake_claude_client(fail_first: int = 0):
    """The REAL anthropic SDK pointed at a mock HTTP transport."""
    import anthropic

    try:
        import httpx2 as http  # anthropic 1.x/2.x are built on httpx2
    except ImportError:
        import httpx as http  # anthropic 0.x used httpx

    state = {"left": fail_first}

    def handler(request: http.Request) -> http.Response:
        if state["left"] > 0:
            state["left"] -= 1
            return http.Response(
                429,
                json={
                    "type": "error",
                    "error": {"type": "rate_limit_error", "message": "slow down"},
                },
            )
        body = {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": CLAUDE_MODEL,
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "content": [{"type": "text", "text": "Hello from (mock) Claude"}],
            "usage": {"input_tokens": 120, "output_tokens": 30},
        }
        return http.Response(200, json=body)

    # max_retries=0: OUR RetryingClient owns retry policy
    return anthropic.Anthropic(
        api_key="test-key",
        max_retries=0,
        http_client=http.Client(transport=http.MockTransport(handler)),
    )


def fake_gemini_client(error: Exception | None = None):
    from google.genai import types

    def reply(text: str):
        part = types.Content(role="model", parts=[types.Part(text=text)])
        usage = types.GenerateContentResponseUsageMetadata(
            prompt_token_count=80, candidates_token_count=20
        )
        return types.GenerateContentResponse(
            candidates=[types.Candidate(content=part)], usage_metadata=usage
        )

    def generate_content(**_kw):
        if error:
            raise error
        return reply("Hello from (fake) Gemini")

    def generate_content_stream(**_kw):
        yield from (reply(w) for w in ("Hello ", "from ", "Gemini"))

    return SimpleNamespace(
        models=SimpleNamespace(
            generate_content=generate_content, generate_content_stream=generate_content_stream
        )
    )


def fake_ollama_http() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["stream"]:
            events = "".join(
                f"data: {json.dumps({'choices': [{'delta': {'content': w}}]})}\n\n"
                for w in ("Hello ", "from ", "llama")
            )
            return httpx.Response(200, content=events + "data: [DONE]\n\n")
        usage = {"prompt_tokens": 50, "completion_tokens": 10}
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Hello from (mock) Ollama"}}],
                "usage": usage,
            },
        )

    return httpx.Client(
        base_url="http://localhost:11434/v1", transport=httpx.MockTransport(handler)
    )


def build_from_env() -> LLMClient | None:
    """Real clients only when configured; returns None when nothing is available."""
    chain: list[LLMClient] = []
    if os.getenv("ANTHROPIC_API_KEY"):
        import anthropic

        chain.append(RetryingClient(ClaudeClient(anthropic.Anthropic(max_retries=0, timeout=30.0))))
    if os.getenv("GEMINI_API_KEY"):
        from google import genai

        chain.append(RetryingClient(GeminiClient(genai.Client())))
    if base := os.getenv("VLLM_BASE_URL"):
        chain.append(
            OpenAICompatClient(
                httpx.Client(base_url=base, timeout=30),
                os.getenv("VLLM_MODEL", "Qwen/Qwen3-8B"),
                "vllm",
            )
        )
    return FallbackClient(chain) if chain else None


"""
Common mistakes
- Leaking provider types (anthropic.Message, genai responses) into app code: the abstraction
  is then fake. Convert at the adapter boundary.
- Retrying non-idempotent or non-retryable errors (400/401): it only burns time and money.
- Stacking SDK retries under your own retries without counting them.
- Failing over silently: record which provider answered (and why) or quality drift is invisible.
- Lowest-common-denominator API: do not hide features you need (tool use, caching, thinking)
  behind the interface; expose provider-specific options through an explicit `extra` argument.
- Assuming equal behaviour: the same prompt can behave differently per model. Run evals (m_16) per provider.

Production notes
- Add a circuit breaker (stop calling a provider that failed N times for a cool-down period).
- Put a total deadline on the whole chain, not just per-provider timeouts.
- Log provider, model, tokens, latency, cost and request id for every call; alert on cost per day.
- Claude models can decline (stop_reason "refusal"); this layer maps that to LLMError so the chain can
  fall back. Anthropic also offers server-side refusal `fallbacks` (beta) for Claude-to-Claude routing.
- For pure Claude apps the SDK's own `max_retries` may be enough; add this layer when you need
  more than one provider.
"""

if __name__ == "__main__":
    messages: Messages = [{"role": "user", "content": "Say hello"}]
    sleeps: list[float] = []
    rng = random.Random(0)  # seeded: reproducible jitter

    # 1) Claude adapter over the real SDK + mock transport; first two calls get HTTP 429
    claude = ClaudeClient(fake_claude_client(fail_first=2))
    retrying = RetryingClient(claude, max_attempts=4, sleep=sleeps.append, rng=rng)
    result = retrying.complete(messages, system="Be brief.")
    print(
        f"claude : {result.text!r} after {len(sleeps)} retries, backoff delays {[round(s, 2) for s in sleeps]}"
    )
    print(
        f"         model={result.model} tokens={result.input_tokens}+{result.output_tokens} cost=${result.cost_usd:.5f}"
    )

    # 2) Gemini and Ollama adapters
    gemini = GeminiClient(fake_gemini_client())
    ollama = OpenAICompatClient(fake_ollama_http(), "llama3.2", name="ollama")
    print("gemini :", gemini.complete(messages).text, "|", "".join(gemini.stream(messages)))
    print("ollama :", ollama.complete(messages).text, "|", "".join(ollama.stream(messages)))

    # 3) Fallback chain: Claude down (always 429), Gemini overloaded (503), Ollama answers
    from google.genai import errors as genai_errors

    down_claude = RetryingClient(
        ClaudeClient(fake_claude_client(fail_first=99)),
        max_attempts=2,
        sleep=sleeps.append,
        rng=rng,
    )
    busy_gemini = GeminiClient(
        fake_gemini_client(genai_errors.ServerError(503, {"error": {"message": "overloaded"}}))
    )
    chain = FallbackClient([down_claude, busy_gemini, ollama])
    tracked = CostTracker(chain)
    answer = tracked.complete(messages)
    print(f"chain  : answered by {chain.last_used!r}: {answer.text!r}")
    try:
        FallbackClient([FakeLLM([RetryableError("a")]), FakeLLM([LLMError("b")])]).complete(
            messages
        )
    except AllProvidersFailed as exc:
        print("all fail:", exc)

    # 4) The same contract check runs against every adapter (Claude streaming needs SSE mocking: skipped)
    for client in (ClaudeClient(fake_claude_client()), gemini, ollama, FakeLLM(["pong", "pong"])):
        print(
            f"contract[{client.name}]:",
            check_contract(client, streaming=client.name != "claude") or "ok",
        )

    real = build_from_env()
    print(
        "real providers configured:",
        real is not None and [p.name for p in real.providers] or "none (offline demo only)",
    )
