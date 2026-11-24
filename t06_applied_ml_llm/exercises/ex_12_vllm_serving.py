"""Exercise 12: vLLM / OpenAI-compatible serving helpers (no GPU needed).

Tasks
1. build_chat_request(model, messages, *, max_tokens=256, temperature=0.0, stream=False,
   stop=None): the JSON body for POST /v1/chat/completions: "model", "messages",
   "max_tokens", "temperature". Add "stream": True only when streaming and "stop" only when
   a list is given.
2. parse_sse(lines): `lines` are text lines of a streamed response. Each event line looks like
   `data: {"choices": [{"delta": {"content": "Hi"}}]}`; the stream ends with `data: [DONE]`.
   Return the list of non-empty content deltas, in order. Ignore blank lines, comments
   (":" prefix), and anything after [DONE].
3. kv_bytes_per_token(layers, kv_heads, head_dim, dtype_bytes=2): bytes of KV cache per token
   = 2 (keys + values) * layers * kv_heads * head_dim * dtype_bytes.
4. max_concurrent_sequences(gpu_gb, weights_gb, utilization, bytes_per_token, context_len):
   KV budget = gpu_gb * utilization - weights_gb (all in GiB, 1 GiB = 1024**3 bytes). Return
   how many full-context sequences fit (integer, never negative).
5. continuous_batching_steps(lengths, batch_size): `lengths[i]` = decode steps request i needs.
   Up to `batch_size` requests run at once; each step every running request advances by one
   token; a finished request leaves immediately and the next waiting request (FIFO) fills the
   slot at the START of the next step. Return the total number of steps. [] -> 0.

Run: uv run pytest t06_applied_ml_llm -k ex_12
"""


def build_chat_request(
    model: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 256,
    temperature: float = 0.0,
    stream: bool = False,
    stop: list[str] | None = None,
) -> dict:
    raise NotImplementedError


def parse_sse(lines: list[str]) -> list[str]:
    raise NotImplementedError


def kv_bytes_per_token(layers: int, kv_heads: int, head_dim: int, dtype_bytes: int = 2) -> int:
    raise NotImplementedError


def max_concurrent_sequences(
    gpu_gb: float, weights_gb: float, utilization: float, bytes_per_token: int, context_len: int
) -> int:
    raise NotImplementedError


def continuous_batching_steps(lengths: list[int], batch_size: int) -> int:
    raise NotImplementedError
