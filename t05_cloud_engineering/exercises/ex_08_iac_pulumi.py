"""Exercise 08: pure-Python IaC helpers: stack config, secret redaction, a mini preview.

No Pulumi or cloud needed (the real program is `iac/pulumi_main.py`; read it, do not run it).

Tasks
1. merge_stack_config: deep-merge shared defaults with stack overrides (no mutation).
2. redact_secrets: return a copy that is safe to log.
3. required_config: fetch required keys or raise ConfigError listing ALL missing ones.
4. plan_diff: compare current vs desired resources like `pulumi preview`.

Run: uv run pytest t05_cloud_engineering -k iac_pulumi
"""

import copy  # noqa: F401  (handy for tasks 1 and 2)
from typing import Any

SECRET_MARKERS = ("password", "secret", "token", "apikey", "api_key", "private_key")


class ConfigError(Exception):
    """Raised when required stack configuration is missing."""


def merge_stack_config(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Return a NEW dict: `base` updated with `overrides`.

    Nested dicts are merged recursively; any other value (including lists) in `overrides`
    replaces the base value. Neither input may be mutated, and the result must not share
    nested objects with them.
    """
    raise NotImplementedError


def redact_secrets(value: Any) -> Any:
    """Return a copy where the value of every dict key containing a SECRET_MARKERS entry
    (case-insensitive substring) is replaced by the string "[secret]".

    Recurse through nested dicts and lists (including dicts inside lists). Other values are
    returned unchanged. Do not mutate the input.
    """
    raise NotImplementedError


def required_config(config: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    """Return {key: config[key]} for each key in `keys`.

    If any are missing raise ConfigError whose message names ALL missing keys, not just the
    first.
    """
    raise NotImplementedError


def plan_diff(
    current: dict[str, dict[str, Any]], desired: dict[str, dict[str, Any]]
) -> dict[str, list[str]]:
    """Return {"create": [...], "update": [...], "delete": [...], "same": [...]} with sorted
    resource names.

    create: only in desired; delete: only in current; update: in both with different
    properties; same: in both with equal properties.
    """
    raise NotImplementedError
