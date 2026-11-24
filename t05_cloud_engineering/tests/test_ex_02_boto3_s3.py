import pytest

boto3 = pytest.importorskip("boto3")
from botocore.config import Config  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402
from moto import mock_aws  # noqa: E402

from _loader import load  # noqa: E402

ex = load("t05_cloud_engineering", "ex_02_boto3_s3")

BUCKET = "test-bucket"


@pytest.fixture
def s3(monkeypatch):
    for key, value in {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": "us-east-1",
    }.items():
        monkeypatch.setenv(key, value)
    with mock_aws():
        client = boto3.client(
            "s3", region_name="us-east-1", config=Config(signature_version="s3v4")
        )
        client.create_bucket(Bucket=BUCKET)
        yield client


def test_put_and_get_json_roundtrip(s3):
    ex.put_json(s3, BUCKET, "a.json", {"n": 1, "tags": ["x"]})
    assert ex.get_json(s3, BUCKET, "a.json") == {"n": 1, "tags": ["x"]}
    assert s3.head_object(Bucket=BUCKET, Key="a.json")["ContentType"] == "application/json"


def test_get_json_missing_key_is_none(s3):
    assert ex.get_json(s3, BUCKET, "nope.json") is None


def test_get_json_other_errors_propagate(s3):
    with pytest.raises(ClientError) as info:
        ex.get_json(s3, "no-such-bucket", "a.json")
    assert info.value.response["Error"]["Code"] == "NoSuchBucket"


def test_list_keys_prefix_and_empty(s3):
    for key in ("logs/1", "logs/2", "data/1"):
        s3.put_object(Bucket=BUCKET, Key=key, Body=b"x")
    assert sorted(ex.list_keys(s3, BUCKET, "logs/")) == ["logs/1", "logs/2"]
    assert ex.list_keys(s3, BUCKET, "zzz/") == []
    assert sorted(ex.list_keys(s3, BUCKET)) == ["data/1", "logs/1", "logs/2"]


def test_list_keys_handles_more_than_one_page(s3):
    for i in range(1005):
        s3.put_object(Bucket=BUCKET, Key=f"bulk/{i:04d}", Body=b"")
    assert len(ex.list_keys(s3, BUCKET, "bulk/")) == 1005


def test_presign_get(s3):
    url = ex.presign_get(s3, BUCKET, "a.json", 120)
    assert BUCKET in url and "a.json" in url
    assert "X-Amz-Expires=120" in url
    assert "X-Amz-Expires=300" in ex.presign_get(s3, BUCKET, "a.json")


def test_plan_parts():
    assert ex.plan_parts(10, 4) == [(1, 0, 4), (2, 4, 8), (3, 8, 10)]
    assert ex.plan_parts(8, 4) == [(1, 0, 4), (2, 4, 8)]
    assert ex.plan_parts(0, 4) == []
    with pytest.raises(ValueError):
        ex.plan_parts(10, 0)
