# Local Models with Ollama
"""
Ollama runs open-weight models (Llama, Qwen, Mistral, Gemma, ...) on your own machine and
exposes them through a small HTTP API on port 11434. No API key, no per-token bill, and your
data never leaves the machine.

CLI cheat sheet
    ollama serve                      # start the server (the desktop app does this for you)
    ollama pull llama3.2              # download a model (quantized GGUF, ~2 GB for 3B)
    ollama run qwen3 "Hello"          # one-shot or interactive chat
    ollama list / ollama ps           # installed models / models loaded in memory
    ollama create my-bot -f Modelfile # build a customised model
    ollama rm gemma3                  # delete

Model families: Llama (Meta), Qwen (Alibaba), Mistral, Gemma (Google). Tags choose size and
quantization: `llama3.2:3b`, `qwen3:8b`, `gemma3:4b-it-q4_K_M`. Quantization (Q4_K_M ~ 4.5 bits
per weight) trades a little quality for ~4x less memory. Rule of thumb: RAM needed ~
params_in_billions * bits / 8 GB + 1-2 GB for context.

REST API (all JSON; streaming = NEWLINE-DELIMITED JSON, one object per line)
    POST /api/chat    {"model", "messages", "stream", "options", "tools", "format"}
    POST /api/generate  (raw prompt, no chat template)
    POST /api/embed   {"model": "nomic-embed-text", "input": ["a", "b"]} -> {"embeddings": [[..]]}
    GET  /api/tags    installed models         (we use it as a <=1s health check)
Ollama also serves an OpenAI-compatible API at /v1/chat/completions (see m_12, m_18).

The Python package `ollama` wraps this: `ollama.Client(host).chat(model=..., messages=[...])`.
Set the server address with `OLLAMA_HOST` (e.g. `127.0.0.1:11434`).

Modelfile = Dockerfile for models:
    FROM llama3.2
    PARAMETER temperature 0.2
    SYSTEM You are a terse code reviewer.

This lesson runs fully offline: if no Ollama server answers within 1 second, the SAME client
code runs against an `httpx.MockTransport` that imitates the server.
Run it: uv run python -m t06_applied_ml_llm.m_11_ollama_local_models
"""

import json
import os
from collections.abc import Callable, Iterator

import httpx
import ollama

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def normalize_host(raw: str | None) -> str:
    """OLLAMA_HOST may be '0.0.0.0:11434' or 'myhost' (no scheme/port). Return a URL."""
    host = (raw or "").strip().rstrip("/") or "http://localhost:11434"
    if "://" not in host:
        host = "http://" + host
    if not host.rsplit(":", 1)[-1].isdigit():  # no port given
        host += ":11434"
    return host


def ollama_reachable(host: str, timeout: float = 1.0) -> bool:
    try:
        return httpx.get(f"{host}/api/tags", timeout=timeout).status_code == 200
    except httpx.HTTPError:
        return False


# Example: a fake Ollama server (what the real one returns, trimmed)
def fake_ollama_handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content or b"{}")
    if request.url.path == "/api/embed":
        inputs = body["input"] if isinstance(body["input"], list) else [body["input"]]
        return httpx.Response(
            200, json={"model": body["model"], "embeddings": [[1.0, 0.0]] * len(inputs)}
        )
    if request.url.path == "/api/chat":
        words = ["Local", " models", " are", " private", "."]
        if body.get("stream"):
            lines = [{"message": {"role": "assistant", "content": w}, "done": False} for w in words]
            lines.append(
                {
                    "message": {"role": "assistant", "content": ""},
                    "done": True,
                    "eval_count": 5,
                    "eval_duration": 250_000_000,
                }
            )
            return httpx.Response(200, content="".join(json.dumps(x) + "\n" for x in lines))
        return httpx.Response(
            200,
            json={
                "model": body["model"],
                "message": {"role": "assistant", "content": "".join(words)},
                "done": True,
                "eval_count": 5,
            },
        )
    return httpx.Response(404, json={"error": "not found"})


