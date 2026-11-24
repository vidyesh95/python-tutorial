"""Test helper: load an exercise module, or its reference solution.

Tests call ``load("t01_fundamentals", "ex_04_strings")``.
By default this imports ``t01_fundamentals.exercises.ex_04_strings`` (your work).
Run ``SOLUTIONS=1 uv run pytest`` to test the reference solutions instead.
"""

import importlib
import os
from types import ModuleType


def load(track: str, name: str) -> ModuleType:
    folder = "solutions" if os.getenv("SOLUTIONS") == "1" else "exercises"
    return importlib.import_module(f"{track}.{folder}.{name}")
