# Dockerizing FastAPI
"""
A container image packages your app and its dependencies so it runs the same everywhere.
The files for this lesson live next to it (read them, they are commented):
    docker/Dockerfile      multi-stage uv build of this very app
    docker/compose.yaml    api + postgres + redis for local development

Build and run (needs Docker; this lesson itself does not):
    docker build -f t04_fastapi_backend/docker/Dockerfile -t fastapi-lesson .
    docker run --rm -p 8000:8000 fastapi-lesson
    docker compose -f t04_fastapi_backend/docker/compose.yaml up --build

Run the app without Docker:  uv run fastapi dev t04_fastapi_backend/m_18_dockerizing_fastapi.py

The Dockerfile, explained
1. MULTI-STAGE. Stage "builder" has uv and installs dependencies into /app/.venv. Stage
   "runtime" starts from a clean slim image and copies only the finished venv + your code.
   Result: smaller image, smaller attack surface, no build tools in production.
2. LAYER CACHING. Copy `pyproject.toml` + `uv.lock` first and install; copy source code AFTER.
   Editing code then reuses the cached dependency layer (rebuilds take seconds).
3. REPRODUCIBLE INSTALL. `uv sync --frozen` installs exactly what `uv.lock` pins and fails if
   the lock is stale. `--no-install-project` installs only dependencies.
4. NON-ROOT USER. `USER app` (fixed uid) so a compromised app is not root in the container.
5. HEALTHCHECK. Docker/compose/orchestrators call `/healthz` to know when the app is alive.
   (slim images lack curl, so the check uses Python.)
6. EXEC-FORM CMD. `CMD ["uvicorn", ...]` runs uvicorn as PID 1, so SIGTERM triggers graceful
   shutdown (lifespan teardown). Shell-form CMD would run it under `sh -c` and swallow it.
7. WORKERS. `WEB_CONCURRENCY=2` gives uvicorn 2 processes. On Kubernetes prefer 1 process per
   container and scale replicas. `fastapi run --workers N app.py` is the other common option.

.dockerignore (at the build-context root) keeps the context small and secrets out of images:
see DOCKERIGNORE below. Without it `COPY .` would ship `.git`, `.venv`, `.env`, caches...

Common mistakes
- Baking secrets into the image (`ENV API_KEY=...`, copying `.env`). Inject at runtime.
- `FROM python:latest` or no tag: builds change under you. Pin the minor version (3.15-slim)
  or even a digest.
- Running as root; copying the whole repo before installing dependencies (no cache).
- Binding to `127.0.0.1` inside the container: unreachable from outside. Use `0.0.0.0`.
- One giant image with dev tools, tests, and compilers shipped to production.
- Treating `depends_on` as readiness. Use `condition: service_healthy` + a healthcheck.

Production notes
- Run migrations (Alembic, m_08) as a separate one-off job/init step, not in every replica.
- Scan images (Trivy, Grype), rebuild regularly for base-image patches, and sign/tag by git SHA.
- Set CPU/memory limits; stay under them (workers x memory per worker).
- Behind a proxy/load balancer run uvicorn with `--proxy-headers` and `--forwarded-allow-ips`.
- Log to stdout/stderr only; the platform collects it (see m_17).
- Alternative to self-managed containers: FastAPI Cloud (`fastapi deploy`), see m_25.
"""

import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

DOCKER_DIR = Path(__file__).resolve().parent / "docker"

app = FastAPI(title="Dockerized app", version="1.0.0")

DOCKERIGNORE = """\
.git
.venv
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.env
.env.*
**/tests/
Dockerfile*
compose*.yaml
"""


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"service": app.title, "version": app.version}


# Example: peek inside a Dockerfile (join `\` continuations, skip comments)
def parse_dockerfile(text: str) -> list[tuple[str, str]]:
    logical = re.sub(r"\\\s*\n", " ", text)
    pairs = []
    for line in logical.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            instruction, _, args = line.partition(" ")
            pairs.append((instruction.upper(), args.strip()))
    return pairs


def summarize(text: str) -> dict[str, object]:
    pairs = parse_dockerfile(text)
    users = [args for ins, args in pairs if ins == "USER"]
    return {
        "stages": [args for ins, args in pairs if ins == "FROM"],
        "final_user": users[-1] if users else "root (default!)",
        "healthcheck": any(ins == "HEALTHCHECK" for ins, _ in pairs),
        "exposed": [args for ins, args in pairs if ins == "EXPOSE"],
        "cmd": next((args for ins, args in reversed(pairs) if ins == "CMD"), None),
    }


if __name__ == "__main__":
    client = TestClient(app)
    print(client.get("/healthz").json(), client.get("/").json())

    for name in ("Dockerfile", "compose.yaml"):
        text = (DOCKER_DIR / name).read_text()
        print(f"\n===== docker/{name} ({len(text.splitlines())} lines) =====")
        print(text)

    print("===== .dockerignore (put at the build-context root) =====")
    print(DOCKERIGNORE)

    print("===== what the Dockerfile builds =====")
    for key, value in summarize((DOCKER_DIR / "Dockerfile").read_text()).items():
        print(f"{key:12} {value}")