def make_client(host: str) -> tuple[ollama.Client, bool]:
    """Real client when a server is reachable, otherwise the same client over a fake transport."""
    if ollama_reachable(host):
        return ollama.Client(host=host, timeout=60), True
    return ollama.Client(host=host, transport=httpx.MockTransport(fake_ollama_handler)), False


# Example: chat, streaming, embeddings
def chat(client: ollama.Client, prompt: str, system: str | None = None) -> str:
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    response = client.chat(model=OLLAMA_MODEL, messages=messages, options={"temperature": 0})
    return response.message.content or ""


def stream_chat(client: ollama.Client, prompt: str) -> Iterator[str]:
    for chunk in client.chat(
        model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}], stream=True
    ):
        if chunk.message.content:
            yield chunk.message.content


def embed(client: ollama.Client, texts: list[str]) -> list[list[float]]:
    return [list(v) for v in client.embed(model=EMBED_MODEL, input=texts).embeddings]


# Example: raw NDJSON parsing, to see what the SDK does for you
def parse_ndjson(lines: list[str], on_text: Callable[[str], None]) -> dict:
    final: dict = {}
    for line in filter(None, (ln.strip() for ln in lines)):
        obj = json.loads(line)
        on_text(obj.get("message", {}).get("content", ""))
        if obj.get("done"):
            final = obj
    return final


# Example: a Modelfile builder
def render_modelfile(base: str, system: str, **params: float | int) -> str:
    lines = (
        [f"FROM {base}"] + [f"PARAMETER {k} {v}" for k, v in params.items()] + [f"SYSTEM {system}"]
    )
    return "\n".join(lines)


"""
Common mistakes
- Binding to 0.0.0.0 (OLLAMA_HOST=0.0.0.0) exposes an unauthenticated server to your network.
- Forgetting `stream=True` consumption: a streamed call returns a generator, not a response.
- Using a chat model for embeddings. Use a dedicated embedding model (nomic-embed-text,
  mxbai-embed-large, bge-m3) and ALWAYS the same one for indexing and querying.
- Default context window is small (often 2k-4k tokens); long prompts are silently truncated.
  Raise it with `options={"num_ctx": 8192}` (costs memory).
- Comparing speed across machines without noting quantization and context length.

Production notes
- Ollama is excellent for laptops, dev boxes and edge devices. For many concurrent users on
  GPUs use vLLM (m_12); both speak the OpenAI wire format so the client code barely changes.
- `keep_alive` controls how long a model stays in RAM after the last request (cold-start is
  seconds); set `keep_alive=-1` for latency-sensitive services.
- Small local models hallucinate and follow instructions worse than frontier models. Evaluate
  them on YOUR task (m_16) before swapping them in.
"""

if __name__ == "__main__":
    host = normalize_host(os.getenv("OLLAMA_HOST"))
    client, live = make_client(host)
    print(f"Ollama at {host}: {'LIVE server' if live else 'not reachable, using fake transport'}")

    print("chat   :", chat(client, "Why run models locally?", system="Answer in one sentence."))
    print("stream :", "|".join(stream_chat(client, "Say it again")))
    print("embed  :", embed(client, ["alpha", "beta"]))

    # What the wire format looks like
    raw = [
        '{"message": {"content": "Hi"}, "done": false}',
        '{"message": {"content": " there"}, "done": false}',
        '{"message": {"content": ""}, "done": true, "eval_count": 20, "eval_duration": 1000000000}',
    ]
    parts: list[str] = []
    final = parse_ndjson(raw, parts.append)
    print(
        "ndjson :",
        "".join(parts),
        f"({final['eval_count'] / (final['eval_duration'] / 1e9):.0f} tokens/s)",
    )

    print("--- Modelfile ---")
    print(
        render_modelfile(
            "llama3.2", "You are a terse code reviewer.", temperature=0.2, num_ctx=4096
        )
    )
