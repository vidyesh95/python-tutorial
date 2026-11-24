# Secrets Management
"""
A secret is anything that grants access: database passwords, API keys, tokens, private keys.
Rules: never in git, never in the image, never in logs, rotated, and readable only by the
workloads that need them.

Where to keep them (AWS)
- SECRETS MANAGER: purpose-built. Versioned secrets (JSON string), KMS encryption, IAM and
  audit via CloudTrail, built-in ROTATION (a Lambda changes the password in the database and
  in the secret). ~ $0.40 per secret per month + API calls.
- SSM PARAMETER STORE: hierarchical key-value config (`/taskboard/prod/db_host`). Type
  `String` for config, `SecureString` (KMS) for secrets. Standard parameters are free. No
  built-in rotation. Great for non-rotating config and cheap secrets.
- Rule of thumb: Secrets Manager for credentials that rotate; Parameter Store for config and
  simple secrets.
GCP equivalent: SECRET MANAGER (`google-cloud-secret-manager`): a secret has numbered
VERSIONS; code reads `projects/P/secrets/NAME/versions/latest` with
`SecretManagerServiceClient().access_secret_version(name=...)`; grant
`roles/secretmanager.secretAccessor` on that ONE secret to the service account. Cloud Run can
also mount a secret as an env var or file with no code at all. (Library not installed here.)

Versions and rotation (Secrets Manager)
- Each `put_secret_value` creates a new VERSION. Staging labels mark them: `AWSCURRENT` (what
  readers get by default), `AWSPREVIOUS` (the one before), `AWSPENDING` (during rotation).
- Rotation = create a new credential (pending) -> set it in the database -> test it -> promote
  it to AWSCURRENT. Clients that fetch the current value on each (cached) read pick it up;
  keep the previous version valid briefly so in-flight connections do not break.
- Cache secrets in memory with a short TTL (a few minutes): fast, cheap, and still picks up
  rotation. Fetching on every request is slow and costs API calls; fetching once at boot and
  never again breaks on rotation.

In code: read the secret at startup / lazily, hold it as a `SecretStr`-like object so that
printing or logging it shows `**********`, and mask known secret values in any text you emit.

Everything here runs on moto (an in-memory fake AWS).

Common mistakes
- Secrets in environment-variable LITERALS in IaC (they appear in templates/state) or
  task definitions; reference the secret instead (ECS `secrets:` injects at runtime).
- Logging request headers, connection strings or exception text that contains a password.
- One shared secret for every service/environment; no rotation; no owner.
- `secretsmanager:GetSecretValue` on `*` (grant the one ARN) and forgetting KMS permissions.
- Fetching the secret on every request (latency + throttling + cost).
- Treating base64 (Kubernetes Secret) as encryption.

Production notes
- Prefer IAM-auth / short-lived credentials where available (RDS IAM auth, workload identity)
  so there is no static secret at all.
- Alarm on unusual GetSecretValue calls; scan repos for leaked keys (git-secrets, gitleaks)
  and revoke any key that was ever committed.
- Separate secrets per environment and per service, with tags for ownership.

Cost notes
- Secrets Manager: ~ $0.40/secret/month + ~ $0.05 per 10,000 API calls. Many tiny secrets add
  up: store one JSON secret per service. Parameter Store standard tier is free.
- KMS customer-managed keys cost ~ $1/month each plus requests; the AWS-managed key is free.
"""

import json
import os
import time
from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import boto3
from botocore.exceptions import ClientError
from moto import mock_aws
from pydantic import SecretStr

FAKE_AWS_ENV = {
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "AWS_SESSION_TOKEN": "testing",
    "AWS_DEFAULT_REGION": "us-east-1",
}


# Example 1: create-or-update a JSON secret (each write is a new version)
def create_or_update_secret(sm: Any, name: str, value: dict[str, str]) -> str:
    payload = json.dumps(value)
    try:
        return sm.put_secret_value(SecretId=name, SecretString=payload)["VersionId"]
    except ClientError as err:
        if err.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
    return sm.create_secret(Name=name, SecretString=payload)["VersionId"]


def get_secret_json(sm: Any, name: str, stage: str = "AWSCURRENT") -> dict[str, str]:
    return json.loads(sm.get_secret_value(SecretId=name, VersionStage=stage)["SecretString"])


# Example 2: Parameter Store: read a whole config path (paginated, decrypted)
def get_parameters_by_path(ssm: Any, path: str) -> dict[str, str]:
    prefix = path.rstrip("/") + "/"
    values: dict[str, str] = {}
    pages = ssm.get_paginator("get_parameters_by_path").paginate(
        Path=path, Recursive=True, WithDecryption=True
    )
    for page in pages:
        for param in page["Parameters"]:
            values[param["Name"].removeprefix(prefix)] = param["Value"]
    return values


# Example 3: a TTL cache so secrets are not fetched on every call (but rotation is noticed)
class TTLCache:
    def __init__(
        self, fetch: Callable[[str], Any], ttl: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._fetch, self._ttl, self._clock = fetch, ttl, clock
        self._items: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any:
        now = self._clock()
        hit = self._items.get(key)
        if hit and now - hit[0] < self._ttl:
            return hit[1]
        value = self._fetch(key)
        self._items[key] = (now, value)
        return value


# Example 4: never log secrets
def mask(text: str, secrets: list[str]) -> str:
    for secret in sorted(filter(None, secrets), key=len, reverse=True):  # longest first
        text = text.replace(secret, "***")
    return text


def run_demo() -> None:
    sm = boto3.client("secretsmanager", region_name="us-east-1")
    ssm = boto3.client("ssm", region_name="us-east-1")

    v1 = create_or_update_secret(sm, "taskboard/prod/db", {"user": "app", "password": "pw-1"})
    v2 = create_or_update_secret(sm, "taskboard/prod/db", {"user": "app", "password": "pw-2"})
    print("new version on rotation:", v1 != v2)
    print("current  :", mask(json.dumps(get_secret_json(sm, "taskboard/prod/db")), ["pw-2"]))
    print(
        "previous password was:",
        get_secret_json(sm, "taskboard/prod/db", "AWSPREVIOUS")["password"],
    )

    calls: list[str] = []

    def fetch(name: str) -> dict[str, str]:
        calls.append(name)
        return get_secret_json(sm, name)

    cache = TTLCache(fetch, ttl=300)
    for _ in range(3):
        cache.get("taskboard/prod/db")
    print("API calls for 3 reads:", len(calls))

    ssm.put_parameter(Name="/taskboard/prod/db_host", Value="db.internal", Type="String")
    ssm.put_parameter(Name="/taskboard/prod/api_key", Value="k-123", Type="SecureString")
    config = get_parameters_by_path(ssm, "/taskboard/prod")
    print("parameters:", sorted(config))

    password = SecretStr(config["api_key"])
    print("repr is safe:", password, "| value only when asked:", password.get_secret_value())


if __name__ == "__main__":
    with patch.dict(os.environ, FAKE_AWS_ENV), mock_aws():
        run_demo()
