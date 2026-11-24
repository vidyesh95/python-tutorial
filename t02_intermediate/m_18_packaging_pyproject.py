# Packaging with pyproject.toml
"""
A Python project is described by pyproject.toml (PEP 517/518/621). It tells tools:
    [project]         name, version, dependencies, Python requirement, scripts
    [build-system]    which backend builds the package (hatchling, setuptools, uv_build...)
    [tool.*]          configuration for tools (pytest, ruff, mypy, uv)
Recommended "src layout":
    my_project/
      pyproject.toml
      README.md
      src/my_project/__init__.py      <- importable code lives in src/
      src/my_project/cli.py
      tests/test_cli.py
Why src/? Tests run against the INSTALLED package, so packaging mistakes show up early.
Entry points ([project.scripts]) create commands like `mytool` that call a function.
Versioning: follow semantic versioning MAJOR.MINOR.PATCH (PEP 440 compatible).
Workflow with uv:
    uv init --package my_project    create a project in src layout
    uv add httpx                    add a dependency (edits pyproject.toml + uv.lock)
    uv add --dev pytest             add to the dev dependency group
    uv sync                         create/update .venv from the lock file
    uv run mytool                   run the entry point
    uv build                        create sdist + wheel in dist/
    uv publish                      upload to PyPI
"""

import tomllib

# Example: a complete pyproject.toml (printed as a string; no files are written)
PYPROJECT = """\
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "log-analyzer"
version = "0.3.1"
description = "Summarize application log files."
readme = "README.md"
requires-python = ">=3.15"
license = { text = "MIT" }
authors = [{ name = "Ada Lovelace", email = "ada@example.com" }]
dependencies = [
    "rich>=13.0",
]

[project.optional-dependencies]
yaml = ["pyyaml>=6.0"]          # pip install log-analyzer[yaml]

[dependency-groups]
dev = ["pytest>=8.3", "ruff>=0.8"]

[project.scripts]
log-analyzer = "log_analyzer.cli:main"   # command -> module:function

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
"""
print(PYPROJECT)

# Example: parse it with the stdlib tomllib to see it is plain data
data = tomllib.loads(PYPROJECT)
project = data["project"]
print(project["name"], project["version"], project["requires-python"])
print("entry points:", project["scripts"])
print("build backend:", data["build-system"]["build-backend"])
print("sections:", sorted(data))

# Example: what the entry point means
ENTRY_MODULE = """\
# src/log_analyzer/cli.py
def main() -> int:
    print("analyzing...")
    return 0       # becomes the process exit code

if __name__ == "__main__":      # also lets you run: python -m log_analyzer.cli
    raise SystemExit(main())
"""
print(ENTRY_MODULE)


# Example: how version strings compare
def parse_version(text: str) -> tuple[int, int, int]:
    major, minor, patch = (int(part) for part in text.split("."))
    return major, minor, patch


print(parse_version("0.3.1") < parse_version("0.10.0"))  # True; plain string compare says False
print("0.3.1" < "0.10.0")

# Semantic versioning cheat sheet:
#   PATCH: bug fixes only         0.3.1 -> 0.3.2
#   MINOR: backwards-compatible features   0.3.2 -> 0.4.0
#   MAJOR: breaking changes       0.4.0 -> 1.0.0

# Example: what `uv build` produces
print("dist/log_analyzer-0.3.1.tar.gz        (sdist: source distribution)")
print("dist/log_analyzer-0.3.1-py3-none-any.whl  (wheel: what pip installs)")

# Example: dependency specifiers
for spec in ("httpx>=0.28", "pydantic>=2,<3", "numpy~=2.1", "requests==2.32.3"):
    print(f"  {spec:20} <- lower bound / range / compatible release / exact pin")

"""
Common mistakes
- Putting code at the repo root and importing it by accident-of-cwd; use src layout
  so what you test is what you ship.
- Forgetting __init__.py (or package discovery config), so modules are missing from the wheel.
- Pinning everything with == in a library; this causes dependency conflicts for users.
  (Applications should commit a lock file; libraries should use ranges.)
- Not bumping the version (PyPI refuses to re-upload the same version).
- Editing the entry-point path without updating it: "pkg.cli:main" must point to a real function.
- Committing the .venv or dist/ directory; add them to .gitignore.
"""

"""
Where this shows up in backend/ML work
- Services are built into Docker images from pyproject.toml + uv.lock for reproducible deploys.
- Internal shared libraries (clients, utils) are published to a private index.
- CLI tools and ML pipelines expose entry points (`train`, `serve`).
- Dependency groups keep heavy extras (torch, boto3) out of images that don't need them.
"""
