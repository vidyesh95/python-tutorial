# Infrastructure as Code with Pulumi
"""
Pulumi is the other popular Python IaC tool. Same goal as CDK (m_07), different engine:
- CDK compiles to CloudFormation and AWS applies it. Pulumi runs your program and talks to
  cloud APIs directly (through providers), recording what it made in STATE.
- Pulumi is multi-cloud (AWS, GCP, Azure, Kubernetes, ...) with one model; CDK is AWS-first.

Concepts
- PROJECT: a folder with `Pulumi.yaml` (name, runtime: python).
- STACK: one instance of the project with its own config and state (`dev`, `staging`,
  `prod`). Same code, different config.
- RESOURCES are Python objects: `aws.s3.BucketV2("uploads", tags=...)`. The first argument
  is the logical name; Pulumi derives the physical name (suffixed) so replacements are safe.
- OUTPUTS: values only known after deployment. `bucket.id` is an `Output[str]`, not a str.
  Pass Outputs straight into other resources (dependency tracking is automatic); transform
  them with `.apply(lambda v: ...)` or `pulumi.Output.concat(...)`. Never print them as str.
- CONFIG and SECRETS: `pulumi.Config().require("x")`; `pulumi config set --secret dbPassword`
  stores it ENCRYPTED in `Pulumi.<stack>.yaml` and masks it in output. Still prefer
  referencing Secrets Manager (m_13) for real credentials.
- STATE BACKEND: where Pulumi records the stack. Pulumi Cloud (default, free for
  individuals), or self-managed: `pulumi login s3://my-state-bucket` / a local file backend.
  State is sensitive (and lets Pulumi know what to delete): protect and version it.
- WORKFLOW: `pulumi preview` (a plan; no changes) -> `pulumi up` -> `pulumi destroy`.
  `pulumi refresh` re-reads reality to detect drift.
- Stack references let one stack read another's exports (network stack -> app stack).

The real program is `iac/pulumi_main.py` (NOT executed here). This lesson demonstrates, in
pure Python, ideas you reuse in any IaC project: per-stack config merging, secret redaction
(logging a config must not leak secrets) and a mini "preview" that diffs desired vs current.

Common mistakes
- Treating an `Output` like a normal value (`f"{bucket.id}"`, `if bucket.id == ...`).
- Renaming a resource's logical name (replaces it: delete + create); use `aliases`.
- Committing plaintext secrets in config or code, or losing the secrets passphrase/key.
- Running `pulumi up` from many laptops at once against shared state (use CI + locks).
- Skipping `preview`, or ignoring the `replace` markers in it.
- Leaving stacks around: always `pulumi destroy` sandboxes, then `pulumi stack rm`.

Production notes
- One project per lifecycle (network, data, app); share via stack references.
- Run preview on pull requests and `up` on merge (m_11), with a role assumed via OIDC.
- Use `protect=True` on stateful resources and `retain_on_delete` where appropriate.
- Unit-test programs with Pulumi's mocks (`pulumi.runtime.set_mocks`) in a normal pytest.

Cost notes
- Pulumi Cloud is free for individuals; team features are paid. State in your own bucket is
  pennies. The real cost is the resources: tag them and destroy sandboxes.
- `pulumi preview` and `cdk diff` are free: review them as carefully as code diffs.
"""

import copy
from pathlib import Path
from typing import Any

PULUMI_MAIN = Path(__file__).resolve().parent / "iac" / "pulumi_main.py"
SECRET_MARKERS = ("password", "secret", "token", "apikey", "api_key", "private_key")

PULUMI_YAML = """\
name: ingest
runtime: python
description: Ingest pipeline for the t04 API
"""


class ConfigError(Exception):
    """Raised when required stack configuration is missing."""


# Example 1: per-stack config = shared defaults + stack overrides (deep merge)
def merge_stack_config(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_stack_config(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


# Example 2: never log secrets
def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: "[secret]" if any(m in k.lower() for m in SECRET_MARKERS) else redact_secrets(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(v) for v in value]
    return value


def required_config(config: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    missing = [k for k in keys if k not in config]
    if missing:
        raise ConfigError(f"missing required config: {', '.join(missing)}")
    return {k: config[k] for k in keys}


# Example 3: a mini `pulumi preview`: desired state vs what exists
def plan_diff(
    current: dict[str, dict[str, Any]], desired: dict[str, dict[str, Any]]
) -> dict[str, list[str]]:
    return {
        "create": sorted(desired.keys() - current.keys()),
        "update": sorted(n for n in desired.keys() & current.keys() if desired[n] != current[n]),
        "delete": sorted(current.keys() - desired.keys()),
        "same": sorted(n for n in desired.keys() & current.keys() if desired[n] == current[n]),
    }


if __name__ == "__main__":
    base = {"region": "us-east-1", "logRetentionDays": 14, "db": {"instance": "t4g.micro"}}
    prod = {"logRetentionDays": 90, "db": {"instance": "m7g.large", "dbPassword": "hunter2"}}
    config = merge_stack_config(base, prod)
    print("merged:", config["logRetentionDays"], config["db"]["instance"])
    print("base untouched:", base["db"])
    print("safe to log:", redact_secrets(config))
    try:
        required_config(config, ["region", "vpcId", "subnetIds"])
    except ConfigError as exc:
        print("config error:", exc)

    current = {"bucket": {"versioned": False}, "queue": {"vt": 30}, "old-log": {}}
    desired = {"bucket": {"versioned": True}, "queue": {"vt": 30}, "alarm": {"threshold": 5}}
    for action, names in plan_diff(current, desired).items():
        print(f"  {action:<6} {names}")
    print(
        "pulumi_main.py exists:",
        PULUMI_MAIN.exists(),
        "| Pulumi.yaml project:",
        PULUMI_YAML.splitlines()[0],
    )
