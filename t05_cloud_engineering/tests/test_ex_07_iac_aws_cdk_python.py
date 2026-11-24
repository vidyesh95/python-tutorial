import copy

import pytest

from _loader import load

ex = load("t05_cloud_engineering", "ex_07_iac_aws_cdk_python")


def test_resource_name_ok():
    assert ex.resource_name("dev", "ingest", "uploads") == "dev-ingest-uploads"
    assert ex.resource_name("prod", "api-v2", "bucket-1") == "prod-api-v2-bucket-1"


@pytest.mark.parametrize(
    "args",
    [
        ("test", "svc", "x"),  # unknown env
        ("dev", "Svc", "x"),  # uppercase
        ("dev", "svc_a", "x"),  # underscore
        ("dev", "svc", ""),  # empty
        ("dev", "-svc", "x"),  # leading hyphen
        ("dev", "svc", "a" * 60),  # too long
    ],
)
def test_resource_name_rejects(args):
    with pytest.raises(ValueError):
        ex.resource_name(*args)


def test_standard_tags():
    assert ex.standard_tags("dev", "team-a", "cc-1") == {
        "owner": "team-a",
        "env": "dev",
        "cost-center": "cc-1",
        "managed-by": "cdk",
    }
    with pytest.raises(ValueError):
        ex.standard_tags("qa", "team-a", "cc-1")


def test_missing_tags():
    assert ex.missing_tags(ex.standard_tags("dev", "o", "c")) == []
    assert ex.missing_tags({"owner": "o", "env": ""}) == ["env", "cost-center"]
    assert ex.missing_tags({"a": "1"}, required=("a", "b")) == ["b"]


def test_synth_bucket_template_secure_defaults():
    tags = {"owner": "o", "env": "dev"}
    t = ex.synth_bucket_template("Uploads", "dev-x-uploads", True, tags)
    assert t["AWSTemplateFormatVersion"] == "2010-09-09"
    res = t["Resources"]["Uploads"]
    assert res["Type"] == "AWS::S3::Bucket"
    props = res["Properties"]
    assert props["BucketName"] == "dev-x-uploads"
    assert props["VersioningConfiguration"] == {"Status": "Enabled"}
    assert props["Tags"] == [{"Key": "env", "Value": "dev"}, {"Key": "owner", "Value": "o"}]
    sse = props["BucketEncryption"]["ServerSideEncryptionConfiguration"][0]
    assert sse["ServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256"
    assert props["PublicAccessBlockConfiguration"] == {
        "BlockPublicAcls": True,
        "BlockPublicPolicy": True,
        "IgnorePublicAcls": True,
        "RestrictPublicBuckets": True,
    }


def test_synth_bucket_template_unversioned_omits_key():
    t = ex.synth_bucket_template("B", "n", False, {})
    assert "VersioningConfiguration" not in t["Resources"]["B"]["Properties"]


def test_unprotected_buckets():
    good = ex.synth_bucket_template("Good", "g", False, {})
    assert ex.unprotected_buckets(good) == []

    bad = copy.deepcopy(good)
    bad["Resources"]["Bad"] = {"Type": "AWS::S3::Bucket", "Properties": {"BucketName": "b"}}
    partial = copy.deepcopy(good["Resources"]["Good"])
    partial["Properties"]["PublicAccessBlockConfiguration"]["RestrictPublicBuckets"] = False
    bad["Resources"]["Partial"] = partial
    bad["Resources"]["Queue"] = {"Type": "AWS::SQS::Queue", "Properties": {}}
    assert ex.unprotected_buckets(bad) == ["Bad", "Partial"]
