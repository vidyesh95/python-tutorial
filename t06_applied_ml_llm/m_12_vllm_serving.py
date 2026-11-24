# Serving Models with vLLM
"""
vLLM is a high-throughput inference ENGINE for open-weight LLMs on GPUs. Where Ollama
(m_11) targets one user on a laptop, vLLM targets many concurrent users on server GPUs.
It is Linux + NVIDIA/AMD GPU software: it does NOT run on macOS, so this lesson explains the
ideas, simulates them, and talks to a mocked server.

Why it is fast
- KV CACHE: for every token already processed the model keeps key/value tensors so it need not
  recompute them. This memory (not the weights) limits how many requests fit on a GPU.
- PAGEDATTENTION: instead of reserving one big contiguous KV buffer per request (wasting
  60-80% of memory), vLLM stores KV in small fixed-size blocks (e.g. 16 tokens) tracked by a
  block table, like virtual-memory paging. Waste drops to < 1 block per request, so more
  requests fit, so throughput goes up.
- CONTINUOUS BATCHING: the scheduler works per decoding step. A finished request leaves the
  batch immediately and a waiting one joins, instead of waiting for the slowest request.
- Also: prefix caching (shared system prompts), chunked prefill, quantization (AWQ/GPTQ/FP8),
  tensor parallelism across GPUs, speculative decoding.

Serving
    vllm serve Qwen/Qwen3-8B --max-model-len 8192 --gpu-memory-utilization 0.90 --port 8000
  exposes an OpenAI-COMPATIBLE API: /v1/models, /v1/chat/completions, /v1/completions,
  /v1/embeddings. Any OpenAI-style client works; we use plain `httpx` against it.
  Key flags: --max-model-len (context limit; the biggest KV-memory knob),
  --gpu-memory-utilization (fraction of VRAM vLLM may claim), --tensor-parallel-size,
  --max-num-seqs (max concurrent sequences), --quantization, --api-key.
Offline/batch use (also Linux/GPU only):
    from vllm import LLM, SamplingParams
    llm = LLM(model="Qwen/Qwen3-8B")
    outs = llm.generate(["Hello"], SamplingParams(temperature=0, max_tokens=64))

Configure the client with VLLM_BASE_URL (e.g. http://gpu-box:8000/v1). If it is unset or
unreachable (checked with a 1 s timeout) the same code runs against `httpx.MockTransport`.
Run it: uv run python -m t06_applied_ml_llm.m_12_vllm_serving
"""

import json
import math
import os
import time
from collections.abc import Callable, Iterator

import httpx
import numpy as np

VLLM_MODEL = os.getenv("VLLM_MODEL", "Qwen/Qwen3-8B")


# Example: KV-cache memory math (why context length and concurrency trade off)
def kv_bytes_per_token(layers: int, kv_heads: int, head_dim: int, dtype_bytes: int = 2) -> int:
    return 2 * layers * kv_heads * head_dim * dtype_bytes  # 2 = keys and values


