import pytest

pytest.importorskip("google.cloud.storage")
from google.api_core.exceptions import NotFound  # noqa: E402

from _loader import load  # noqa: E402

ex = load("t05_cloud_engineering", "ex_06_google_cloud_sdk")


class FakeBlob:
    def __init__(self, store, bucket, name):
        self.store, self.bucket, self.name = store, bucket, name

    def upload_from_string(self, data, content_type="text/plain"):
        self.store[(self.bucket, self.name)] = (data, content_type)

    def download_as_text(self):
        try:
            return self.store[(self.bucket, self.name)][0]
        except KeyError:
            raise NotFound("missing") from None


class FakeBucket:
    def __init__(self, store, name):
        self.store, self.name = store, name

    def blob(self, name):
        return FakeBlob(self.store, self.name, name)


class FakeClient:
    def __init__(self):
        self.store = {}

    def bucket(self, name):
        return FakeBucket(self.store, name)

    def list_blobs(self, bucket_or_name, prefix=None):
        return iter(
            [
                FakeBlob(self.store, b, n)
                for (b, n) in sorted(self.store)
                if b == bucket_or_name and n.startswith(prefix or "")
            ]
        )


@pytest.fixture
def client():
    return FakeClient()


def test_choose_auth_method_order():
    assert ex.choose_auth_method({}) == "gcloud_user_adc"
    assert ex.choose_auth_method({"K_SERVICE": "api"}) == "attached_service_account"
    assert ex.choose_auth_method({"KUBERNETES_SERVICE_HOST": "10.0.0.1"}) == (
        "attached_service_account"
    )
    both = {"GOOGLE_APPLICATION_CREDENTIALS": "/k.json", "K_SERVICE": "api"}
    assert ex.choose_auth_method(both) == "service_account_key_file"
    assert ex.choose_auth_method({"GOOGLE_APPLICATION_CREDENTIALS": ""}) == "gcloud_user_adc"


def test_upload_and_download_roundtrip(client):
    assert ex.upload_text(client, "b", "x/y.txt", "hello") == "gs://b/x/y.txt"
    assert client.store[("b", "x/y.txt")] == ("hello", "text/plain")
    assert ex.download_text(client, "b", "x/y.txt") == "hello"


def test_download_missing_is_none(client):
    assert ex.download_text(client, "b", "nope") is None


def test_list_names_prefix(client):
    for name in ("logs/1", "logs/2", "data/1"):
        ex.upload_text(client, "b", name, "x")
    ex.upload_text(client, "other", "logs/9", "x")
    assert ex.list_names(client, "b", "logs/") == ["logs/1", "logs/2"]
    assert ex.list_names(client, "b") == ["data/1", "logs/1", "logs/2"]
    assert ex.list_names(client, "b", "zzz") == []


def test_parse_gs_uri():
    assert ex.parse_gs_uri("gs://my-bucket/a/b.txt") == ("my-bucket", "a/b.txt")
    for bad in ("s3://b/k", "gs://bucket", "gs://bucket/", "gs:///k", "http://x/y"):
        with pytest.raises(ValueError):
            ex.parse_gs_uri(bad)
