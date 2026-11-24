# Local Multi-Service Stacks with Docker Compose
"""
Docker Compose describes a multi-container application in one `compose.yaml` and runs it
with one command: `docker compose up --build` (stop: `down`, also drop data: `down -v`).
It is the best way to give every developer (and CI) the same API + Postgres + Redis.

Anatomy of a compose file
- `services:` each is a container: `image:` OR `build:`, `ports:`, `environment:`,
  `env_file:`, `volumes:`, `depends_on:`, `healthcheck:`, `restart:`.
- NETWORKS: Compose creates a private network; services reach each other by SERVICE NAME
  (`postgres:5432`, `redis:6379`). `ports: "8000:8000"` is only for access from the host.
- VOLUMES: named volumes (`pgdata:`) keep data when containers are re-created; bind mounts
  (`./src:/app/src`) share host files (dev hot reload).
- HEALTHCHECK: a command Docker runs to decide a container is `healthy`
  (`pg_isready`, `redis-cli ping`, an HTTP `/healthz`, see t04 m_18).
- `depends_on` with `condition: service_healthy` makes the API wait until Postgres is
  actually ready. Plain `depends_on: [postgres]` only orders STARTING, not readiness.
- CONFIG: `environment:` (inline), `env_file: .env` (a file next to compose; keep it out of
  git, commit `.env.example`), and `${VAR}` / `${VAR:-default}` interpolation from your shell
  or `.env`. `docker compose config` prints the fully resolved file: use it to validate.
- SECRETS: for real credentials use Compose `secrets:` (mounted at /run/secrets/...) or an
  external secret store; never hard-code passwords in the compose file or the image.

The t04 stack (`t04_fastapi_backend/docker/compose.yaml`: api + postgres + redis) is the
capstone's local environment. This lesson models a compose file as a Python dict and shows
how to PARSE and VALIDATE one with plain Python: env files, startup order and lint checks.
(Real YAML parsing needs a library such as PyYAML; the logic is identical on the loaded dict.)

Common mistakes
- Treating `depends_on` as readiness (no healthcheck / no `service_healthy`).
- Publishing databases on all interfaces (`"5432:5432"`); bind to `127.0.0.1:5432:5432`.
- Secrets in `environment:` literals, or `.env` committed to git.
- `image: postgres` / `:latest` instead of a pinned tag; surprise upgrades corrupt volumes.
- Using `localhost` between containers (it means the container itself): use service names.
- `docker compose down -v` in the wrong directory, deleting a dev database you wanted.

Production notes
- Compose is for dev/test and small single-host deployments. For fleets use ECS/Cloud Run
  or Kubernetes (m_10, capstone); the same image runs everywhere.
- Add resource limits, restart policies and log rotation if you run Compose on a server.
- Keep one base file + override files (`-f compose.yaml -f compose.prod.yaml`).
- Run migrations as a one-off service (`docker compose run --rm migrate`).

Cost notes
- Compose itself is free; Docker Desktop licensing applies to large companies. Building images
  in CI costs minutes: cache layers (t04 m_18) and pin base images.
- Idle local volumes eat disk: `docker system df`, `docker volume prune`.
"""

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

T04_COMPOSE = (
    Path(__file__).resolve().parents[1] / "t04_fastapi_backend" / "docker" / "compose.yaml"
)
SECRET_WORDS = ("PASSWORD", "SECRET", "TOKEN", "API_KEY", "PRIVATE_KEY")

COMPOSE: dict[str, Any] = {
    "name": "taskboard",
    "services": {
        "api": {
            "build": {"context": ".", "dockerfile": "Dockerfile"},
            "ports": ["8000:8000"],
            "env_file": [".env"],
            "environment": {
                "DATABASE_URL": "postgresql+asyncpg://app:${POSTGRES_PASSWORD}@postgres:5432/app",
                "REDIS_URL": "redis://redis:6379/0",
            },
            "depends_on": {
                "postgres": {"condition": "service_healthy"},
                "redis": {"condition": "service_healthy"},
            },
        },
        "postgres": {
            "image": "postgres:17-alpine",
            "environment": {"POSTGRES_PASSWORD": "${POSTGRES_PASSWORD}"},
            "volumes": ["pgdata:/var/lib/postgresql/data"],
            "healthcheck": {"test": ["CMD-SHELL", "pg_isready -U app"], "interval": "5s"},
        },
        "redis": {
            "image": "redis:7-alpine",
            "healthcheck": {"test": ["CMD", "redis-cli", "ping"], "interval": "5s"},
        },
    },
    "volumes": {"pgdata": {}},
}