def max_concurrent_sequences(
    gpu_gb: float, weights_gb: float, utilization: float, bytes_per_token: int, context_len: int
) -> int:
    kv_budget = gpu_gb * utilization * 1024**3 - weights_gb * 1024**3
    return max(0, int(kv_budget // (bytes_per_token * context_len)))


# Example: a toy paged KV cache (block table per sequence)
class PagedKVCache:
    def __init__(self, num_blocks: int, block_size: int = 16) -> None:
        self.block_size = block_size
        self.free_blocks = list(range(num_blocks))
        self.tables: dict[str, list[int]] = {}

    def append_tokens(self, seq: str, n_tokens: int, current_len: int) -> None:
        table = self.tables.setdefault(seq, [])
        needed = math.ceil((current_len + n_tokens) / self.block_size) - len(table)
        if needed > len(self.free_blocks):
            raise MemoryError("KV cache full: preempt or queue the request")
        table.extend(self.free_blocks.pop() for _ in range(needed))

    def free(self, seq: str) -> None:
        self.free_blocks.extend(self.tables.pop(seq, []))


# Example: static vs continuous batching, counted in decode steps
def static_batching_steps(lengths: list[int], batch_size: int) -> int:
    chunks = (lengths[i : i + batch_size] for i in range(0, len(lengths), batch_size))
    return sum(max(c) for c in chunks)  # every batch waits for its slowest member


def continuous_batching_steps(lengths: list[int], batch_size: int) -> int:
    pending, running, steps = list(lengths), [], 0
    while pending or running:
        while pending and len(running) < batch_size:
            running.append(pending.pop(0))  # a free slot is refilled immediately
        running = [r - 1 for r in running if r - 1 > 0]
        steps += 1
    return steps


# Example: OpenAI-compatible client (works for vLLM, Ollama /v1, many hosted providers)
def build_chat_request(
    model: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 256,
    temperature: float = 0.0,
    stream: bool = False,
) -> dict:
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if stream:
        body["stream"] = True
    return body


def chat(client: httpx.Client, messages: list[dict[str, str]]) -> tuple[str, dict]:
    resp = client.post("/chat/completions", json=build_chat_request(VLLM_MODEL, messages))
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"], data["usage"]


def parse_sse(lines: list[str]) -> Iterator[str]:
    """Server-sent events: `data: {json}` lines, terminated by `data: [DONE]`."""
    for line in lines:
        if not line.startswith("data:"):
            continue
        payload = line.removeprefix("data:").strip()
        if payload == "[DONE]":
            return
        delta = json.loads(payload)["choices"][0]["delta"]
        if delta.get("content"):
            yield delta["content"]


def stream_chat(client: httpx.Client, messages: list[dict[str, str]]) -> Iterator[str]:
    body = build_chat_request(VLLM_MODEL, messages, stream=True)
    with client.stream("POST", "/chat/completions", json=body) as resp:
        resp.raise_for_status()
        yield from parse_sse(list(resp.iter_lines()))


# Example: a fake vLLM server so the lesson runs anywhere
def fake_vllm_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/models"):
        return httpx.Response(200, json={"data": [{"id": VLLM_MODEL}]})
    body = json.loads(request.content)
    words = ["vLLM", " batches", " requests", " continuously."]
    if body.get("stream"):
        events = [{"choices": [{"delta": {"content": w}}]} for w in words]
        text = "".join(f"data: {json.dumps(e)}\n\n" for e in events) + "data: [DONE]\n\n"
        return httpx.Response(200, content=text, headers={"content-type": "text/event-stream"})
    usage = {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16}
    reply = {
        "choices": [{"message": {"role": "assistant", "content": "".join(words)}}],
        "usage": usage,
    }
    return httpx.Response(200, json=reply)


def make_client() -> tuple[httpx.Client, bool]:
    base = os.getenv("VLLM_BASE_URL", "").rstrip("/")
    headers = {
        "Authorization": f"Bearer {os.getenv('VLLM_API_KEY', 'EMPTY')}"
    }  # vLLM ignores it unless --api-key
    if base:
        try:
            httpx.get(f"{base}/models", timeout=1.0, headers=headers).raise_for_status()
            return httpx.Client(base_url=base, headers=headers, timeout=60), True
        except httpx.HTTPError:
            pass
    return httpx.Client(
        base_url="http://vllm.invalid/v1", transport=httpx.MockTransport(fake_vllm_handler)
    ), False


def benchmark(fn: Callable[[], object], n: int = 50) -> float:
    start = time.perf_counter()
    for _ in range(n):
        fn()
    return n / (time.perf_counter() - start)  # requests per second


"""
Common mistakes
- Setting --max-model-len to the model's maximum (128k) when you need 8k: the KV cache budget
  is reserved per sequence, so concurrency collapses.
- --gpu-memory-utilization 0.99: leaves no headroom for activations and CUDA graphs (OOM).
- Benchmarking with one request at a time. vLLM's win is concurrency; measure with many
  in-flight requests and report p50/p95 latency AND tokens/s.
- Forgetting the chat template for base models, or sending `stream: true` and not parsing SSE.
- Treating "OpenAI-compatible" as "identical": check tool-calling, JSON-mode and logprobs
  support per model/version.

Production notes
- Run `vllm serve` behind a gateway (auth, rate limits, logging); pass --api-key at minimum.
- Autoscale on queue depth / KV-cache utilization (exposed at /metrics for Prometheus), not CPU.
- Pin the vLLM and CUDA versions in your image; upgrades change memory use and performance.
- Keep the client provider-agnostic (m_18) so you can fail over to a hosted model.
"""

if __name__ == "__main__":
    # Llama-3-8B-like shape: 32 layers, 8 KV heads, head_dim 128, fp16
    per_token = kv_bytes_per_token(32, 8, 128)
    print(
        f"KV cache: {per_token // 1024} KiB per token, {per_token * 8192 / 1024**3:.1f} GiB for 8k context"
    )
    for ctx in (4096, 8192, 32768):
        n = max_concurrent_sequences(80, 16, 0.9, per_token, ctx)
        print(f"  80 GB GPU, 16 GB weights, ctx={ctx:>5}: ~{n} concurrent sequences")

    cache = PagedKVCache(num_blocks=8, block_size=16)
    cache.append_tokens("a", 40, 0)  # 40 tokens -> 3 blocks (waste: 8 slots)
    cache.append_tokens("b", 10, 0)  # 10 tokens -> 1 block
    print("block tables:", cache.tables, "free blocks:", len(cache.free_blocks))
    cache.free("a")
    print("after freeing a:", len(cache.free_blocks), "free blocks")

    rng = np.random.default_rng(0)
    lengths = [int(x) for x in rng.integers(4, 60, size=12)]
    print("output lengths:", lengths)
    print("static batching steps    :", static_batching_steps(lengths, 4))
    print("continuous batching steps:", continuous_batching_steps(lengths, 4))

    client, live = make_client()
    print(
        "server:",
        "LIVE (VLLM_BASE_URL)" if live else "not configured/reachable, using MockTransport",
    )
    messages = [{"role": "user", "content": "How does vLLM batch requests?"}]
    text, usage = chat(client, messages)
    print("chat  :", text, usage)
    print("stream:", list(stream_chat(client, messages)))
    print(
        f"mock throughput: {benchmark(lambda: chat(client, messages)):.0f} req/s (client overhead only)"
    )
