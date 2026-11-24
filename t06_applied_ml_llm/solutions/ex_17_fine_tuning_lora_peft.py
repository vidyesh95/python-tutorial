"""Reference solution for Exercise 17: LoRA arithmetic and dataset validation."""

import numpy as np


def lora_param_count(d_in: int, d_out: int, r: int) -> int:
    return r * (d_in + d_out)


def trainable_fraction(layer_shapes: list[tuple[int, int]], r: int) -> float:
    full = sum(d_in * d_out for d_in, d_out in layer_shapes)
    lora = sum(lora_param_count(d_in, d_out, r) for d_in, d_out in layer_shapes)
    return lora / full


def lora_merge(w: np.ndarray, a: np.ndarray, b: np.ndarray, alpha: float) -> np.ndarray:
    return w + (alpha / a.shape[0]) * (b @ a)


def validate_chat_example(example: dict) -> list[str]:
    messages = example.get("messages")
    if not isinstance(messages, list) or not messages:
        return ["missing non-empty 'messages' list"]
    errors: list[str] = []
    for i, message in enumerate(messages):
        role = message.get("role")
        if role not in {"system", "user", "assistant"}:
            errors.append(f"message {i}: bad role {role!r}")
        if not str(message.get("content", "")).strip():
            errors.append(f"message {i}: empty content")
    if messages[-1].get("role") != "assistant":
        errors.append("last message must be from the assistant")
    return errors


def qlora_memory_gb(
    params_billion: float, adapter_params_million: float, base_bits: int = 4
) -> float:
    base = params_billion * base_bits / 8
    adapter = adapter_params_million * 1e6 * 12 / 1024**3
    return base + adapter
