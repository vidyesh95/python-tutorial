"""Exercise 06: Google Cloud Storage code written against an injected client.

Tests pass an in-memory fake with the same surface as `google.cloud.storage.Client`:
`client.bucket(name).blob(key)` with `upload_from_string(data, content_type=...)`,
`download_as_text()` (raises `google.api_core.exceptions.NotFound` if missing), and
`client.list_blobs(bucket_name, prefix=...)` yielding objects with a `.name`.

Tasks
1. choose_auth_method: which Application Default Credentials source applies?
2. upload_text / download_text: round-trip text; missing object -> None.
3. list_names: object names under a prefix.
4. parse_gs_uri: split "gs://bucket/path/to/obj" into (bucket, name).

Run: uv run pytest t05_cloud_engineering -k google_cloud_sdk
"""

from collections.abc import Mapping
from typing import Any

from google.api_core.exceptions import NotFound


def choose_auth_method(env: Mapping[str, str]) -> str:
    """Return which credential source ADC would use, checking in this order:

    - env has a non-empty GOOGLE_APPLICATION_CREDENTIALS -> "service_account_key_file"
    - env has K_SERVICE (Cloud Run) or KUBERNETES_SERVICE_HOST (GKE) -> "attached_service_account"
    - otherwise -> "gcloud_user_adc"
    """
    if env.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return "service_account_key_file"
    if env.get("K_SERVICE") or env.get("KUBERNETES_SERVICE_HOST"):
        return "attached_service_account"
    return "gcloud_user_adc"


def upload_text(client: Any, bucket: str, name: str, text: str) -> str:
    """Upload `text` (content_type="text/plain") and return its URI f"gs://{bucket}/{name}"."""
    client.bucket(bucket).blob(name).upload_from_string(text, content_type="text/plain")
    return f"gs://{bucket}/{name}"


def download_text(client: Any, bucket: str, name: str) -> str | None:
    """Return the object's text, or None if it does not exist (catch NotFound)."""
    try:
        return client.bucket(bucket).blob(name).download_as_text()
    except NotFound:
        return None


def list_names(client: Any, bucket: str, prefix: str = "") -> list[str]:
    """Return the names of objects whose name starts with `prefix`, in the client's order."""
    return [blob.name for blob in client.list_blobs(bucket, prefix=prefix)]


def parse_gs_uri(uri: str) -> tuple[str, str]:
    """Split "gs://my-bucket/a/b.txt" into ("my-bucket", "a/b.txt").

    Raise ValueError if the scheme is not gs://, the bucket is empty, or the object name is
    empty (e.g. "gs://bucket" or "gs://bucket/").
    """
    if not uri.startswith("gs://"):
        raise ValueError(f"not a gs:// URI: {uri!r}")
    bucket, _, name = uri.removeprefix("gs://").partition("/")
    if not bucket or not name:
        raise ValueError(f"missing bucket or object name: {uri!r}")
    return bucket, name
