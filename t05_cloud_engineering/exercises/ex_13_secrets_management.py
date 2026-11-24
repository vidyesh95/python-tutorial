"""Exercise 13: Secrets Manager, Parameter Store, caching and masking.

`sm` is a boto3 "secretsmanager" client and `ssm` an "ssm" client (moto-backed in tests).

Tasks
1. create_or_update_secret: store a dict as a JSON secret; each call adds a version.
2. get_secret_json: read a secret (by version stage) back as a dict.
3. get_parameters_by_path: read a whole parameter-store path, decrypted.
4. TTLCache: fetch-through cache with an injectable clock.
5. mask: replace secret values in text before logging it.

Run: uv run pytest t05_cloud_engineering -k secrets
"""

import json  # noqa: F401  (handy for tasks 1 and 2)
import time
from collections.abc import Callable
from typing import Any

from botocore.exceptions import ClientError  # noqa: F401  (handy for task 1)


def create_or_update_secret(sm: Any, name: str, value: dict[str, str]) -> str:
    """Store json.dumps(value) as the secret `name` and return the new VersionId.

    If the secret does not exist create it (create_secret); if it exists add a new version
    (put_secret_value). Only treat the error code "ResourceNotFoundException" as "does not
    exist"; re-raise other ClientErrors.
    """
    raise NotImplementedError


def get_secret_json(sm: Any, name: str, stage: str = "AWSCURRENT") -> dict[str, str]:
    """Return the secret's SecretString decoded from JSON for the given version stage."""
    raise NotImplementedError


def get_parameters_by_path(ssm: Any, path: str) -> dict[str, str]:
    """Return {relative_name: value} for every parameter under `path`, recursively, with
    decryption, using the get_parameters_by_path paginator.

    relative_name is the parameter Name without the `path` prefix and its slash:
    path "/app/prod" and Name "/app/prod/db/host" -> "db/host".
    """
    raise NotImplementedError


class TTLCache:
    """Cache fetch(key) results for `ttl` seconds.

    `clock` returns the current time in seconds (injectable for tests). get(key) returns the
    cached value while less than `ttl` seconds have passed since it was fetched; otherwise
    it calls fetch(key) again and stores the new value.
    """

    def __init__(
        self, fetch: Callable[[str], Any], ttl: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        raise NotImplementedError

    def get(self, key: str) -> Any:
        raise NotImplementedError


def mask(text: str, secrets: list[str]) -> str:
    """Replace every occurrence of each secret value in `text` with "***".

    Ignore empty secrets. When one secret contains another, mask the longer one first.
    """
    raise NotImplementedError
