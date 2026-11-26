# FastAPI CLI and FastAPI Cloud
"""
`fastapi[standard]` installs the `fastapi` command (package `fastapi-cli`, which runs your app
with uvicorn) and the FastAPI Cloud client (`fastapi login`, `fastapi deploy`, ...).

Two ways to serve an app (the only differences are the defaults):

    fastapi dev   reload ON,   host 127.0.0.1 (this machine only), port 8000
    fastapi run   reload OFF,  host 0.0.0.0   (all interfaces),    port 8000, `--workers N`

- `dev` also sets FASTAPI_ENV=development (an existing value is kept, so FASTAPI_ENV=staging
  works). `run` leaves FASTAPI_ENV alone: set FASTAPI_ENV=production yourself if your code
  needs to know.
- `--proxy-headers/--no-proxy-headers` (X-Forwarded-For/-Proto/-Port) is ON by default in the
  installed fastapi-cli 0.0.34; older docs tell you to add `--proxy-headers`. Behind a load
  balancer also set `--forwarded-allow-ips` (comma separated IPs, or `*` to trust everything).
- `--root-path /api` tells the app it is served under a path prefix by a proxy.
- `--workers N` exists on `run` only. It is how you get N processes without a process manager.

How the CLI finds your app (highest priority first)
1. A path argument:   fastapi dev src/api.py   (+ `--app name` to pick the variable).
   It walks up while parent folders contain `__init__.py`, adds the top folder to sys.path and
   imports e.g. `pkg.sub.api`. Then it looks for a FastAPI object named `app`, then `api`, then
   the first FastAPI instance in the module.
2. `--entrypoint module:attr` (short `-e`). Cannot be combined with a path or `--app` (error).
   It overrides the pyproject setting below.
3. `[tool.fastapi] entrypoint = "module:attr"` in `pyproject.toml` of the CURRENT directory.
   (A path argument beats it, because the CLI only reads it when no path/--app is given.)
4. Auto-discovery: main.py, app.py, api.py, app/main.py, app/app.py, app/api.py (in that order).
Prefer option 3: it is written once, and other tools (the VS Code extension, FastAPI Cloud) read
it too. The entrypoint is imported from the current directory, so `backend.main:app` needs
`backend/` to be importable from where you run the command.

The app must be a FastAPI INSTANCE at module level. There is no `--factory` flag. For the
app-factory pattern, keep `create_app(...)` for tests and export `app = create_app()` for the CLI.

Run the demo app of this lesson (reads FASTAPI_ENV):
    uv run fastapi dev t04_fastapi_backend/m_25_fastapi_cli_and_cloud.py
    FASTAPI_ENV=production uv run fastapi run t04_fastapi_backend/m_25_fastapi_cli_and_cloud.py
    uv run fastapi dev --entrypoint t04_fastapi_backend.m_25_fastapi_cli_and_cloud:app

FastAPI Cloud (described here, never executed by this lesson)
A hosted platform from the FastAPI team: you give it your code, it gives you HTTPS, a
`*.fastapicloud.dev` URL, replication and request-based autoscaling. The flow from the docs:
    uv run fastapi login      browser-based sign in (`--no-open` prints the URL instead)
    uv run fastapi deploy     detects the app, asks to create/link a Cloud app, uploads, waits
`deploy` logs you in by itself if needed. Useful options: `--no-wait`, `--app-id`
(env FASTAPI_CLOUD_APP_ID), `--json`, and in CI a deploy token (env FASTAPI_CLOUD_TOKEN) instead
of a browser login. Other subcommands: `fastapi cloud logs | env | whoami | link | domains`.
What it relies on, according to the installed client:
- `pyproject.toml` (dependencies, and the `[tool.fastapi]` entrypoint so it finds the app); on
  the first deploy it asks which directory holds it (e.g. `backend`) and remembers the answer.
- The directory is uploaded as an archive. Always skipped: .venv, .git, __pycache__, *.pyc,
  .pytest_cache, .mypy_cache, .env and .env.* files, .fastapicloud. Add your own patterns in a
  `.fastapicloudignore` file (gitignore syntax).
- `.fastapicloud/cloud.json` links the folder to a Cloud app. Do not commit it (the folder
  contains its own .gitignore).
Secrets do not go in the archive: set them with `fastapi cloud env set` (see m_19).

Common mistakes
- Using `fastapi dev` in production (reload watcher, loopback-only host) or `fastapi run` while
  developing (no reload) and wondering why edits are ignored.
- Binding to 127.0.0.1 in a container (`--host 127.0.0.1`): unreachable from outside.
- Trusting proxy headers from anywhere (`--forwarded-allow-ips '*'`) when the app is directly
  exposed: clients can then spoof their IP. List the proxy IPs.
- Entrypoint typos: it must be `module.path:variable`, a dot path then ONE colon.
- Exporting only a factory (`def create_app()`) and no module-level `app`: the CLI can't find it.
- Running the CLI from another directory, so `pyproject.toml` is not seen.

Production notes
- Reload and `--workers` do not mix (uvicorn ignores workers when reloading): dev = reload,
  production = workers.
- On Kubernetes run one process per container (`fastapi run`) and scale replicas; on a single
  VM `--workers` ~ number of CPU cores.
- Disable interactive docs/OpenAPI in production if the API is not public (see create_app).
- Self-managed alternative to FastAPI Cloud: containers, see m_18.
"""