# Example 1: parse a .env file
def parse_env_file(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.removeprefix("export ").strip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]  # quoted: keep everything inside, including '#'
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()  # drop inline comment
        values[key.strip()] = value
    return values


# Example 2: ${VAR} / ${VAR:-default} interpolation
def interpolate(text: str, env: Mapping[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        name, default = match.group(1), match.group(2)
        return env.get(name) or (default if default is not None else "")

    return re.sub(r"\$\{(\w+)(?::-([^}]*))?\}", repl, text)


# Example 3: `environment` may be a dict or a list of "KEY=value"
def normalize_env(environment: dict[str, Any] | list[str] | None) -> dict[str, str]:
    if not environment:
        return {}
    if isinstance(environment, dict):
        return {k: "" if v is None else str(v) for k, v in environment.items()}
    result = {}
    for item in environment:
        key, _, value = item.partition("=")
        result[key] = value
    return result


def _tag(image: str) -> str | None:
    """Tag of an image reference; a ':' before the last '/' is a registry port, not a tag."""
    last = image.rsplit("/", 1)[-1]
    return last.split(":", 1)[1] if ":" in last else None


def _dependencies(service: dict[str, Any]) -> dict[str, str | None]:
    deps = service.get("depends_on") or {}
    if isinstance(deps, list):
        return dict.fromkeys(deps)
    return {name: (cfg or {}).get("condition") for name, cfg in deps.items()}


# Example 4: dependency-ordered startup (topological sort)
def startup_order(compose: dict[str, Any]) -> list[str]:
    services = compose["services"]
    deps = {name: set(_dependencies(svc)) for name, svc in services.items()}
    for name, wanted in deps.items():
        unknown = wanted - services.keys()
        if unknown:
            raise ValueError(f"{name} depends on unknown service(s): {sorted(unknown)}")
    order: list[str] = []
    remaining = dict(deps)
    while remaining:
        ready = sorted(n for n, d in remaining.items() if d <= set(order))
        if not ready:
            raise ValueError(f"dependency cycle among: {sorted(remaining)}")
        order.append(ready[0])
        del remaining[ready[0]]
    return order


# Example 5: lint a compose file
def validate_compose(compose: dict[str, Any]) -> list[str]:
    issues: set[str] = set()
    services = compose.get("services", {})
    for name, svc in services.items():
        image = svc.get("image")
        if image and "@sha256:" not in image and _tag(image) in (None, "latest"):
            issues.add(f"latest-tag:{name}")
        for var, value in normalize_env(svc.get("environment")).items():
            if any(w in var.upper() for w in SECRET_WORDS) and value and not value.startswith("${"):
                issues.add(f"inline-secret:{name}:{var}")
        for dep, condition in _dependencies(svc).items():
            if dep not in services:
                issues.add(f"unknown-dependency:{name}:{dep}")
            elif condition == "service_healthy" and "healthcheck" not in services[dep]:
                issues.add(f"missing-healthcheck:{dep}")
    return sorted(issues)


def service_names_from_text(text: str) -> list[str]:
    """Names under the top-level `services:` key, found without a YAML parser."""
    names, in_services = [], False
    for line in text.splitlines():
        if re.match(r"^\S", line) and not line.startswith("#"):
            in_services = line.startswith("services:")
            continue
        if in_services and (m := re.match(r"^  ([\w-]+):\s*$", line)):
            names.append(m.group(1))
    return names


if __name__ == "__main__":
    print("startup order:", startup_order(COMPOSE))
    print("issues (clean):", validate_compose(COMPOSE))

    bad = {
        "services": {
            "api": {"image": "myapp", "depends_on": {"db": {"condition": "service_healthy"}}},
            "db": {"image": "postgres:latest", "environment": ["POSTGRES_PASSWORD=hunter2"]},
            "worker": {"image": "x:1", "depends_on": ["ghost"]},
        }
    }
    for issue in validate_compose(bad):
        print("  issue:", issue)
    try:
        startup_order({"services": {"a": {"depends_on": ["b"]}, "b": {"depends_on": ["a"]}}})
    except ValueError as exc:
        print("cycle:", exc)

    env = parse_env_file('# dev\nPOSTGRES_PASSWORD="s3cret #1"\nexport LOG_LEVEL=debug # inline\n')
    print("env file:", {k: ("***" if "PASSWORD" in k else v) for k, v in env.items()})
    print("interpolate:", interpolate("postgresql://app:${PW}@db/${DB:-app}", {"PW": "x"}))
    print("t04 compose services:", service_names_from_text(T04_COMPOSE.read_text()))
