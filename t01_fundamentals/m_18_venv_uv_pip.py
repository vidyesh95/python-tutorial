# Virtual Environments, pip and uv
"""
Why: different projects need different package versions. A virtual environment (venv) is an isolated folder
(.venv) holding its own Python interpreter link and its own installed packages, so projects do not clash and
you never touch the system Python.

THE CLASSIC WAY (venv + pip)
    python -m venv .venv                 create the environment
    source .venv/bin/activate            activate it (Windows: .venv\\Scripts\\activate)
    pip install requests                 install a package
    pip install -r requirements.txt      install a list of packages
    pip freeze > requirements.txt        save exact versions
    pip list / pip show requests         inspect
    deactivate                           leave the environment

THE MODERN WAY (uv: one fast tool for Python versions, venvs, dependencies and running code)
    uv init my-project                   scaffold a project with pyproject.toml
    uv python install 3.13               install/manage Python versions
    uv add requests                      add a dependency (updates pyproject.toml + uv.lock)
    uv add --dev pytest ruff             add a dev-only dependency
    uv remove requests                   remove a dependency
    uv sync                              create/update .venv to match pyproject.toml + uv.lock
    uv run python script.py              run inside the project environment (no manual activation)
    uv run pytest                        run any tool from the environment
    uv pip install <pkg>                 pip-compatible interface (rarely needed)
    uv lock --upgrade                    upgrade locked versions

pyproject.toml is the project's single configuration file. A minimal one:

    [project]
    name = "my-project"
    version = "0.1.0"
    requires-python = ">=3.13"
    dependencies = ["requests>=2.32"]

    [dependency-groups]
    dev = ["pytest>=8.3", "ruff>=0.8"]

uv.lock records the exact resolved versions so every machine gets identical installs - commit it.
Do NOT commit .venv/ (add it to .gitignore); anyone can rebuild it with `uv sync`.
"""

import sys
import sysconfig
from importlib import metadata
from pathlib import Path

# Which Python am I running?
# Example
print(sys.version)
print(sys.version_info[:3] >= (3, 13, 0))
print("executable path set:", bool(sys.executable))

# Am I inside a virtual environment?
"""
Inside a venv, sys.prefix points at the venv folder while sys.base_prefix points at the original Python.
When they differ, you are in a virtual environment.
"""
# Example
in_venv = sys.prefix != sys.base_prefix
print("inside a virtual environment:", in_venv)
print("prefix ends with .venv:", Path(sys.prefix).name == ".venv")
print(
    "site-packages is a directory:", Path(sysconfig.get_paths()["purelib"]).name == "site-packages"
)

# Inspecting installed packages
# Example
installed = sorted(dist.metadata["Name"] for dist in metadata.distributions())
print(len(installed) >= 0, "packages visible")
try:
    print("pytest version:", metadata.version("pytest"))
except metadata.PackageNotFoundError:
    print("pytest is not installed in this environment")

# Where do imports come from?
# Example
print(any("site-packages" in p for p in sys.path) or "no site-packages on sys.path")

# Environment variables that influence tools
# Example
"""
VIRTUAL_ENV is set by `source .venv/bin/activate`. `uv run` does not need activation.
UV_PROJECT_ENVIRONMENT can point uv to a different environment folder.
"""

# Suggested workflow for this repository
"""
    uv sync                                          install dev dependencies
    uv run python -m t01_fundamentals.m_18_venv_uv_pip   run a lesson
    uv run pytest t01_fundamentals -k venv           run exercises for a lesson
    uv add --group backend httpx                     add to an optional dependency group
"""

# Common mistakes
"""
1. Installing packages globally with pip instead of inside a venv.
2. Forgetting to activate the venv (with uv, use `uv run` instead and skip activation).
3. Committing .venv/ to git; commit pyproject.toml and uv.lock instead.
4. Editing uv.lock by hand; use `uv add` / `uv remove` / `uv lock`.
5. Mixing tools: if the project uses uv, do not also `pip install` into its .venv - use `uv add`.
6. Running `python` and getting a different interpreter than expected; check `sys.executable`.
"""
