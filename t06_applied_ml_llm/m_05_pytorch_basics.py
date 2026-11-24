# PyTorch Basics
"""
PyTorch is a tensor library with automatic differentiation. If you know NumPy, a `Tensor` is an
ndarray that can live on a GPU and remember how it was computed so gradients are free.

Core ideas:
- TENSORS: `torch.tensor`, `torch.zeros`, `.shape`, `.dtype`, `.to(device)`. NumPy interop via
  `torch.from_numpy` / `.numpy()` (shares memory on CPU).
- AUTOGRAD: tensors with `requires_grad=True` record operations; `loss.backward()` fills
  `.grad` on every leaf. Gradients ACCUMULATE, so reset them each step.
- `nn.Module`: a class holding layers/parameters, with `forward()` defining the computation.
  `model.parameters()` feeds an optimizer.
- TRAINING LOOP (the same five lines for every model):
      optimizer.zero_grad(); pred = model(x); loss = loss_fn(pred, y)
      loss.backward(); optimizer.step()
- DEVICE: pick `cuda` (NVIDIA), `mps` (Apple Silicon) or `cpu`; model and data must be on the
  same device.
- SAVING: `torch.save(model.state_dict(), path)`, then rebuild the model and `load_state_dict`.
  Load with `weights_only=True` (safe against pickle code execution).

This lesson needs the optional torch group:  uv sync --group ml-torch
Run: uv run python -m t06_applied_ml_llm.m_05_pytorch_basics
"""

import sys
import tempfile
from pathlib import Path

try:
    import torch
    from torch import nn
except ImportError:  # learners without the ml-torch group get a friendly exit, not a traceback
    print("PyTorch is not installed. Install it with:  uv sync --group ml-torch")
    sys.exit(0)


def pick_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


# Example: tensors and autograd on a one-line function
def autograd_demo() -> None:
    a = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
    print(a.shape, a.dtype, (a @ a).tolist(), a.mean().item())
    w = torch.tensor(3.0, requires_grad=True)
    loss = (w * 2 - 10) ** 2  # d(loss)/dw = 2*(2w-10)*2 = -16 at w=3
    loss.backward()
    print("grad:", w.grad.item())  # -16.0
    with torch.no_grad():  # inference / manual updates: don't record the graph
        w -= 0.1 * w.grad
    print("after one manual step:", round(w.item(), 2))


# Example: a tiny model as an nn.Module
class LinearRegressor(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.linear = nn.Linear(1, 1)  # y = w*x + b, both learnable

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(x)


# Example: the training loop on synthetic data (y = 3x + 1 plus noise)
def train_demo(device: torch.device) -> LinearRegressor:
    torch.manual_seed(0)
    x = torch.linspace(-1, 1, 64).unsqueeze(1).to(device)  # shape (64, 1)
    y = 3 * x + 1 + 0.05 * torch.randn_like(x)
    model = LinearRegressor().to(device)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    loss_fn = nn.MSELoss()
    for epoch in range(200):
        optimizer.zero_grad()  # gradients accumulate; clear last step's
        loss = loss_fn(model(x), y)
        loss.backward()
        optimizer.step()
        if epoch % 50 == 0:
            print(f"epoch {epoch:3d} loss {loss.item():.4f}")
    w, b = model.linear.weight.item(), model.linear.bias.item()
    print(f"learned w={w:.2f} b={b:.2f} (true 3, 1)")
    return model


# Example: save and reload a state_dict
def save_demo(model: LinearRegressor) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "model.pt"
        torch.save(model.state_dict(), path)  # weights only; the class definition stays in code
        fresh = LinearRegressor()
        fresh.load_state_dict(torch.load(path, weights_only=True, map_location="cpu"))
        fresh.eval()  # eval mode matters for dropout/batchnorm; harmless here
        x = torch.tensor([[0.5]])
        print("reloaded prediction:", round(fresh(x.cpu()).item(), 3))


"""
Common mistakes:
- Forgetting `optimizer.zero_grad()`: gradients silently accumulate across steps.
- Model on GPU, data on CPU (or vice versa): "Expected all tensors to be on the same device".
- Calling `.item()`/`.numpy()` inside the hot loop on GPU tensors (forces a sync); log every N steps.
- Evaluating without `model.eval()` and `torch.no_grad()`: wastes memory and changes dropout/BN.
- Shape bugs: (N,) vs (N, 1) in regression silently broadcasts into a wrong loss. Print shapes.
- `torch.load` on untrusted files without `weights_only=True` can execute code.

Production notes:
- Seed (`torch.manual_seed`) for reproducibility; GPU kernels may still be nondeterministic.
- Use `DataLoader` with batches (and `num_workers`) instead of full-batch tensors for real data.
- Mixed precision (`torch.autocast`) and `torch.compile` are the first speed-ups to try.
- Save checkpoints with optimizer state to resume training; export for serving (ONNX/TorchScript)
  or load the state_dict into the same class in the service.
- GPU memory, not compute, is usually the limit: watch batch size and use `torch.no_grad()`.
"""

if __name__ == "__main__":
    dev = pick_device()
    print("device:", dev)
    autograd_demo()
    trained = train_demo(dev)
    save_demo(trained.cpu())
