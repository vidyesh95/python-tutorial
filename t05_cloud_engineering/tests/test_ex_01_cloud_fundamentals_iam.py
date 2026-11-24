import json

import pytest

boto3 = pytest.importorskip("boto3")
from moto import mock_aws  # noqa: E402

from _loader import load  # noqa: E402

ex = load("t05_cloud_engineering", "ex_01_cloud_fundamentals_iam")


@pytest.fixture
def iam(monkeypatch):
    for key, value in {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": "us-east-1",
    }.items():
        monkeypatch.setenv(key, value)
    with mock_aws():
        yield boto3.client("iam", region_name="us-east-1")


def test_s3_read_only_policy_shape():
    doc = ex.s3_read_only_policy("data", "reports/")
    assert doc["Version"] == "2012-10-17"
    assert len(doc["Statement"]) == 2
    by_action = {tuple(s["Action"]): s for s in doc["Statement"]}
    assert by_action[("s3:GetObject",)]["Resource"] == ["arn:aws:s3:::data/reports/*"]
    assert by_action[("s3:ListBucket",)]["Resource"] == ["arn:aws:s3:::data"]
    assert all(s["Effect"] == "Allow" for s in doc["Statement"])


def test_clean_policy_has_no_risks():
    assert ex.find_wildcard_risks(ex.s3_read_only_policy("data", "x/")) == []


def test_wildcards_flagged():
    bad = {"Statement": [{"Effect": "Allow", "Action": "*", "Resource": ["*"]}]}
    assert len(ex.find_wildcard_risks(bad)) >= 1
    only_resource = {
        "Statement": [{"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": "*"}]
    }
    assert len(ex.find_wildcard_risks(only_resource)) == 1


def test_deny_wildcard_not_risky():
    deny = {"Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}]}
    assert ex.find_wildcard_risks(deny) == []


def test_is_allowed_basic_and_implicit_deny():
    policy = ex.s3_read_only_policy("data", "reports/")
    assert ex.is_allowed([policy], "s3:GetObject", "arn:aws:s3:::data/reports/a.csv")
    assert not ex.is_allowed([policy], "s3:GetObject", "arn:aws:s3:::data/other/a.csv")
    assert not ex.is_allowed([policy], "s3:PutObject", "arn:aws:s3:::data/reports/a.csv")


def test_explicit_deny_wins():
    allow = {"Statement": [{"Effect": "Allow", "Action": "s3:*", "Resource": "*"}]}
    deny = {
        "Statement": [
            {"Effect": "Deny", "Action": ["s3:DeleteObject"], "Resource": ["arn:aws:s3:::data/*"]}
        ]
    }
    assert ex.is_allowed([allow, deny], "s3:GetObject", "arn:aws:s3:::data/a")
    assert not ex.is_allowed([allow, deny], "s3:DeleteObject", "arn:aws:s3:::data/a")
    assert not ex.is_allowed([deny, allow], "s3:DeleteObject", "arn:aws:s3:::data/a")


def test_create_managed_policy(iam):
    doc = ex.s3_read_only_policy("data", "reports/")
    arn = ex.create_managed_policy(iam, "reader", doc)
    assert arn.startswith("arn:aws:iam::") and arn.endswith(":policy/reader")
    stored = iam.get_policy_version(PolicyArn=arn, VersionId="v1")["PolicyVersion"]["Document"]
    assert json.loads(json.dumps(stored)) == doc
