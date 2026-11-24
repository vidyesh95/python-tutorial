# Plotting with matplotlib
"""
matplotlib draws a `Figure` (the canvas) containing one or more `Axes` (the actual plots).
Prefer the explicit object API (`fig, ax = plt.subplots()`; `ax.plot(...)`) over the implicit
`plt.plot(...)` state machine: it scales to multiple subplots and is easier to test.

Core ideas:
- Plot kinds: `ax.plot` (lines), `ax.scatter` (points), `ax.hist` (distribution), `ax.bar`.
- Decorate: `set_title`, `set_xlabel`, `set_ylabel`, `legend()` (needs `label=` on each artist).
- Grids of plots: `plt.subplots(nrows, ncols, figsize=...)` returns an array of Axes;
  `layout="constrained"` avoids overlapping labels.
- Save: `fig.savefig(path, dpi=150)`; close with `plt.close(fig)` to free memory.
- Headless use (servers, CI, these lessons): select the `Agg` backend BEFORE importing pyplot
  so no window ever opens. pandas can plot too: `df.plot(ax=ax)`.

Run: uv run python -m t06_applied_ml_llm.m_03_matplotlib
"""

import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no GUI; must come before `import matplotlib.pyplot`
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

rng = np.random.default_rng(0)


# Example: line plot with several series and a legend
def line_figure() -> Figure:
    x = np.linspace(0, 2 * np.pi, 100)
    fig, ax = plt.subplots(figsize=(5, 3), layout="constrained")
    ax.plot(x, np.sin(x), label="sin")
    ax.plot(x, np.cos(x), label="cos", linestyle="--")
    ax.set(title="Waves", xlabel="radians", ylabel="value")  # set() takes many properties at once
    ax.legend()
    return fig


# Example: scatter + histogram in a 1x2 grid (typical "explore a dataset" view)
def scatter_hist_figure() -> Figure:
    x = rng.normal(size=300)
    y = 2 * x + rng.normal(scale=0.5, size=300)
    fig, (ax_scatter, ax_hist) = plt.subplots(1, 2, figsize=(8, 3), layout="constrained")
    ax_scatter.scatter(x, y, s=8, alpha=0.6)
    ax_scatter.set(title="x vs y", xlabel="x", ylabel="y")
    ax_hist.hist(y, bins=20, color="tab:orange")
    ax_hist.set(title="distribution of y", xlabel="y", ylabel="count")
    return fig


# Example: training-curve style plot with an annotation of the best point
def loss_curve_figure() -> Figure:
    epochs = np.arange(1, 21)
    val = 1 / epochs + 0.02 * (epochs - 10) ** 2 / 20  # dips, then rises (overfitting)
    fig, ax = plt.subplots(figsize=(5, 3), layout="constrained")
    ax.plot(epochs, val, marker="o", markersize=3)
    best = int(np.argmin(val))
    ax.annotate(
        f"best epoch {epochs[best]}",
        xy=(epochs[best], val[best]),
        xytext=(epochs[best] + 3, val[best] + 0.2),
        arrowprops={"arrowstyle": "->"},
    )
    ax.set(title="validation loss", xlabel="epoch", ylabel="loss")
    return fig


# Example: saving to a temp directory and releasing memory
def save(fig: Figure, directory: Path, name: str) -> Path:
    path = directory / name
    fig.savefig(path, dpi=100)
    plt.close(fig)  # forgetting this leaks figures: matplotlib warns after 20 open ones
    return path


"""
Common mistakes:
- Calling `plt.show()` in scripts/servers/tests: it blocks or fails when there is no display.
  Use Agg + `savefig`.
- Mixing the implicit `plt.plot` API with explicit Axes, then drawing on the wrong subplot.
- Not closing figures in loops (memory leak) or reusing the global current figure by accident.
- Forgetting labels/units/legend: a plot nobody can read is not a result.
- Using `plt` from multiple threads: pyplot is not thread-safe; build `Figure()` objects directly.

Production notes:
- On servers render with `Figure()` + `FigureCanvasAgg` (no pyplot global state) or return
  PNG bytes via `fig.savefig(io.BytesIO(), format="png")`.
- Save vector formats (`.svg`, `.pdf`) for docs, PNG at 100-200 dpi for dashboards.
- Pin the `matplotlib` version for golden-image tests; rendering differs slightly across versions.
- For interactive dashboards use Plotly/Altair/Streamlit (t08) instead of fighting matplotlib.
"""

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        for name, maker in [
            ("line.png", line_figure),
            ("scatter_hist.png", scatter_hist_figure),
            ("loss.png", loss_curve_figure),
        ]:
            out = save(maker(), Path(tmp), name)
            print(out.name, out.stat().st_size > 0)
