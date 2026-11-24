# Google Cloud SDK and Python Clients
"""
Google Cloud (GCP) has the same building blocks as AWS under different names:
    object storage  Cloud Storage (GCS)      ~ S3
    queues/pub-sub  Pub/Sub                  ~ SQS + SNS
    containers      Cloud Run                ~ Fargate / App Runner (scale to zero!)
    secrets         Secret Manager           ~ Secrets Manager
    identity        IAM + service accounts   ~ IAM roles
    logs/metrics    Cloud Logging/Monitoring ~ CloudWatch
Hierarchy: Organization > Folders > PROJECT > resources. The project is the unit of
billing, IAM and quotas; you pass a project id to almost every client.

Authentication: Application Default Credentials (ADC)
Client libraries call `google.auth.default()` and find credentials automatically, in order:
    1. `GOOGLE_APPLICATION_CREDENTIALS` env var -> a service-account key FILE (avoid: a
       long-lived secret on disk)
    2. `gcloud auth application-default login` -> YOUR user credentials (local dev)
    3. The attached SERVICE ACCOUNT of the runtime (Cloud Run, GKE Workload Identity, GCE)
       via the metadata server. This is the right answer in production: no keys at all.
Your code stays identical across all three, like the boto3 credential chain (m_01).

Service accounts are the workload identity. Grant each one only the roles it needs, ideally a
role bound to ONE bucket (`roles/storage.objectViewer` on the bucket), never `roles/owner`
or `roles/editor` on the project.

Cloud Storage client: `storage.Client()` -> `client.bucket(name).blob(key)` ->
`blob.upload_from_string(...)`, `blob.download_as_text()`, `client.list_blobs(bucket,
prefix=...)`. A missing object raises `google.api_core.exceptions.NotFound`.

Pub/Sub (`google-cloud-pubsub`, not installed here): `publisher.publish(topic_path, data=bytes,
**attributes)` returns a future; subscribers PULL messages and must `ack` them (like SQS delete);
unacked messages are redelivered after the ack deadline. Dead-letter topics and idempotent
handlers apply exactly as in m_04.

Cloud Run (see m_12): deploy a container (`gcloud run deploy --source .` or an image from
Artifact Registry). It listens on `$PORT`, scales 0..N by request concurrency, bills per
100 ms of CPU while handling requests.

Design for testability: depend on a small Protocol, inject the client, and unit-test with an
in-memory fake (below). Real GCP is only touched when GOOGLE_CLOUD_PROJECT is set.

Common mistakes
- Committing or baking a service-account JSON key; keys do not expire by default.
- `roles/editor`/`roles/owner` for an app service account.
- Forgetting to enable the API (`gcloud services enable storage.googleapis.com`).
- Mixing up project id (my-proj-123) and project number or display name.
- Creating a client per request (reuse it; clients hold connection pools).

Production notes
- Prefer Workload Identity / attached service accounts; for CI use Workload Identity
  Federation (OIDC, m_11) instead of keys.
- Use uniform bucket-level access, set a region, and apply lifecycle rules.
- Impersonate service accounts (`gcloud ... --impersonate-service-account`) for admin tasks.

Cost notes
- GCS: storage per GB-month by class, operations, and egress; Cloud Run has a monthly free
  tier (requests/CPU/memory) and scales to zero; Pub/Sub has a free 10 GB/month.
- Set budgets and alerts per project; delete test projects to stop all charges.
"""

import os
from collections.abc import Iterator, Mapping
from typing import Protocol

from google.api_core.exceptions import NotFound


class BlobLike(Protocol):
    name: str

    def upload_from_string(self, data: str, content_type: str = ...) -> None: ...
    def download_as_text(self) -> str: ...


class BucketLike(Protocol):
    def blob(self, name: str) -> BlobLike: ...


class StorageClientLike(Protocol):
    def bucket(self, name: str) -> BucketLike: ...
    def list_blobs(self, bucket_or_name: str, prefix: str | None = ...) -> Iterator[BlobLike]: ...


# --- in-memory fake used by this lesson and by the tests ---
class FakeBlob:
    def __init__(self, store: dict[tuple[str, str], str], bucket: str, name: str) -> None:
        self._store, self._bucket, self.name = store, bucket, name

    def upload_from_string(self, data: str, content_type: str = "text/plain") -> None:
        self._store[(self._bucket, self.name)] = data

    def download_as_text(self) -> str:
        try:
            return self._store[(self._bucket, self.name)]
        except KeyError:
            raise NotFound(f"gs://{self._bucket}/{self.name}") from None


