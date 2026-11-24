import pytest

pytest.importorskip("matplotlib")
import matplotlib

matplotlib.use("Agg")  # headless: never open a window
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from _loader import load  # noqa: E402

ex = load("t06_applied_ml_llm", "ex_03_matplotlib")


@pytest.fixture(autouse=True)
def _close_all():
    yield
    plt.close("all")


def test_line_figure_has_labeled_lines_legend_and_axis_labels():
    x = [0, 1, 2, 3]
    fig = ex.make_line_figure(x, {"a": [1, 2, 3, 4], "b": [4, 3, 2, 1]})
    assert len(fig.axes) == 1
    ax = fig.axes[0]
    assert len(ax.lines) == 2
    assert [line.get_label() for line in ax.lines] == ["a", "b"]
    assert ax.get_legend() is not None
    assert (ax.get_xlabel(), ax.get_ylabel()) == ("x", "y")
    np.testing.assert_allclose(ax.lines[1].get_ydata(), [4, 3, 2, 1])


def test_scatter_hist_figure_layout():
    rng = np.random.default_rng(0)
    x, y = rng.normal(size=40), rng.normal(size=40)
    fig = ex.make_scatter_hist_figure(x, y)
    assert len(fig.axes) == 2
    scatter_ax, hist_ax = fig.axes
    assert len(scatter_ax.collections) == 1
    np.testing.assert_allclose(scatter_ax.collections[0].get_offsets()[:, 1], y)
    assert len(hist_ax.patches) == 10
    assert sum(p.get_height() for p in hist_ax.patches) == 40


def test_annotate_max_adds_single_annotation_at_peak():
    fig, ax = plt.subplots()
    x, y = [0, 1, 2, 3], [1.0, 5.5, 2.0, 3.0]
    ax.plot(x, y)
    ex.annotate_max(ax, x, y)
    assert len(ax.texts) == 1
    assert ax.texts[0].get_text() == "max=5.5 at x=1"
    assert tuple(ax.texts[0].xy) == (1, 5.5)


def test_save_figure_writes_png_creates_dirs_and_closes(tmp_path):
    fig, ax = plt.subplots()
    ax.plot([1, 2], [3, 4])
    number = fig.number
    target = tmp_path / "nested" / "dir" / "plot.png"
    result = ex.save_figure(fig, target)
    assert result == target
    assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert not plt.fignum_exists(number)
