# Cloud Fundamentals and IAM
"""
Cloud basics you need before touching any SDK.

Geography
- REGION: a geographic area (us-east-1, eu-west-1) made of several independent data centre
  groups. Data and resources live in ONE region unless you copy them. Pick a region close to
  users, with the services you need, and respecting data-residency law.
- AVAILABILITY ZONE (AZ): one or more isolated data centres inside a region (us-east-1a,
  1b ...). Spread replicas over >= 2 AZs to survive a data-centre failure.

Shared responsibility model
- The provider secures the cloud: hardware, hypervisor, physical network, managed-service
  internals.
- YOU secure what you put in it: IAM, data, encryption choices, network rules, OS patches on
  EC2, application code, who can read your bucket.

IAM (Identity and Access Management)
- USER: a long-lived identity (avoid for apps; prefer SSO for humans).
- ROLE: an identity with NO permanent credentials; something (a Lambda, an ECS task, a person
  via SSO) ASSUMES it and receives short-lived credentials from STS.
- POLICY: a JSON document: Statements of Effect (Allow/Deny), Action, Resource, Condition.
- Identity policies attach to users/roles; resource policies attach to buckets/queues;
  a role also has a TRUST policy saying who may assume it.

Policy evaluation (simplified)
    1. An explicit Deny anywhere always wins.
    2. Otherwise an explicit Allow is needed.
    3. Otherwise: implicit deny (everything is denied by default).
(SCPs and permission boundaries can only further restrict; this lesson ignores them.)

Credential chain (boto3 looks in this order): explicit args -> env vars -> shared config /
SSO profile -> container (ECS task role) / EC2 instance profile / Lambda role. Code should
NEVER pass keys; let the chain find the role.

Example below: build policy documents in Python, lint them, evaluate them with a small
evaluator, then create a role under moto (a fake AWS in memory; no network, no account).

Common mistakes
- `"Action": "*"` or `"Resource": "*"` "to make it work" (admin by accident).
- Using the root account or long-lived access keys for apps; committing keys to git.
- Forgetting s3 needs TWO resource ARNs: the bucket (ListBucket) and `bucket/*` (objects).
- Trust policy too broad (`"Principal": {"AWS": "*"}`) so anyone can assume the role.
- Assuming a policy change is instant everywhere; IAM is eventually consistent.

Production notes
- Start from zero permissions, add what CloudTrail / Access Analyzer says is used.
- Humans: IAM Identity Center (SSO) + MFA. Workloads: roles. CI: OIDC (see m_11).
- Tag resources and use Condition keys (aws:PrincipalTag, aws:RequestedRegion) to scope.
- Turn on CloudTrail in all regions and send it to a locked-down bucket.

Cost notes
- IAM and STS are free. CloudTrail's first management-event trail is free; data events and
  extra trails cost. Multi-AZ doubles some resources (databases, NAT gateways): decide
  deliberately.
"""

import json
import os
from fnmatch import fnmatchcase
from typing import Any
from unittest.mock import patch

import boto3
from moto import mock_aws

FAKE_AWS_ENV = {
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "AWS_SESSION_TOKEN": "testing",
    "AWS_DEFAULT_REGION": "us-east-1",
}

type Policy = dict[str, Any]


# Example 1: build policy documents (least privilege)
def statement(
    effect: str, actions: list[str], resources: list[str], sid: str | None = None
) -> dict[str, Any]:
    st: dict[str, Any] = {"Effect": effect, "Action": actions, "Resource": resources}
    if sid:
        st["Sid"] = sid
    return st


def policy_document(statements: list[dict[str, Any]]) -> Policy:
    return {"Version": "2012-10-17", "Statement": statements}


def s3_read_only(bucket: str, prefix: str = "") -> Policy:
    """Read objects under `prefix` only; listing is allowed on the bucket."""
    return policy_document(
        [
            statement(
                "Allow", ["s3:GetObject"], [f"arn:aws:s3:::{bucket}/{prefix}*"], "ReadObjects"
            ),
            statement("Allow", ["s3:ListBucket"], [f"arn:aws:s3:::{bucket}"], "ListBucket"),
        ]
    )


def assume_role_policy(service: str) -> Policy:
    """Trust policy: only this AWS service (e.g. lambda.amazonaws.com) may assume the role."""
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": service},
                "Action": "sts:AssumeRole",
            }
        ],
    }


# Example 2: lint a policy for risky wildcards
def _as_list(value: str | list[str]) -> list[str]:
    return [value] if isinstance(value, str) else list(value)


def lint_policy(policy: Policy) -> list[str]:
    findings: list[str] = []
    for i, st in enumerate(policy.get("Statement", [])):
        if st.get("Effect") != "Allow":
            continue
        if any(a == "*" for a in _as_list(st.get("Action", []))):
            findings.append(f"statement {i}: Action '*' grants every API call")
        if any(r == "*" for r in _as_list(st.get("Resource", []))):
            findings.append(f"statement {i}: Resource '*' applies to every resource")
    return findings


# Example 3: a tiny policy evaluator (explicit deny > allow > implicit deny)
def _matches(patterns: str | list[str], value: str) -> bool:
    return any(fnmatchcase(value.lower(), p.lower()) for p in _as_list(patterns))


def evaluate(policies: list[Policy], action: str, resource: str) -> str:
    """Return 'ExplicitDeny', 'Allow' or 'ImplicitDeny'. Conditions are NOT evaluated."""
    allowed = False
    for policy in policies:
        for st in policy.get("Statement", []):
            if _matches(st.get("Action", []), action) and _matches(
                st.get("Resource", []), resource
            ):
                if st["Effect"] == "Deny":
                    return "ExplicitDeny"
                allowed = True
    return "Allow" if allowed else "ImplicitDeny"


# Example 4: create a role under moto and use STS
def create_app_role(iam: Any, name: str, policy: Policy) -> str:
    iam.create_role(
        RoleName=name,
        AssumeRolePolicyDocument=json.dumps(assume_role_policy("lambda.amazonaws.com")),
    )
    created = iam.create_policy(PolicyName=f"{name}-policy", PolicyDocument=json.dumps(policy))
    arn = created["Policy"]["Arn"]
    iam.attach_role_policy(RoleName=name, PolicyArn=arn)
    return arn


if __name__ == "__main__":
    policy = s3_read_only("reports-bucket", "public/")
    print("policy:", json.dumps(policy)[:80], "...")
    print("lint(clean):", lint_policy(policy))
    print("lint(bad):", lint_policy(policy_document([statement("Allow", ["*"], ["*"])])))

    deny_secret = policy_document(
        [statement("Deny", ["s3:GetObject"], ["arn:aws:s3:::reports-bucket/public/secret*"])]
    )
    for key in ("public/a.csv", "public/secret.txt", "private/b.csv"):
        res = f"arn:aws:s3:::reports-bucket/{key}"
        print(f"{key}: {evaluate([policy, deny_secret], 's3:GetObject', res)}")

    with patch.dict(os.environ, FAKE_AWS_ENV), mock_aws():
        iam = boto3.client("iam")
        arn = create_app_role(iam, "report-reader", policy)
        print("policy arn:", arn)
        print(
            "attached:",
            [
                p["PolicyName"]
                for p in iam.list_attached_role_policies(RoleName="report-reader")[
                    "AttachedPolicies"
                ]
            ],
        )
        sts = boto3.client("sts")
        print("caller:", sts.get_caller_identity()["Arn"])
