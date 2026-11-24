import pytest

boto3 = pytest.importorskip("boto3")
from botocore.exceptions import ClientError  # noqa: E402
from moto import mock_aws  # noqa: E402

from _loader import load  # noqa: E402

ex = load("t05_cloud_engineering", "ex_13_secrets_management")


@pytest.fixture
def aws(monkeypatch):
    for key, value in {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": "us-east-1",
    }.items():
        monkeypatch.setenv(key, value)
    with mock_aws():
        yield {
            "sm": boto3.client("secretsmanager", region_name="us-east-1"),
            "ssm": boto3.client("ssm", region_name="us-east-1"),
        }


def test_create_then_update_secret_adds_versions(aws):
    sm = aws["sm"]
    v1 = ex.create_or_update_secret(sm, "app/db", {"password": "one"})
    v2 = ex.create_or_update_secret(sm, "app/db", {"password": "two"})
    assert v1 and v2 and v1 != v2
    assert ex.get_secret_json(sm, "app/db") == {"password": "two"}
    assert ex.get_secret_json(sm, "app/db", "AWSPREVIOUS") == {"password": "one"}


def test_get_secret_json_missing_raises(aws):
    with pytest.raises(ClientError) as info:
        ex.get_secret_json(aws["sm"], "nope")
    assert info.value.response["Error"]["Code"] == "ResourceNotFoundException"


def test_get_parameters_by_path_relative_names_and_decryption(aws):
    ssm = aws["ssm"]
    ssm.put_parameter(Name="/app/prod/db_host", Value="db.local", Type="String")
    ssm.put_parameter(Name="/app/prod/db/password", Value="s3cret", Type="SecureString")
    ssm.put_parameter(Name="/app/dev/db_host", Value="other", Type="String")
    assert ex.get_parameters_by_path(ssm, "/app/prod") == {
        "db_host": "db.local",
        "db/password": "s3cret",
    }
    assert ex.get_parameters_by_path(ssm, "/app/prod/") == {
        "db_host": "db.local",
        "db/password": "s3cret",
    }
    assert ex.get_parameters_by_path(ssm, "/nothing") == {}


def test_get_parameters_by_path_many_parameters(aws):
    ssm = aws["ssm"]
    for i in range(25):  # more than one page of 10
        ssm.put_parameter(Name=f"/big/p{i:02d}", Value=str(i), Type="String")
    assert len(ex.get_parameters_by_path(ssm, "/big")) == 25


def test_ttl_cache_hits_and_expiry():
    now = [100.0]
    calls = []

    def fetch(key):
        calls.append(key)
        return f"{key}-v{len(calls)}"

    cache = ex.TTLCache(fetch, ttl=60, clock=lambda: now[0])
    assert cache.get("a") == "a-v1"
    now[0] = 159.9
    assert cache.get("a") == "a-v1"  # still fresh
    assert calls == ["a"]
    now[0] = 160.0
    assert cache.get("a") == "a-v2"  # expired exactly at ttl
    assert cache.get("b") == "b-v3"  # keys are independent
    assert calls == ["a", "a", "b"]


def test_mask():
    assert ex.mask("password=hunter2 ok", ["hunter2"]) == "password=*** ok"
    assert ex.mask("a hunter2 b hunter2", ["hunter2"]) == "a *** b ***"
    assert ex.mask("nothing here", ["", "zzz"]) == "nothing here"
    # longer secret first so no fragment of it leaks
    assert ex.mask("token=abcdef", ["abc", "abcdef"]) == "token=***"
