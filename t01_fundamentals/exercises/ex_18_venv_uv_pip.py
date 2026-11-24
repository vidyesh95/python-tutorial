"""Exercise 18 - Virtual environments, pip and uv.

Tasks:
1. python_version_string: "major.minor.micro" of the running interpreter.
2. in_virtualenv: are we running inside a virtual environment?
3. parse_requirement: split a requirement line into (name, version specifier).
4. read_dependencies: read the dependency list from pyproject.toml text.
5. pip_to_uv: translate common pip/python commands to their uv equivalents.
"""


def python_version_string() -> str:
    """Return the running Python version like ``"3.15.2"``.

    Examples:
        python_version_string() -> "3.15.2"
    """
    raise NotImplementedError


def in_virtualenv() -> bool:
    """True when ``sys.prefix`` differs from ``sys.base_prefix``.

    Examples:
        in_virtualenv() -> True under `uv run`, usually False for the system Python
    """
    raise NotImplementedError


def parse_requirement(line: str) -> tuple[str, str]:
    """Split ``"name<operator>version"`` into ``(name, specifier)``; the specifier is "" if absent.
    Whitespace is ignored. Supported operators: ``==, >=, <=, ~=, !=, >, <``.

    Examples:
        parse_requirement("requests>=2.32") -> ("requests", ">=2.32")
        parse_requirement("pytest == 8.3.1") -> ("pytest", "==8.3.1")
        parse_requirement("ruff") -> ("ruff", "")
    """
    raise NotImplementedError


def read_dependencies(pyproject_text: str) -> list[str]:
    """Return ``[project].dependencies`` from pyproject.toml text (use ``tomllib``); ``[]`` if absent.

    Examples:
        read_dependencies('[project]\\nname="x"\\ndependencies=["requests>=2"]') -> ["requests>=2"]
        read_dependencies('[project]\\nname="x"') -> []
    """
    raise NotImplementedError


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
    raise NotImplementedError
