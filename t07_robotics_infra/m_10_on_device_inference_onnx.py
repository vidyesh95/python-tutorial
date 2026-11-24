# On-Device Inference with ONNX
"""
ONNX (Open Neural Network Exchange) is a portable file format for a trained model: a GRAPH
of operators (MatMul, Add, Relu, Conv...) plus WEIGHTS (initializers). Train in PyTorch,
export once, run anywhere with a small runtime, without shipping Python training code.

Pieces
- `onnx.helper` builds a graph by hand: `make_node` (an op), `make_tensor_value_info`
  (an input/output with dtype and shape), `numpy_helper.from_array` (a weight), `make_graph`,
  `make_model` (adds the opset: the version of the operator definitions).
- `onnx.checker.check_model` validates structure; `onnx.shape_inference.infer_shapes`
  fills in intermediate tensor shapes. Use both in CI for every model you ship.
- Dynamic axes: give the batch dim a NAME ("batch") instead of a number so one model serves
  batch sizes 1..N.
- Runtime: on real devices use `onnxruntime` (CPU/ARM, GPU, NPU execution providers) or
  TensorRT on NVIDIA Jetson. onnxruntime has NO Python 3.15 wheels yet, so this lesson uses
  `onnx.reference.ReferenceEvaluator`: a slow, pure-Python/numpy interpreter that is exact
  enough to verify a graph is correct, and has the same `run(None, {name: array})` shape.
  Swap in `onnxruntime.InferenceSession(path).run(None, feeds)` once wheels exist.

Quantization (smaller and faster, slightly less accurate)
- float32 weights (4 bytes) -> int8 (1 byte): 4x smaller, and int8 math is much faster on
  CPUs/NPUs with integer units.
- Symmetric per-tensor: scale = max|x| / 127, q = round(x / scale) clipped to [-127, 127],
  back with x ~ q * scale. The error per value is at most scale / 2.
- In ONNX this is `QuantizeLinear` / `DequantizeLinear` (QDQ) nodes. Post-training
  quantization needs CALIBRATION DATA that looks like real inputs, or the scale is wrong.
  Always re-measure accuracy on a held-out set after quantizing.

Latency budgeting
- A 50 Hz control loop gives 20 ms per cycle for sensing + inference + actuation. Budget the
  inference share (say 30%) and judge it by a HIGH PERCENTILE (p95/p99), not the mean: one
  slow frame is a missed deadline. Warm up first (first runs allocate/compile), measure on the
  TARGET device with realistic batch size and input, and use `time.perf_counter_ns`.

Common mistakes
- Feeding float64 or the wrong layout: ONNX is strict (float32 stays float32); mean/std
  preprocessing must match training EXACTLY.
- Fixed batch dim baked in during export, then failing at batch 2.
- Benchmarking on your laptop and assuming the robot matches.
- Quantizing without calibration data or without re-checking accuracy.
- Using the mean latency as the budget.

Production notes
- Version model files and record the sha256; refuse to load a file whose hash is wrong, and
  roll out new models like any OTA update (canary first, see m_09).
- Validate inputs: shape, dtype, NaN/inf, and plausible ranges. Never trust sensor data
  blindly: a stuck or NaN sensor must trigger a safe fallback, not garbage inference.
- Keep a deterministic fallback (rule-based controller or last known good model) and a
  watchdog: if inference exceeds its deadline, drop the result and use the fallback.
- Pin opset versions: the runtime must support the opset you exported.
"""

import hashlib
import importlib.util
import time
import warnings

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper, shape_inference
from onnx.reference import ReferenceEvaluator

OPSET = 17  # widely supported by runtimes
QDQ_OPSET = 19  # the reference evaluator implements Quantize/DequantizeLinear from here


def _model(graph: onnx.GraphProto, opset: int, ir_version: int) -> onnx.ModelProto:
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", opset)])
    model.ir_version = ir_version
    onnx.checker.check_model(model)
    return model


# Example 1: build a tiny MLP (4 -> 8 -> 2) with onnx.helper
def build_mlp(w1: np.ndarray, b1: np.ndarray, w2: np.ndarray, b2: np.ndarray) -> onnx.ModelProto:
    n_in, n_out = w1.shape[0], w2.shape[1]
    nodes = [
        helper.make_node("MatMul", ["x", "w1"], ["h0"]),
        helper.make_node("Add", ["h0", "b1"], ["h1"]),
        helper.make_node("Relu", ["h1"], ["h2"]),
        helper.make_node("MatMul", ["h2", "w2"], ["o0"]),
        helper.make_node("Add", ["o0", "b2"], ["y"]),
    ]
    named = {"w1": w1, "b1": b1, "w2": w2, "b2": b2}
    weights = [numpy_helper.from_array(a.astype(np.float32), n) for n, a in named.items()]
    graph = helper.make_graph(
        nodes,
        "tiny_mlp",
        [helper.make_tensor_value_info("x", TensorProto.FLOAT, ["batch", n_in])],
        [helper.make_tensor_value_info("y", TensorProto.FLOAT, ["batch", n_out])],
        weights,
    )
    return _model(graph, OPSET, ir_version=8)


def random_weights(seed: int = 0) -> tuple[np.ndarray, ...]:
    rng = np.random.default_rng(seed)
    return (
        rng.normal(size=(4, 8)).astype(np.float32),
        rng.normal(size=8).astype(np.float32),
        rng.normal(size=(8, 2)).astype(np.float32),
        rng.normal(size=2).astype(np.float32),
    )


def numpy_mlp(x: np.ndarray, w1, b1, w2, b2) -> np.ndarray:
    return np.maximum(x @ w1 + b1, 0) @ w2 + b2