import importlib
import os
import tomllib
from collections.abc import Mapping

from fastapi import FastAPI
from fastapi.testclient import TestClient

DEFAULT_PATHS = (
    "main.py",
    "app.py",
    "api.py",
    "app/main.py",
    "app/app.py",
    "app/api.py",
)

EXAMPLE_PYPROJECT = """\
[project]
name = "awesomeapp"
version = "0.1.0"
dependencies = ["fastapi[standard]"]

[tool.fastapi]
entrypoint = "t04_fastapi_backend.m_25_fastapi_cli_and_cloud:app"
"""


def create_app(env: str = "development") -> FastAPI:
    """App factory: a new, independent app per call (great for tests)."""
    production = env == "production"
    app = FastAPI(
        title="CLI demo",
        # Hide the interactive docs and the schema outside development-like environments.
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
    return create_app(environ.get("FASTAPI_ENV", "development"))


# The CLI needs this module-level instance. `fastapi dev` sets FASTAPI_ENV before importing.
app = app_from_env(os.environ)


def build_argv(
    mode: str,
    target: str | None = None,
    *,
    port: int | None = None,
    host: str | None = None,
    workers: int | None = None,
) -> list[str]:
    """The command line for `mode` ("dev" | "run"): ["fastapi", mode, <target>, --host, ...]."""
    if mode not in ("dev", "run"):
        raise ValueError(f"mode must be 'dev' or 'run', not {mode!r}")
    if workers is not None and mode == "dev":
        raise ValueError("--workers only exists on `fastapi run`")
    argv = ["fastapi", mode]
    if target:
        argv.append(target)
    for flag, value in (("--host", host), ("--port", port), ("--workers", workers)):
        if value is not None:
            argv += [flag, str(value)]
    return argv


def read_entrypoint(pyproject_text: str) -> str | None:
    """`[tool.fastapi] entrypoint` of a pyproject.toml text, or None."""
    return tomllib.loads(pyproject_text).get("tool", {}).get("fastapi", {}).get("entrypoint")


def resolve_entrypoint(entrypoint: str) -> FastAPI:
    """What the CLI does with "module.path:attr": import the module, fetch the attribute."""
    module_name, _, attr = entrypoint.partition(":")
    if not module_name or not attr:
        raise ValueError("Import string must be in the format module.submodule:app_name")
    obj = getattr(importlib.import_module(module_name), attr)
    if not isinstance(obj, FastAPI):
        raise TypeError(f"{entrypoint} is not a FastAPI app")
    return obj


if __name__ == "__main__":
    client = TestClient(create_app("development"))
    print("development:", client.get("/info").json(), "docs ->", client.get("/docs").status_code)
    client = TestClient(create_app("production"))
    print("production: ", client.get("/info").json(), "docs ->", client.get("/docs").status_code)

    print("\n== argv the CLI would be given (nothing is started) ==")
    print(" ".join(build_argv("dev", "main.py")))
    print(" ".join(build_argv("run", "main.py", host="0.0.0.0", port=80, workers=4)))

    print("\n== entrypoint from pyproject.toml ==")
    entrypoint = read_entrypoint(EXAMPLE_PYPROJECT)
    print(entrypoint)
    resolved = resolve_entrypoint(entrypoint) if entrypoint else None
    print("resolved ->", type(resolved).__name__, getattr(resolved, "title", None))

    print("\n== FastAPI Cloud (never run here) ==")
    print("uv run fastapi login   # opens a browser")
    print("uv run fastapi deploy  # uploads the folder, prints https://<app>.fastapicloud.dev")
