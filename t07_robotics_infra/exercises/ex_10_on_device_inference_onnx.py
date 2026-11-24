"""Exercise 10: build, run and budget a tiny ONNX model.

Uses `onnx` and numpy only. onnxruntime has no Python 3.15 wheels, so models run on
`onnx.reference.ReferenceEvaluator` (same `run(None, feeds)` call shape).

Tasks
1. build_linear_relu_model: ONNX graph for y = Relu(x @ w + b), dynamic batch dim.
2. run_model: run a model on a float32 batch with the ReferenceEvaluator.
3. quantize_symmetric / dequantize: int8 symmetric per-tensor quantization.
4. latency_stats: p50/p95/p99/max from latency samples.
5. within_budget: is a high percentile of the latency under the budget?

Run: uv run pytest t07_robotics_infra -k onnx
"""

import numpy as np


def build_linear_relu_model(w: np.ndarray, b: np.ndarray):
    """Return an onnx.ModelProto computing y = Relu(x @ w + b).

    - input "x": float32, shape ["batch", w.shape[0]] (the batch dim is a NAMED dynamic dim)
    - output "y": float32, shape ["batch", w.shape[1]]
    - nodes MatMul(x, w) -> Add(., b) -> Relu, with `w` and `b` stored as float32
      initializers named "w" and "b"
    - opset 17 (helper.make_opsetid("", 17)) and model.ir_version = 8
    - the model must pass onnx.checker.check_model
    Hint: onnx.helper.make_node / make_graph / make_model, onnx.numpy_helper.from_array.
    """
    raise NotImplementedError


def run_model(model, x: np.ndarray) -> np.ndarray:
    """Run `model` (input name "x", first output) with onnx.reference.ReferenceEvaluator and
    return the output array. Cast x to float32 first.
    """
    raise NotImplementedError


def quantize_symmetric(x: np.ndarray) -> tuple[np.ndarray, float]:
    """Symmetric per-tensor int8 quantization.

    scale = max(|x|) / 127 (use scale 1.0 if x is all zeros); q = round(x / scale) clipped to
    [-127, 127] as np.int8. Return (q, scale).
    """
    raise NotImplementedError


def dequantize(q: np.ndarray, scale: float) -> np.ndarray:
    """Return q * scale as a float32 array."""
    raise NotImplementedError


def latency_stats(samples_ms: list[float]) -> dict[str, float]:
    """Return {"p50", "p95", "p99", "max"} (floats) using linear-interpolated percentiles
    (np.percentile defaults). Raise ValueError for an empty list.
    """
    raise NotImplementedError


def within_budget(samples_ms: list[float], budget_ms: float, percentile: float = 99.0) -> bool:
    """True if the given percentile of `samples_ms` is <= budget_ms. A single outlier above
    the budget must make a p100 check fail but not necessarily a p99 check. Raise ValueError
    for an empty list.
    """
    raise NotImplementedError
