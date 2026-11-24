"""Exercise 18: Packaging and pyproject.toml.

Tasks
1. parse_version: strict MAJOR.MINOR.PATCH parsing.
2. bump_version: semantic version bumps.
3. read_project_metadata: pull fields out of pyproject text with tomllib.
4. parse_entry_point: split 'package.module:function'.
5. resolve_entry_point: import and return the callable.

Run: uv run pytest t02_intermediate -k packaging
"""

import re
from collections.abc import Callable
from typing import Any, Literal

_VERSION_RE = re.compile("(\\d+)\\.(\\d+)\\.(\\d+)")
_ENTRY_RE = re.compile("^([A-Za-z_][\\w.]*):([A-Za-z_]\\w*)$")


def parse_version(text: str) -> tuple[int, int, int]:
    """Parse 'MAJOR.MINOR.PATCH' into a tuple of ints. Raise ValueError otherwise.

    >>> parse_version("1.12.0")
    (1, 12, 0)
    """
    raise NotImplementedError


def bump_version(version: str, part: Literal["major", "minor", "patch"]) -> str:
    """Bump one part; lower parts reset to 0. Raise ValueError for an unknown part.

    >>> bump_version("1.2.3", "minor")
    '1.3.0'
    >>> bump_version("1.2.3", "major")
    '2.0.0'
    """
    raise NotImplementedError


def read_project_metadata(toml_text: str) -> dict[str, Any]:
    """From pyproject text return {'name', 'version', 'dependencies', 'scripts'}.

    Missing dependencies -> [], missing scripts -> {}. Raise KeyError if the [project]
    table or its name/version is missing.
    """
    raise NotImplementedError


def parse_entry_point(spec: str) -> tuple[str, str]:
    """Split 'package.module:function' into ('package.module', 'function').

    Raise ValueError if the spec is malformed.

    >>> parse_entry_point("log_analyzer.cli:main")
    ('log_analyzer.cli', 'main')
    """
    raise NotImplementedError


def resolve_entry_point(spec: str) -> Callable[..., Any]:
    """Import the module and return the named attribute (use importlib).

    >>> resolve_entry_point("json:dumps")({"a": 1})
    '{"a": 1}'
    """
    raise NotImplementedError
