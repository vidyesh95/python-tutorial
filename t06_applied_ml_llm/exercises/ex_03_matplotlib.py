"""Exercise 03: matplotlib.

The Agg backend is selected for you so no window ever opens. Use the object API
(`fig, ax = plt.subplots()`), not `plt.show()`.

Tasks
1. make_line_figure(x, series): ONE Axes with one line per entry of `series` (label -> y values),
   each line labeled, a legend, x label "x" and y label "y". Return the Figure.
2. make_scatter_hist_figure(x, y): a Figure with TWO Axes side by side: axes[0] is a scatter
   of (x, y); axes[1] is a 10-bin histogram of y. Return the Figure.
3. annotate_max(ax, x, y): add ONE annotation on `ax` located at the maximum y point with the
   text f"max={y_max:g} at x={x_at_max:g}".
4. save_figure(fig, path): create missing parent folders, save the figure to `path`, CLOSE the
   figure (free memory), and return the path as a `Path`.

Run: uv run pytest t06_applied_ml_llm -k ex_03
"""

from collections.abc import Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402, F401
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402


def make_line_figure(x: Sequence[float], series: dict[str, Sequence[float]]) -> Figure:
    raise NotImplementedError


def make_scatter_hist_figure(x: Sequence[float], y: Sequence[float]) -> Figure:
    raise NotImplementedError


def annotate_max(ax: Axes, x: Sequence[float], y: Sequence[float]) -> None:
    raise NotImplementedError


def save_figure(fig: Figure, path: str | Path) -> Path:
    raise NotImplementedError
