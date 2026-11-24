"""Exercise 01: build, lint and evaluate IAM policy documents.

Tasks
1. s3_read_only_policy: least-privilege read policy for one bucket prefix.
2. find_wildcard_risks: report Allow statements that use '*' for Action or Resource.
3. is_allowed: evaluate policies (explicit Deny > Allow > implicit deny).
4. create_managed_policy: create the policy in IAM (boto3 client is passed in) and return its ARN.

Run: uv run pytest t05_cloud_engineering -k cloud_fundamentals_iam
"""

import json
from fnmatch import fnmatchcase
from typing import Any


def s3_read_only_policy(bucket: str, prefix: str) -> dict[str, Any]:
    """Return a policy document (Version "2012-10-17") with exactly two Allow statements:

    - Action ["s3:GetObject"] on [f"arn:aws:s3:::{bucket}/{prefix}*"]
    - Action ["s3:ListBucket"] on [f"arn:aws:s3:::{bucket}"]
    """
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/{prefix}*"],
            },
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{bucket}"],
            },
        ],
    }


def _as_list(value: str | list[str]) -> list[str]:
    return [value] if isinstance(value, str) else list(value)


def find_wildcard_risks(policy: dict[str, Any]) -> list[str]:
    """Return one message per risky Allow statement.

    A statement is risky if Action or Resource (string or list) contains exactly "*".
    Deny statements are never risky. Return [] for a clean policy. Messages are free-form but
    each risky statement must produce at least one message.
    """
    findings: list[str] = []
    for i, st in enumerate(policy.get("Statement", [])):
        if st.get("Effect") != "Allow":
            continue
        if "*" in _as_list(st.get("Action", [])):
            findings.append(f"statement {i}: Action '*'")
        if "*" in _as_list(st.get("Resource", [])):
            findings.append(f"statement {i}: Resource '*'")
    return findings


def _matches(patterns: str | list[str], value: str) -> bool:
    return any(fnmatchcase(value.lower(), p.lower()) for p in _as_list(patterns))


def is_allowed(policies: list[dict[str, Any]], action: str, resource: str) -> bool:
    """True only if some statement Allows (fnmatch-style `*` wildcards, case-insensitive for
    actions) and NO statement Denies. Ignore Condition. Statement Action/Resource may be a
    string or a list.
    """
    allowed = False
    for policy in policies:
        for st in policy.get("Statement", []):
            if _matches(st.get("Action", []), action) and _matches(
                st.get("Resource", []), resource
            ):
                if st["Effect"] == "Deny":
                    return False
                allowed = True
    return allowed


def create_managed_policy(iam: Any, name: str, policy: dict[str, Any]) -> str:
    """Create a customer-managed policy with iam.create_policy and return its ARN.

    PolicyDocument must be a JSON string (json.dumps).
    """
    resp = iam.create_policy(PolicyName=name, PolicyDocument=json.dumps(policy))
    return resp["Policy"]["Arn"]
