"""Exercise 07: pure-Python IaC helpers: naming, tags, a synthesized template, a policy check.

No AWS or CDK needed. Real CDK code lives in `iac/cdk_app.py` (read it, do not run it).

Tasks
1. resource_name: enforce a naming convention.
2. standard_tags / missing_tags: mandatory cost-allocation tags.
3. synth_bucket_template: CloudFormation-style dict for a secure S3 bucket.
4. unprotected_buckets: flag buckets without full Public Access Block.

Run: uv run pytest t05_cloud_engineering -k iac_aws_cdk
"""

import re  # noqa: F401  (handy for task 1)
from typing import Any

ENVIRONMENTS = {"dev", "staging", "prod"}
REQUIRED_TAGS = ("owner", "env", "cost-center")


def resource_name(env: str, service: str, resource: str) -> str:
    """Return f"{env}-{service}-{resource}".

    Raise ValueError if env is not in ENVIRONMENTS, if any part is not lowercase
    letters/digits with single inner hyphens (regex [a-z0-9]+(-[a-z0-9]+)*), or if the final
    name is longer than 63 characters.
    """
    raise NotImplementedError


def standard_tags(env: str, owner: str, cost_center: str) -> dict[str, str]:
    """Return {"owner": owner, "env": env, "cost-center": cost_center, "managed-by": "cdk"}.

    Raise ValueError if env is not in ENVIRONMENTS.
    """
    raise NotImplementedError


def missing_tags(tags: dict[str, str], required: tuple[str, ...] = REQUIRED_TAGS) -> list[str]:
    """Return the required keys that are absent OR have an empty value, in `required` order."""
    raise NotImplementedError


def synth_bucket_template(
    logical_id: str, bucket_name: str, versioned: bool, tags: dict[str, str]
) -> dict[str, Any]:
    """Return a CloudFormation template dict:

    {"AWSTemplateFormatVersion": "2010-09-09",
     "Resources": {logical_id: {"Type": "AWS::S3::Bucket", "Properties": {...}}}}

    Properties: BucketName; BucketEncryption with SSE AES256
    ({"ServerSideEncryptionConfiguration": [{"ServerSideEncryptionByDefault":
    {"SSEAlgorithm": "AES256"}}]}); PublicAccessBlockConfiguration with BlockPublicAcls,
    BlockPublicPolicy, IgnorePublicAcls and RestrictPublicBuckets all True; Tags as
    [{"Key": k, "Value": v}] sorted by key; and VersioningConfiguration {"Status": "Enabled"}
    ONLY when `versioned` is true (omit the key otherwise).
    """
    raise NotImplementedError


def unprotected_buckets(template: dict[str, Any]) -> list[str]:
    """Return the sorted logical ids of AWS::S3::Bucket resources whose
    Properties.PublicAccessBlockConfiguration does not have all four flags set to True
    (missing config counts as unprotected). Other resource types are ignored.
    """
    raise NotImplementedError
