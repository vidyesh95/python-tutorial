"""Reference solution for Exercise 03: matplotlib."""

from collections.abc import Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402


def make_line_figure(x: Sequence[float], series: dict[str, Sequence[float]]) -> Figure:
    fig, ax = plt.subplots()
    for label, values in series.items():
        ax.plot(x, values, label=label)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.legend()
    return fig


def make_scatter_hist_figure(x: Sequence[float], y: Sequence[float]) -> Figure:
    fig, (ax_scatter, ax_hist) = plt.subplots(1, 2)
    ax_scatter.scatter(x, y)
    ax_hist.hist(y, bins=10)
    return fig


def annotate_max(ax: Axes, x: Sequence[float], y: Sequence[float]) -> None:
    i = int(np.argmax(y))
    ax.annotate(f"max={y[i]:g} at x={x[i]:g}", xy=(x[i], y[i]))


def save_figure(fig: Figure, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    plt.close(fig)
    return out
