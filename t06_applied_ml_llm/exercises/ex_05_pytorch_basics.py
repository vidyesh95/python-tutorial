"""Exercise 05: PyTorch basics.

Needs the optional torch group: uv sync --group ml-torch  (tests skip without it).

Tasks
1. pick_device(cuda_available, mps_available): return "cuda" if CUDA is available, else "mps"
   if MPS is, else "cpu". (Pure logic so it is testable without a GPU.)
2. gradient_of_mse(w, xs, ys): using AUTOGRAD, return d/dw of mean((w * x - y) ** 2) at the
   given float `w`, as a Python float. Do not use the closed-form formula.
3. LinearRegressor: an nn.Module with one `nn.Linear(1, 1)` stored as `self.linear`; `forward`
   applies it to a (N, 1) tensor.
4. train(model, x, y, epochs=100, lr=0.1): plain SGD + MSELoss full-batch training loop.
   Return the list of per-epoch loss floats (the loss BEFORE each step's update is fine).
5. save_state / load_state: `save_state(model, path)` writes the state_dict;
   `load_state(path)` returns a NEW LinearRegressor with those weights loaded
   (use `weights_only=True`).

Run: uv run pytest t06_applied_ml_llm -k ex_05
"""

from collections.abc import Sequence
from pathlib import Path

import torch
from torch import nn


def pick_device(cuda_available: bool, mps_available: bool) -> str:
    raise NotImplementedError


def gradient_of_mse(w: float, xs: Sequence[float], ys: Sequence[float]) -> float:
    raise NotImplementedError


class LinearRegressor(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        raise NotImplementedError

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError


def train(
    model: LinearRegressor, x: torch.Tensor, y: torch.Tensor, epochs: int = 100, lr: float = 0.1
) -> list[float]:
    raise NotImplementedError


def save_state(model: LinearRegressor, path: Path) -> None:
    raise NotImplementedError


def load_state(path: Path) -> LinearRegressor:
    raise NotImplementedError
