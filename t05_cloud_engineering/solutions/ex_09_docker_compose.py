"""Exercise 09: parse and validate Docker Compose configuration as plain Python.

A compose file loaded from YAML is a dict:
    {"services": {"api": {"image": "...", "depends_on": {...} or [...], ...}, ...}}

Tasks
1. parse_env_file: parse `.env` text.
2. interpolate: expand ${VAR} and ${VAR:-default}.
3. normalize_env: turn `environment` (dict or list of "K=V") into a dict of strings.
4. startup_order: dependency-ordered service list.
5. validate_compose: report common mistakes.

Run: uv run pytest t05_cloud_engineering -k docker_compose
"""

import re
from collections.abc import Mapping
from typing import Any

SECRET_WORDS = ("PASSWORD", "SECRET", "TOKEN", "API_KEY", "PRIVATE_KEY")


def parse_env_file(text: str) -> dict[str, str]:
    """Parse KEY=VALUE lines.

    - Ignore blank lines and lines starting with '#'.
    - Allow an optional leading "export ".
    - Strip whitespace around key and value.
    - A value wrapped in matching single or double quotes keeps its inner text as is
      (including '#'); the quotes are removed.
    - For an unquoted value, drop an inline comment that starts with whitespace + '#'.
    - Lines without '=' are ignored. Only split on the FIRST '='.
    """
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
            value = value[1:-1]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        values[key.strip()] = value
    return values


def interpolate(text: str, env: Mapping[str, str]) -> str:
    """Expand ${VAR} and ${VAR:-default}.

    A variable that is unset OR empty uses the default if given; with no default an unset
    variable expands to "".
    """

    def repl(match: re.Match[str]) -> str:
        name, default = match.group(1), match.group(2)
        return env.get(name) or (default if default is not None else "")

    return re.sub(r"\$\{(\w+)(?::-([^}]*))?\}", repl, text)


def normalize_env(environment: dict[str, Any] | list[str] | None) -> dict[str, str]:
    """Normalize a compose `environment` value.

    - None or empty -> {}
    - dict -> same keys; values converted with str(); None becomes ""
    - list of "KEY=value" strings -> dict (split on the first '='; "KEY" alone -> "")
    """
    if not environment:
        return {}
    if isinstance(environment, dict):
        return {k: "" if v is None else str(v) for k, v in environment.items()}
    result: dict[str, str] = {}
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


def startup_order(compose: dict[str, Any]) -> list[str]:
    """Return service names so every service comes after the services it depends on.

    `depends_on` may be a list of names or a dict {name: {"condition": ...}}.
    Among services that are ready at the same time pick them in alphabetical order.
    Raise ValueError for an unknown dependency or a dependency cycle.
    """
    services = compose["services"]
    remaining = {name: set(_dependencies(svc)) for name, svc in services.items()}
    for name, wanted in remaining.items():
        unknown = wanted - services.keys()
        if unknown:
            raise ValueError(f"{name} depends on unknown service(s): {sorted(unknown)}")
    order: list[str] = []
    while remaining:
        ready = sorted(n for n, d in remaining.items() if d <= set(order))
        if not ready:
            raise ValueError(f"dependency cycle among: {sorted(remaining)}")
        order.append(ready[0])
        del remaining[ready[0]]
    return order


def validate_compose(compose: dict[str, Any]) -> list[str]:
    """Return a sorted list of unique issue strings:

    - "latest-tag:<service>": `image` has no tag, or tag "latest" (a digest "@sha256:" is ok;
      services using `build:` without `image:` are skipped)
    - "inline-secret:<service>:<VAR>": an environment variable whose NAME contains PASSWORD,
      SECRET, TOKEN, API_KEY or PRIVATE_KEY (case-insensitive) has a non-empty literal value
      (values that start with "${" are fine)
    - "unknown-dependency:<service>:<dep>": depends_on names a service that does not exist
    - "missing-healthcheck:<dep>": some service waits on <dep> with condition
      "service_healthy" but <dep> defines no `healthcheck`
    """
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
