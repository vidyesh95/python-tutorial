"""Reference solution for Exercise 12: vLLM / OpenAI-compatible serving helpers."""

import json


def build_chat_request(
    model: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 256,
    temperature: float = 0.0,
    stream: bool = False,
    stop: list[str] | None = None,
) -> dict:
    body: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if stream:
        body["stream"] = True
    if stop:
        body["stop"] = stop
    return body


def parse_sse(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        if not line.startswith("data:"):
            continue
        payload = line.removeprefix("data:").strip()
        if payload == "[DONE]":
            break
        delta = json.loads(payload)["choices"][0]["delta"]
        if delta.get("content"):
            out.append(delta["content"])
    return out


def kv_bytes_per_token(layers: int, kv_heads: int, head_dim: int, dtype_bytes: int = 2) -> int:
    return 2 * layers * kv_heads * head_dim * dtype_bytes


def max_concurrent_sequences(
    gpu_gb: float, weights_gb: float, utilization: float, bytes_per_token: int, context_len: int
) -> int:
    budget = (gpu_gb * utilization - weights_gb) * 1024**3
    return max(0, int(budget // (bytes_per_token * context_len)))


def continuous_batching_steps(lengths: list[int], batch_size: int) -> int:
    pending = list(lengths)
    running: list[int] = []
    steps = 0
    while pending or running:
        while pending and len(running) < batch_size:
            running.append(pending.pop(0))
        running = [r - 1 for r in running if r - 1 > 0]
        steps += 1
    return steps
