"""Exercise 25: FastAPI CLI. Build the pieces the `fastapi` command uses, offline.

Tasks
1. cli_defaults: the default host/port/reload of `fastapi dev` and `fastapi run`.
2. build_argv: build the argv list for `fastapi dev|run`.
3. find_default_path: auto-discovery when no path is given.
4. read_entrypoint: read `[tool.fastapi] entrypoint` from pyproject.toml text (tomllib).
5. split_entrypoint + resolve_entrypoint: turn "module:attr" into the app object (importlib).
6. discovery_source: which of the discovery rules the CLI ends up using.
7. create_app + app_from_env: an app factory driven by FASTAPI_ENV.

Import what you need (tomllib, importlib). Nothing here starts a server or talks to FastAPI Cloud.
Run: uv run pytest t04_fastapi_backend -k fastapi_cli
"""

from collections.abc import Iterable, Mapping
from typing import Any

from fastapi import FastAPI

DEFAULT_PATHS = (
    "main.py",
    "app.py",
    "api.py",
    "app/main.py",
    "app/app.py",
    "app/api.py",
)


def cli_defaults(mode: str) -> dict[str, Any]:
    """Return {"host": ..., "port": ..., "reload": ...} for mode "dev" or "run".

    dev: 127.0.0.1, 8000, reload on.  run: 0.0.0.0, 8000, reload off.
    Any other mode raises ValueError.
    """
    raise NotImplementedError


def build_argv(
    mode: str,
    target: str | None = None,
    *,
    entrypoint: str | None = None,
    host: str | None = None,
    port: int | None = None,
    workers: int | None = None,
    proxy_headers: bool | None = None,
    forwarded_allow_ips: str | None = None,
) -> list[str]:
    """Build the command line as a list, e.g. ["fastapi", "run", "main.py", "--port", "80"].

    Order: "fastapi", mode, target (if given), then the options below in this order:
    --entrypoint, --host, --port, --workers, then proxy headers, then --forwarded-allow-ips.
    - Options that are None are left out (the CLI's defaults apply). Numbers become strings.
    - proxy_headers: True -> "--proxy-headers", False -> "--no-proxy-headers", None -> nothing.
    - ValueError for: a mode other than "dev"/"run"; target together with entrypoint (the CLI
      refuses it); workers with mode "dev" (only `fastapi run` has --workers).
    """
    raise NotImplementedError


def find_default_path(existing_files: Iterable[str]) -> str | None:
    """Return the first of DEFAULT_PATHS that is in `existing_files` (DEFAULT_PATHS order wins,
    not the order of the input), or None if there is none."""
    raise NotImplementedError


def read_entrypoint(pyproject_text: str) -> str | None:
    """Parse pyproject.toml text with tomllib and return `[tool.fastapi] entrypoint`.

    None if the `tool`, `fastapi` table or `entrypoint` key is missing. If it is present but not
    a string (e.g. `entrypoint = 3`), raise TypeError. Invalid TOML raises tomllib's error.
    """
    raise NotImplementedError


def split_entrypoint(entrypoint: str) -> tuple[str, str]:
    """ "pkg.mod:app" -> ("pkg.mod", "app"). ValueError unless there is a non-empty module,
    exactly one colon and a non-empty attribute name."""
    raise NotImplementedError


def resolve_entrypoint(entrypoint: str) -> FastAPI:
    """Import the module (importlib.import_module) and return the attribute.

    - Bad format: ValueError (use split_entrypoint).
    - Missing module: let ModuleNotFoundError propagate.
    - Missing attribute: AttributeError.
    - Attribute that is not a FastAPI instance (e.g. a factory function): TypeError.
    """
    raise NotImplementedError


def discovery_source(
    *,
    path: str | None = None,
    app: str | None = None,
    entrypoint: str | None = None,
    pyproject_entrypoint: str | None = None,
) -> str:
    """Say where the CLI takes the app from. Return one of:
    "path-argument", "entrypoint-option", "entrypoint-pyproject", "auto-discovery".

    Priority: path or --app (path-argument) > --entrypoint option > pyproject entrypoint >
    auto-discovery. But `entrypoint` together with `path` or `app` is an error: ValueError.
    """
    raise NotImplementedError


def create_app(env: str = "development") -> FastAPI:
    """App factory. Every call returns a NEW FastAPI app with:
    - GET /healthz -> {"status": "ok"}
    - GET /info    -> {"env": env}
    - when env == "production": no docs at all (docs_url, redoc_url and openapi_url are None);
      otherwise the usual /docs, /redoc and /openapi.json.
    """
    raise NotImplementedError


def app_from_env(environ: Mapping[str, str]) -> FastAPI:
    """create_app(environ["FASTAPI_ENV"]), defaulting to "development" when it is not set.
    (`fastapi dev` sets that variable before importing your app; `fastapi run` does not.)"""
    raise NotImplementedError
