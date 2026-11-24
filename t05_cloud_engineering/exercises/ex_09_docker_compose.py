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

import re  # noqa: F401  (handy for tasks 1, 2 and 5)
from collections.abc import Mapping
from typing import Any


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
    raise NotImplementedError


def interpolate(text: str, env: Mapping[str, str]) -> str:
    """Expand ${VAR} and ${VAR:-default}.

    A variable that is unset OR empty uses the default if given; with no default an unset
    variable expands to "".
    """
    raise NotImplementedError


def normalize_env(environment: dict[str, Any] | list[str] | None) -> dict[str, str]:
    """Normalize a compose `environment` value.

    - None or empty -> {}
    - dict -> same keys; values converted with str(); None becomes ""
    - list of "KEY=value" strings -> dict (split on the first '='; "KEY" alone -> "")
    """
    raise NotImplementedError


def startup_order(compose: dict[str, Any]) -> list[str]:
    """Return service names so every service comes after the services it depends on.

    `depends_on` may be a list of names or a dict {name: {"condition": ...}}.
    Among services that are ready at the same time pick them in alphabetical order.
    Raise ValueError for an unknown dependency or a dependency cycle.
    """
    raise NotImplementedError


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
    raise NotImplementedError