# Example 2: shape inference and inspection
def describe(model: onnx.ModelProto) -> dict[str, list]:
    inferred = shape_inference.infer_shapes(model)

    def dims(v: onnx.ValueInfoProto) -> list:
        return [d.dim_param or d.dim_value for d in v.type.tensor_type.shape.dim]

    return {
        "ops": [n.op_type for n in model.graph.node],
        "intermediate_shapes": [(v.name, dims(v)) for v in inferred.graph.value_info],
        "weights": [(i.name, list(i.dims)) for i in model.graph.initializer],
    }


# Example 3: run it, and preprocess inputs like the training pipeline did
def preprocess(raw: np.ndarray, mean: np.ndarray, std: np.ndarray, clip: float = 5.0) -> np.ndarray:
    if not np.all(np.isfinite(raw)):
        raise ValueError("non-finite sensor value: refuse to run inference")
    z = (raw - mean) / np.maximum(std, 1e-6)
    return np.clip(z, -clip, clip).astype(np.float32)  # ONNX wants float32


def run(model: onnx.ModelProto, x: np.ndarray) -> np.ndarray:
    return ReferenceEvaluator(model).run(None, {"x": x})[0]


# Example 4: int8 symmetric quantization
def quantize(x: np.ndarray) -> tuple[np.ndarray, float]:
    scale = float(np.abs(x).max()) / 127.0 or 1.0
    return np.clip(np.round(x / scale), -127, 127).astype(np.int8), scale


def dequantize(q: np.ndarray, scale: float) -> np.ndarray:
    return q.astype(np.float32) * np.float32(scale)


def qdq_model(scale: float) -> onnx.ModelProto:
    """The same quantize -> dequantize round trip, expressed as ONNX QDQ nodes."""
    graph = helper.make_graph(
        [
            helper.make_node("QuantizeLinear", ["x", "scale", "zp"], ["q"]),
            helper.make_node("DequantizeLinear", ["q", "scale", "zp"], ["y"]),
        ],
        "qdq",
        [helper.make_tensor_value_info("x", TensorProto.FLOAT, ["n"])],
        [helper.make_tensor_value_info("y", TensorProto.FLOAT, ["n"])],
        [
            numpy_helper.from_array(np.array(scale, dtype=np.float32), "scale"),
            numpy_helper.from_array(np.array(0, dtype=np.int8), "zp"),
        ],
    )
    return _model(graph, QDQ_OPSET, ir_version=9)


# Example 5: latency measurement and budgeting
def measure_ms(fn, runs: int = 100, warmup: int = 10) -> list[float]:
    for _ in range(warmup):
        fn()
    out = []
    for _ in range(runs):
        start = time.perf_counter_ns()
        fn()
        out.append((time.perf_counter_ns() - start) / 1e6)
    return out


def within_budget(samples_ms: list[float], budget_ms: float, percentile: float = 99.0) -> bool:
    return float(np.percentile(samples_ms, percentile)) <= budget_ms


# Example 6 (optional): export from PyTorch if installed, guarded
def export_from_torch() -> onnx.ModelProto | None:
    if importlib.util.find_spec("torch") is None:
        return None
    try:
        import io

        import torch

        torch.manual_seed(0)
        net = torch.nn.Sequential(torch.nn.Linear(4, 8), torch.nn.ReLU(), torch.nn.Linear(8, 2))
        buf = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # legacy exporter deprecation notice
            torch.onnx.export(
                net.eval(),
                (torch.zeros(1, 4),),
                buf,
                input_names=["x"],
                output_names=["y"],
                dynamic_axes={"x": {0: "batch"}, "y": {0: "batch"}},
                opset_version=OPSET,
                dynamo=False,
            )
        return onnx.load_from_string(buf.getvalue())
    except Exception as exc:  # exporter APIs change between torch versions
        print(f"  torch export skipped: {type(exc).__name__}")
        return None


def run_demo() -> None:
    w1, b1, w2, b2 = random_weights()
    model = build_mlp(w1, b1, w2, b2)
    info = describe(model)
    print("ops:", info["ops"])
    print("shapes:", info["intermediate_shapes"])

    rng = np.random.default_rng(1)
    raw = rng.normal(loc=10.0, scale=3.0, size=(3, 4))
    x = preprocess(raw, mean=np.full(4, 10.0), std=np.full(4, 3.0))
    out = run(model, x)
    ref = numpy_mlp(x, w1, b1, w2, b2)
    print("matches numpy:", np.allclose(out, ref, atol=1e-5), "output shape:", out.shape)

    q, scale = quantize(w1)
    err = float(np.abs(dequantize(q, scale) - w1).max())
    print(f"int8 weights: {q.nbytes} bytes vs {w1.nbytes}; max error {err:.4f} <= {scale / 2:.4f}")
    qdq = ReferenceEvaluator(qdq_model(scale)).run(None, {"x": np.array([0.0, 0.3, 99.0], "f4")})
    print("QDQ node output (99.0 saturates):", qdq[0])

    one = x[:1]
    samples = measure_ms(lambda: run(model, one), runs=50, warmup=5)
    print(
        f"reference evaluator p50={np.percentile(samples, 50):.3f} ms "
        f"p99={np.percentile(samples, 99):.3f} ms; "
        f"fits 6 ms budget (30% of 20 ms): {within_budget(samples, 6.0)}"
    )

    digest = hashlib.sha256(model.SerializeToString()).hexdigest()[:12]
    print("model sha256 (verify before loading on device):", digest)

    torch_model = export_from_torch()
    if torch_model is not None:
        print("torch export ops:", [n.op_type for n in torch_model.graph.node])
    else:
        print("torch not available: skipped the optional export example")


if __name__ == "__main__":
    run_demo()
