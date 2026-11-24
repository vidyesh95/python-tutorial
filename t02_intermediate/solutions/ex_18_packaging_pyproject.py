"""Exercise 18: Packaging and pyproject.toml.

Tasks
1. parse_version: strict MAJOR.MINOR.PATCH parsing.
2. bump_version: semantic version bumps.
3. read_project_metadata: pull fields out of pyproject text with tomllib.
4. parse_entry_point: split 'package.module:function'.
5. resolve_entry_point: import and return the callable.

Run: uv run pytest t02_intermediate -k packaging
"""

import importlib
import re
import tomllib
from collections.abc import Callable
from typing import Any, Literal

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")
_ENTRY_RE = re.compile(r"^([A-Za-z_][\w.]*):([A-Za-z_]\w*)$")


def parse_version(text: str) -> tuple[int, int, int]:
    """Parse 'MAJOR.MINOR.PATCH' into a tuple of ints. Raise ValueError otherwise.

    >>> parse_version("1.12.0")
    (1, 12, 0)
    """
    m = _VERSION_RE.fullmatch(text.strip())
    if not m:
        raise ValueError(f"invalid version: {text!r}")
    major, minor, patch = (int(g) for g in m.groups())
    return major, minor, patch


def bump_version(version: str, part: Literal["major", "minor", "patch"]) -> str:
    """Bump one part; lower parts reset to 0. Raise ValueError for an unknown part.

    >>> bump_version("1.2.3", "minor")
    '1.3.0'
    >>> bump_version("1.2.3", "major")
    '2.0.0'
    """
    major, minor, patch = parse_version(version)
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"unknown part: {part!r}")


def read_project_metadata(toml_text: str) -> dict[str, Any]:
    """From pyproject text return {'name', 'version', 'dependencies', 'scripts'}.

    Missing dependencies -> [], missing scripts -> {}. Raise KeyError if the [project]
    table or its name/version is missing.
    """
    project = tomllib.loads(toml_text)["project"]
    return {
        "name": project["name"],
        "version": project["version"],
        "dependencies": list(project.get("dependencies", [])),
        "scripts": dict(project.get("scripts", {})),
    }


def parse_entry_point(spec: str) -> tuple[str, str]:
    """Split 'package.module:function' into ('package.module', 'function').

    Raise ValueError if the spec is malformed.

    >>> parse_entry_point("log_analyzer.cli:main")
    ('log_analyzer.cli', 'main')
    """
    m = _ENTRY_RE.match(spec.strip())
    if not m:
        raise ValueError(f"invalid entry point: {spec!r}")
    return m.group(1), m.group(2)


def resolve_entry_point(spec: str) -> Callable[..., Any]:
    """Import the module and return the named attribute (use importlib).

    >>> resolve_entry_point("json:dumps")({"a": 1})
    '{"a": 1}'
    """
    module_name, attr = parse_entry_point(spec)
    return getattr(importlib.import_module(module_name), attr)
