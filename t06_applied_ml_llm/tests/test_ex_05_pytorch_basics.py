import pytest

pytest.importorskip("torch")
import torch

from _loader import load

ex = load("t06_applied_ml_llm", "ex_05_pytorch_basics")


@pytest.mark.parametrize(
    ("cuda", "mps", "expected"),
    [(True, True, "cuda"), (True, False, "cuda"), (False, True, "mps"), (False, False, "cpu")],
)
def test_pick_device(cuda, mps, expected):
    assert ex.pick_device(cuda, mps) == expected


def test_gradient_of_mse_matches_closed_form():
    xs, ys, w = [1.0, 2.0, 3.0], [2.0, 4.0, 7.0], 1.5
    expected = sum(2 * (w * x - y) * x for x, y in zip(xs, ys, strict=True)) / len(xs)
    assert ex.gradient_of_mse(w, xs, ys) == pytest.approx(expected, rel=1e-5)
    assert isinstance(ex.gradient_of_mse(w, xs, ys), float)


def test_linear_regressor_is_module_with_linear_layer():
    model = ex.LinearRegressor()
    assert isinstance(model, torch.nn.Module)
    assert isinstance(model.linear, torch.nn.Linear)
    assert (model.linear.in_features, model.linear.out_features) == (1, 1)
    assert model(torch.zeros(5, 1)).shape == (5, 1)


def _data():
    torch.manual_seed(0)
    x = torch.linspace(-1, 1, 64).unsqueeze(1)
    y = 3 * x + 1 + 0.01 * torch.randn_like(x)
    return x, y


def test_train_reduces_loss_and_learns_parameters():
    torch.manual_seed(1)
    model = ex.LinearRegressor()
    x, y = _data()
    history = ex.train(model, x, y, epochs=300, lr=0.1)
    assert len(history) == 300
    assert all(isinstance(v, float) for v in history)
    assert history[-1] < history[0] * 0.01
    assert model.linear.weight.item() == pytest.approx(3.0, abs=0.1)
    assert model.linear.bias.item() == pytest.approx(1.0, abs=0.1)


def test_save_and_load_state_roundtrip(tmp_path):
    torch.manual_seed(2)
    model = ex.LinearRegressor()
    x, y = _data()
    ex.train(model, x, y, epochs=20)
    path = tmp_path / "model.pt"
    ex.save_state(model, path)
    loaded = ex.load_state(path)
    assert loaded is not model
    assert isinstance(loaded, ex.LinearRegressor)
    assert torch.allclose(loaded(x), model(x))
    assert set(torch.load(path, weights_only=True)) == {"linear.weight", "linear.bias"}
