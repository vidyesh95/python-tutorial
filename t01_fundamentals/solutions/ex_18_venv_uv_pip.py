"""Exercise 18 - Virtual environments, pip and uv.

Tasks:
1. python_version_string: "major.minor.micro" of the running interpreter.
2. in_virtualenv: are we running inside a virtual environment?
3. parse_requirement: split a requirement line into (name, version specifier).
4. read_dependencies: read the dependency list from pyproject.toml text.
5. pip_to_uv: translate common pip/python commands to their uv equivalents.
"""

import re
import sys
import tomllib


def python_version_string() -> str:
    """Return the running Python version like ``"3.15.2"``.

    Examples:
        python_version_string() -> "3.15.2"
    """
    v = sys.version_info
    return f"{v.major}.{v.minor}.{v.micro}"


def in_virtualenv() -> bool:
    """True when ``sys.prefix`` differs from ``sys.base_prefix``.

    Examples:
        in_virtualenv() -> True under `uv run`, usually False for the system Python
    """
    return sys.prefix != sys.base_prefix


def parse_requirement(line: str) -> tuple[str, str]:
    """Split ``"name<operator>version"`` into ``(name, specifier)``; the specifier is "" if absent.
    Whitespace is ignored. Supported operators: ``==, >=, <=, ~=, !=, >, <``.

    Examples:
        parse_requirement("requests>=2.32") -> ("requests", ">=2.32")
        parse_requirement("pytest == 8.3.1") -> ("pytest", "==8.3.1")
        parse_requirement("ruff") -> ("ruff", "")
    """
    cleaned = line.strip().replace(" ", "")
    match = re.match(r"^([A-Za-z0-9_.\-]+)(.*)$", cleaned)
    if match is None:
        raise ValueError(f"invalid requirement: {line!r}")
    return match.group(1), match.group(2)


def read_dependencies(pyproject_text: str) -> list[str]:
    """Return ``[project].dependencies`` from pyproject.toml text (use ``tomllib``); ``[]`` if absent.

    Examples:
        read_dependencies('[project]\\nname="x"\\ndependencies=["requests>=2"]') -> ["requests>=2"]
        read_dependencies('[project]\\nname="x"') -> []
    """
    data = tomllib.loads(pyproject_text)
    return list(data.get("project", {}).get("dependencies", []))


def pip_to_uv(command: str) -> str:
    """Translate a command to its uv equivalent:

    - ``pip install <pkg...>``       -> ``uv add <pkg...>``
    - ``pip uninstall <pkg...>``     -> ``uv remove <pkg...>``
    - ``pip install -r requirements.txt`` -> ``uv sync``
    - ``python -m venv .venv``       -> ``uv venv``
    - ``python <args>``              -> ``uv run python <args>``
    Anything else raises ValueError.

    Examples:
        pip_to_uv("pip install requests httpx") -> "uv add requests httpx"
        pip_to_uv("pip uninstall requests") -> "uv remove requests"
        pip_to_uv("pip install -r requirements.txt") -> "uv sync"
        pip_to_uv("python -m venv .venv") -> "uv venv"
        pip_to_uv("python app.py") -> "uv run python app.py"
    """
    parts = command.split()
    if parts[:2] == ["pip", "install"]:
        if parts[2:] == ["-r", "requirements.txt"]:
            return "uv sync"
        return " ".join(["uv", "add", *parts[2:]])
    if parts[:2] == ["pip", "uninstall"]:
        return " ".join(["uv", "remove", *parts[2:]])
    if parts[:3] == ["python", "-m", "venv"]:
        return "uv venv"
    if parts[:1] == ["python"]:
        return "uv run " + command.strip()
    raise ValueError(f"unsupported command: {command!r}")
