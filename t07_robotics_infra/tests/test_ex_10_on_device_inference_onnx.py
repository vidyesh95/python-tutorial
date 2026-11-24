import pytest

np = pytest.importorskip("numpy")
onnx = pytest.importorskip("onnx")
pytest.importorskip("onnx.reference")

from _loader import load  # noqa: E402

ex = load("t07_robotics_infra", "ex_10_on_device_inference_onnx")


@pytest.fixture
def weights():
    rng = np.random.default_rng(0)
    return rng.normal(size=(4, 3)).astype(np.float32), rng.normal(size=3).astype(np.float32)


def test_model_structure(weights):
    w, b = weights
    model = ex.build_linear_relu_model(w, b)
    onnx.checker.check_model(model)
    assert [n.op_type for n in model.graph.node] == ["MatMul", "Add", "Relu"]
    assert {i.name for i in model.graph.initializer} == {"w", "b"}
    assert model.opset_import[0].version == 17
    dims = model.graph.input[0].type.tensor_type.shape.dim
    assert dims[0].dim_param == "batch" and dims[1].dim_value == 4


def test_model_runs_with_dynamic_batch(weights):
    w, b = weights
    model = ex.build_linear_relu_model(w, b)
    rng = np.random.default_rng(1)
    for batch in (1, 5):
        x = rng.normal(size=(batch, 4)).astype(np.float32)
        out = ex.run_model(model, x)
        assert out.shape == (batch, 3)
        assert out.dtype == np.float32
        np.testing.assert_allclose(out, np.maximum(x @ w + b, 0), atol=1e-5)
        assert (out >= 0).all()


def test_run_model_casts_float64(weights):
    w, b = weights
    model = ex.build_linear_relu_model(w, b)
    out = ex.run_model(model, np.ones((2, 4), dtype=np.float64))
    assert out.shape == (2, 3)


def test_quantize_roundtrip_error_bounded():
    rng = np.random.default_rng(2)
    x = rng.normal(size=200).astype(np.float32)
    q, scale = ex.quantize_symmetric(x)
    assert q.dtype == np.int8
    assert scale == pytest.approx(float(np.abs(x).max()) / 127)
    assert int(np.abs(q).max()) == 127
    back = ex.dequantize(q, scale)
    assert back.dtype == np.float32
    assert float(np.abs(back - x).max()) <= scale / 2 + 1e-6


def test_quantize_zeros_and_clipping():
    q, scale = ex.quantize_symmetric(np.zeros(4, dtype=np.float32))
    assert scale == 1.0 and not q.any()
    q, _ = ex.quantize_symmetric(np.array([-2.0, 2.0, 1.0], dtype=np.float32))
    assert q.tolist() == [-127, 127, 64]  # 1.0 / (2/127) = 63.5 -> rounds half to even = 64


def test_latency_stats():
    stats = ex.latency_stats([float(i) for i in range(1, 101)])
    assert stats["p50"] == pytest.approx(50.5)
    assert stats["p95"] == pytest.approx(95.05)
    assert stats["p99"] == pytest.approx(99.01)
    assert stats["max"] == 100.0
    with pytest.raises(ValueError):
        ex.latency_stats([])


def test_within_budget_uses_percentile_not_mean():
    samples = [1.0] * 99 + [50.0]  # mean 1.49 but one slow frame
    assert ex.within_budget(samples, budget_ms=5.0, percentile=99.0)
    assert not ex.within_budget(samples, budget_ms=5.0, percentile=100.0)
    assert not ex.within_budget([6.0] * 10, budget_ms=5.0)
    with pytest.raises(ValueError):
        ex.within_budget([], 5.0)
