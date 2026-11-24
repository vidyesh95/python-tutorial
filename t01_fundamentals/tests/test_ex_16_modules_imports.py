import math
import os
import sys

import pytest

from _loader import load

ex = load("t01_fundamentals", "ex_16_modules_imports")


def test_circle_area():
    assert ex.circle_area(1) == pytest.approx(math.pi)
    assert ex.circle_area(0) == 0.0
    assert ex.circle_area(2) == pytest.approx(4 * math.pi)
    with pytest.raises(ValueError):
        ex.circle_area(-1)


def test_shuffled():
    items = [1, 2, 3, 4, 5, 6]
    result = ex.shuffled(items, seed=1)
    assert sorted(result) == items
    assert items == [1, 2, 3, 4, 5, 6]  # input untouched
    assert ex.shuffled(items, 5) == ex.shuffled(items, 5)
    assert ex.shuffled([], 1) == []


def test_file_extension():
    assert ex.file_extension("report.CSV") == ".csv"
    assert ex.file_extension("archive.tar.gz") == ".gz"
    assert ex.file_extension("README") == ""
    assert ex.file_extension("/path/to/.bashrc") == ""


def test_get_env(monkeypatch):
    monkeypatch.setenv("T01_EXAMPLE_VAR", "hello")
    monkeypatch.delenv("T01_MISSING_VAR", raising=False)
    assert ex.get_env("T01_EXAMPLE_VAR") == "hello"
    assert ex.get_env("T01_MISSING_VAR", "fallback") == "fallback"
    assert ex.get_env("T01_MISSING_VAR") == ""
    assert ex.get_env("PATH") == os.environ["PATH"]


def test_python_at_least():
    assert ex.python_at_least(3) is True
    assert ex.python_at_least(sys.version_info.major, sys.version_info.minor) is True
    assert ex.python_at_least(sys.version_info.major, sys.version_info.minor + 1) is False
    assert ex.python_at_least(99) is False
