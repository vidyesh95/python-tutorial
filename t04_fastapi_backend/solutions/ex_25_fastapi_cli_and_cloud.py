"""Exercise 25: FastAPI CLI. Build the pieces the `fastapi` command uses, offline.

Tasks
1. cli_defaults: the default host/port/reload of `fastapi dev` and `fastapi run`.
2. build_argv: build the argv list for `fastapi dev|run`.
3. find_default_path: auto-discovery when no path is given.
4. read_entrypoint: read `[tool.fastapi] entrypoint` from pyproject.toml text (tomllib).
5. split_entrypoint + resolve_entrypoint: turn "module:attr" into the app object (importlib).
6. discovery_source: which of the discovery rules the CLI ends up using.
7. create_app + app_from_env: an app factory driven by FASTAPI_ENV.

Nothing here starts a server or talks to FastAPI Cloud.
Run: uv run pytest t04_fastapi_backend -k fastapi_cli
"""

import importlib
import tomllib
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
    if mode == "dev":
        return {"host": "127.0.0.1", "port": 8000, "reload": True}
    if mode == "run":
        return {"host": "0.0.0.0", "port": 8000, "reload": False}
    raise ValueError(f"mode must be 'dev' or 'run', not {mode!r}")


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
    if mode not in ("dev", "run"):
        raise ValueError(f"mode must be 'dev' or 'run', not {mode!r}")
    if target and entrypoint:
        raise ValueError("--entrypoint cannot be combined with a path")
    if workers is not None and mode == "dev":
        raise ValueError("--workers is only available on `fastapi run`")
    argv = ["fastapi", mode]
    if target:
        argv.append(target)
    if entrypoint is not None:
        argv += ["--entrypoint", entrypoint]
    for flag, value in (("--host", host), ("--port", port), ("--workers", workers)):
        if value is not None:
            argv += [flag, str(value)]
    if proxy_headers is not None:
        argv.append("--proxy-headers" if proxy_headers else "--no-proxy-headers")
    if forwarded_allow_ips is not None:
        argv += ["--forwarded-allow-ips", forwarded_allow_ips]
    return argv


def find_default_path(existing_files: Iterable[str]) -> str | None:
    """Return the first of DEFAULT_PATHS that is in `existing_files` (DEFAULT_PATHS order wins,
    not the order of the input), or None if there is none."""
    existing = set(existing_files)
    return next((path for path in DEFAULT_PATHS if path in existing), None)


def read_entrypoint(pyproject_text: str) -> str | None:
    """Parse pyproject.toml text with tomllib and return `[tool.fastapi] entrypoint`.

    None if the `tool`, `fastapi` table or `entrypoint` key is missing. If it is present but not
    a string (e.g. `entrypoint = 3`), raise TypeError. Invalid TOML raises tomllib's error.
    """
    value = tomllib.loads(pyproject_text).get("tool", {}).get("fastapi", {}).get("entrypoint")
    if value is not None and not isinstance(value, str):
        raise TypeError(f"entrypoint must be a string, not {type(value).__name__}")
    return value


def split_entrypoint(entrypoint: str) -> tuple[str, str]:
    """ "pkg.mod:app" -> ("pkg.mod", "app"). ValueError unless there is a non-empty module,
    exactly one colon and a non-empty attribute name."""
    module_name, sep, attr = entrypoint.partition(":")
    if not sep or not module_name or not attr or ":" in attr:
        raise ValueError("Import string must be in the format module.submodule:app_name")
    return module_name, attr


def resolve_entrypoint(entrypoint: str) -> FastAPI:
    """Import the module (importlib.import_module) and return the attribute.

    - Bad format: ValueError (use split_entrypoint).
    - Missing module: let ModuleNotFoundError propagate.
    - Missing attribute: AttributeError.
    - Attribute that is not a FastAPI instance (e.g. a factory function): TypeError.
    """
    module_name, attr = split_entrypoint(entrypoint)
    module = importlib.import_module(module_name)
    obj = getattr(module, attr)
    if not isinstance(obj, FastAPI):
        raise TypeError(f"{entrypoint} is not a FastAPI instance")
    return obj


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
    if entrypoint and (path or app):
        raise ValueError("Cannot use --entrypoint together with path or --app arguments")
    if path or app:
        return "path-argument"
    if entrypoint:
        return "entrypoint-option"
    if pyproject_entrypoint:
        return "entrypoint-pyproject"
    return "auto-discovery"


def create_app(env: str = "development") -> FastAPI:
    """App factory. Every call returns a NEW FastAPI app with:
    - GET /healthz -> {"status": "ok"}
    - GET /info    -> {"env": env}
    - when env == "production": no docs at all (docs_url, redoc_url and openapi_url are None);
      otherwise the usual /docs, /redoc and /openapi.json.
    """
    production = env == "production"
    app = FastAPI(
        title="CLI demo",
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/info")
    def info() -> dict[str, str]:
        return {"env": env}

    return app


def app_from_env(environ: Mapping[str, str]) -> FastAPI:
    """create_app(environ["FASTAPI_ENV"]), defaulting to "development" when it is not set.
    (`fastapi dev` sets that variable before importing your app; `fastapi run` does not.)"""
    return create_app(environ.get("FASTAPI_ENV", "development"))