class FakeBucket:
    def __init__(self, store: dict[tuple[str, str], str], name: str) -> None:
        self._store, self.name = store, name

    def blob(self, name: str) -> FakeBlob:
        return FakeBlob(self._store, self.name, name)


class FakeStorageClient:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}

    def bucket(self, name: str) -> FakeBucket:
        return FakeBucket(self.store, name)

    def list_blobs(self, bucket_or_name: str, prefix: str | None = None) -> Iterator[FakeBlob]:
        for bucket, name in sorted(self.store):
            if bucket == bucket_or_name and name.startswith(prefix or ""):
                yield FakeBlob(self.store, bucket, name)


# Example 1: which ADC source will be used? (pure function, easy to test)
def choose_auth_method(env: Mapping[str, str]) -> str:
    if env.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return "service_account_key_file"  # works, but a long-lived secret: avoid
    if env.get("K_SERVICE") or env.get("KUBERNETES_SERVICE_HOST"):
        return "attached_service_account"  # Cloud Run / GKE: keyless, preferred
    return "gcloud_user_adc"  # local dev: `gcloud auth application-default login`


# Example 2: code against the Protocol, not the real client
def upload_text(client: StorageClientLike, bucket: str, name: str, text: str) -> str:
    client.bucket(bucket).blob(name).upload_from_string(text, content_type="text/plain")
    return f"gs://{bucket}/{name}"


def download_text(client: StorageClientLike, bucket: str, name: str) -> str | None:
    try:
        return client.bucket(bucket).blob(name).download_as_text()
    except NotFound:
        return None


def list_names(client: StorageClientLike, bucket: str, prefix: str = "") -> list[str]:
    return [blob.name for blob in client.list_blobs(bucket, prefix=prefix)]


# Example 3: Pub/Sub publish against an injected publisher (real one: pubsub_v1.PublisherClient)
class PublisherLike(Protocol):
    def publish(self, topic: str, data: bytes, **attributes: str) -> object: ...


def publish_event(publisher: PublisherLike, topic_path: str, payload: str, kind: str) -> None:
    publisher.publish(topic_path, payload.encode(), kind=kind)  # attributes must be strings


class FakePublisher:
    def __init__(self) -> None:
        self.sent: list[tuple[str, bytes, dict[str, str]]] = []

    def publish(self, topic: str, data: bytes, **attributes: str) -> None:
        self.sent.append((topic, data, attributes))


def real_gcs_demo(project: str) -> None:
    """Runs ONLY when GOOGLE_CLOUD_PROJECT is set (needs ADC and network)."""
    import google.auth
    from google.cloud import storage

    credentials, detected_project = google.auth.default()  # walks the ADC chain
    print("ADC project:", detected_project, "| credential type:", type(credentials).__name__)
    client = storage.Client(project=project)
    for bucket in client.list_buckets(max_results=5):
        print("bucket:", bucket.name)


if __name__ == "__main__":
    print("auth (laptop):", choose_auth_method({}))
    print("auth (key file):", choose_auth_method({"GOOGLE_APPLICATION_CREDENTIALS": "/x.json"}))
    print("auth (Cloud Run):", choose_auth_method({"K_SERVICE": "api"}))

    fake = FakeStorageClient()
    print("uploaded:", upload_text(fake, "demo-bucket", "reports/a.txt", "hello"))
    upload_text(fake, "demo-bucket", "reports/b.txt", "world")
    upload_text(fake, "demo-bucket", "other/c.txt", "!")
    print("download:", download_text(fake, "demo-bucket", "reports/a.txt"))
    print("missing:", download_text(fake, "demo-bucket", "nope.txt"))
    print("list:", list_names(fake, "demo-bucket", "reports/"))

    pub = FakePublisher()
    publish_event(pub, "projects/demo/topics/orders", '{"id": 1}', "order.created")
    print("published:", pub.sent)

    if project := os.getenv("GOOGLE_CLOUD_PROJECT"):
        real_gcs_demo(project)
    else:
        print("GOOGLE_CLOUD_PROJECT not set: skipping real Google Cloud calls")
