"""Reference solution for Exercise 11: Ollama helpers."""

import json


def normalize_host(raw: str | None) -> str:
    host = (raw or "").strip().rstrip("/") or "http://localhost:11434"
    if "://" not in host:
        host = "http://" + host
    if not host.rsplit(":", 1)[-1].isdigit():
        host += ":11434"
    return host


def build_chat_payload(
    model: str,
    messages: list[dict[str, str]],
    *,
    stream: bool = False,
    options: dict | None = None,
) -> dict:
    payload: dict = {"model": model, "messages": messages, "stream": stream}
    if options is not None:
        payload["options"] = options
    return payload


def collect_stream(lines: list[str]) -> tuple[str, float | None]:
    parts: list[str] = []
    tps: float | None = None
    for line in lines:
        if not line.strip():
            continue
        obj = json.loads(line)
        parts.append(obj.get("message", {}).get("content", ""))
        if obj.get("done"):
            count, duration = obj.get("eval_count"), obj.get("eval_duration")
            if count is not None and duration:
                tps = count / (duration / 1e9)
    return "".join(parts), tps


def render_modelfile(base: str, system: str, **params: float | int | str) -> str:
    lines = [f"FROM {base}"]
    lines += [f"PARAMETER {k} {v}" for k, v in params.items()]
    lines.append(f"SYSTEM {system}")
    return "\n".join(lines)


def estimate_memory_gb(params_billion: float, bits: int, overhead_gb: float = 1.5) -> float:
    return params_billion * bits / 8 + overhead_gb
