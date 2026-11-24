"""Exercise 08: pure-Python IaC helpers: stack config, secret redaction, a mini preview.

No Pulumi or cloud needed (the real program is `iac/pulumi_main.py`; read it, do not run it).

Tasks
1. merge_stack_config: deep-merge shared defaults with stack overrides (no mutation).
2. redact_secrets: return a copy that is safe to log.
3. required_config: fetch required keys or raise ConfigError listing ALL missing ones.
4. plan_diff: compare current vs desired resources like `pulumi preview`.

Run: uv run pytest t05_cloud_engineering -k iac_pulumi
"""

import copy
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
    merged = copy.deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_stack_config(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def redact_secrets(value: Any) -> Any:
    """Return a copy where the value of every dict key containing a SECRET_MARKERS entry
    (case-insensitive substring) is replaced by the string "[secret]".

    Recurse through nested dicts and lists (including dicts inside lists). Other values are
    returned unchanged. Do not mutate the input.
    """
    if isinstance(value, dict):
        return {
            k: "[secret]" if any(m in k.lower() for m in SECRET_MARKERS) else redact_secrets(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(v) for v in value]
    return value


def required_config(config: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    """Return {key: config[key]} for each key in `keys`.

    If any are missing raise ConfigError whose message names ALL missing keys, not just the
    first.
    """
    missing = [k for k in keys if k not in config]
    if missing:
        raise ConfigError(f"missing required config: {', '.join(missing)}")
    return {k: config[k] for k in keys}


def plan_diff(
    current: dict[str, dict[str, Any]], desired: dict[str, dict[str, Any]]
) -> dict[str, list[str]]:
    """Return {"create": [...], "update": [...], "delete": [...], "same": [...]} with sorted
    resource names.

    create: only in desired; delete: only in current; update: in both with different
    properties; same: in both with equal properties.
    """
    both = current.keys() & desired.keys()
    return {
        "create": sorted(desired.keys() - current.keys()),
        "update": sorted(n for n in both if current[n] != desired[n]),
        "delete": sorted(current.keys() - desired.keys()),
        "same": sorted(n for n in both if current[n] == desired[n]),
    }
