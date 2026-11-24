"""Exercise 17: LoRA arithmetic and dataset validation (numpy, no training).

Tasks
1. lora_param_count(d_in, d_out, r): trainable parameters of ONE LoRA adapter on a weight of
   shape (d_out, d_in): A is (r, d_in) and B is (d_out, r).
2. trainable_fraction(layer_shapes, r): `layer_shapes` is a list of (d_in, d_out). Return
   total LoRA params / total full-weight params (sum of d_in * d_out) as a float.
3. lora_merge(w, a, b, alpha): merged weight W' = W + (alpha / r) * (B @ A), where
   r = a.shape[0], w is (d_out, d_in), a is (r, d_in), b is (d_out, r). Do not modify `w`.
4. validate_chat_example(example): return a list of problems (empty list = valid) for one
   chat fine-tuning example {"messages": [{"role", "content"}, ...]}:
   - messages missing, not a list, or empty -> ["missing non-empty 'messages' list"] (stop)
   - for each message i: role not in {"system", "user", "assistant"} ->
     f"message {i}: bad role {role!r}"; blank/whitespace content -> f"message {i}: empty content"
   - last message role is not "assistant" -> "last message must be from the assistant"
5. qlora_memory_gb(params_billion, adapter_params_million, base_bits=4): frozen base weights
   take params_billion * base_bits / 8 GB; adapters need 12 bytes per parameter (bf16 weight +
   bf16 grad + fp32 Adam moments); 1 GB = 1024**3 bytes. Return the sum in GB.

Run: uv run pytest t06_applied_ml_llm -k ex_17
"""

import numpy as np


def lora_param_count(d_in: int, d_out: int, r: int) -> int:
    raise NotImplementedError


def trainable_fraction(layer_shapes: list[tuple[int, int]], r: int) -> float:
    raise NotImplementedError


def lora_merge(w: np.ndarray, a: np.ndarray, b: np.ndarray, alpha: float) -> np.ndarray:
    raise NotImplementedError


def validate_chat_example(example: dict) -> list[str]:
    raise NotImplementedError


def qlora_memory_gb(
    params_billion: float, adapter_params_million: float, base_bits: int = 4
) -> float:
    raise NotImplementedError
