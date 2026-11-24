"""Exercise 11: Ollama helpers (pure functions, no server needed).

Tasks
1. normalize_host(raw): turn an OLLAMA_HOST value into a base URL.
   None/"" -> "http://localhost:11434"; add "http://" when no scheme; add ":11434" when no
   port; strip a trailing "/".   "myhost" -> "http://myhost:11434"
2. build_chat_payload(model, messages, *, stream=False, options=None): the JSON body for
   POST /api/chat: {"model", "messages", "stream"} plus "options" ONLY when options is given.
3. collect_stream(lines): `lines` are NDJSON lines from a streamed /api/chat call (may contain
   blank lines). Concatenate every `message.content`; the final object has `"done": true`,
   `eval_count` (tokens) and `eval_duration` (nanoseconds). Return (text, tokens_per_second);
   tokens_per_second is None when those fields are missing or the duration is 0.
4. render_modelfile(base, system, **params): "FROM <base>", then one "PARAMETER k v" line per
   keyword (in order), then "SYSTEM <system>", joined by newlines (no trailing newline).
5. estimate_memory_gb(params_billion, bits, overhead_gb=1.5): weights take
   params_billion * bits / 8 GB; add the overhead (KV cache, runtime).

Run: uv run pytest t06_applied_ml_llm -k ex_11
"""


def normalize_host(raw: str | None) -> str:
    raise NotImplementedError


def build_chat_payload(
    model: str,
    messages: list[dict[str, str]],
    *,
    stream: bool = False,
    options: dict | None = None,
) -> dict:
    raise NotImplementedError


def collect_stream(lines: list[str]) -> tuple[str, float | None]:
    raise NotImplementedError


def render_modelfile(base: str, system: str, **params: float | int | str) -> str:
    raise NotImplementedError


def estimate_memory_gb(params_billion: float, bits: int, overhead_gb: float = 1.5) -> float:
    raise NotImplementedError
