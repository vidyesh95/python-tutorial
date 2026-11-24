"""Reference solution for Exercise 05: PyTorch basics."""

from collections.abc import Sequence
from pathlib import Path

import torch
from torch import nn


def pick_device(cuda_available: bool, mps_available: bool) -> str:
    if cuda_available:
        return "cuda"
    if mps_available:
        return "mps"
    return "cpu"


def gradient_of_mse(w: float, xs: Sequence[float], ys: Sequence[float]) -> float:
    weight = torch.tensor(float(w), requires_grad=True)
    x = torch.tensor(list(xs), dtype=torch.float32)
    y = torch.tensor(list(ys), dtype=torch.float32)
    loss = ((weight * x - y) ** 2).mean()
    loss.backward()
    return float(weight.grad.item())


class LinearRegressor(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.linear = nn.Linear(1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(x)


def train(
    model: LinearRegressor, x: torch.Tensor, y: torch.Tensor, epochs: int = 100, lr: float = 0.1
) -> list[float]:
    optimizer = torch.optim.SGD(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()
    history: list[float] = []
    for _ in range(epochs):
        optimizer.zero_grad()
        loss = loss_fn(model(x), y)
        loss.backward()
        optimizer.step()
        history.append(loss.item())
    return history


def save_state(model: LinearRegressor, path: Path) -> None:
    torch.save(model.state_dict(), path)


def load_state(path: Path) -> LinearRegressor:
    model = LinearRegressor()
    model.load_state_dict(torch.load(path, weights_only=True, map_location="cpu"))
    return model
