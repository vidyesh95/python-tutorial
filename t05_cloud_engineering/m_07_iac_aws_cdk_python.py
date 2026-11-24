# Infrastructure as Code with AWS CDK (Python)
"""
Infrastructure as Code (IaC) describes cloud resources in files you review, version and
re-apply, instead of clicking in a console. Benefits: repeatable environments, code review
for infra changes, drift detection, easy teardown.

AWS CDK lets you write that description in Python. Your program builds a TREE of objects;
`cdk synth` turns it into a CloudFormation template; CloudFormation creates/updates/deletes
the real resources.
    App                      the root; synthesizes to a cloud assembly
     └─ Stack                a deployable unit (= one CloudFormation stack)
         └─ Construct        a building block. Levels:
              L1 `CfnBucket`  1:1 with a CloudFormation resource (raw, all properties)
              L2 `s3.Bucket`  sensible defaults + helper methods (`bucket.grant_read(fn)`)
              L3 patterns     several resources together (e.g. load-balanced Fargate service)

Workflow (CLI is a Node program, your app is Python):
    cdk bootstrap   one-time per account/region: creates the staging bucket and roles
    cdk synth       print/produce the CloudFormation template (no AWS changes)
    cdk diff        compare your code with what is deployed  <- read this before every deploy
    cdk deploy      create/update the stack
    cdk destroy     delete it (RemovalPolicy.RETAIN resources are kept)

Passing configuration between stacks: reference one stack's construct property from another
(`bucket=storage_stack.bucket`) and CDK creates exports/imports; or pass plain values via
context (`-c env=prod`) and constructor arguments. Keep stacks small and ordered by
lifecycle (network/data stacks change rarely; app stacks often).

The real program is `iac/cdk_app.py` (NOT executed here: aws-cdk-lib is not installed). This
lesson shows the pure-Python parts of an IaC practice that you can test without a cloud:
naming conventions, mandatory tags, a tiny synth model, and a policy check on the output.

Common mistakes
- Skipping `cdk diff` and replacing a stateful resource (database, bucket) by renaming it:
  a changed logical ID means DELETE + CREATE. Keep logical IDs stable; use RETAIN for data.
- Hard-coding account ids/ARNs; use `Stack.of(self).account`, references, or context.
- Giving broad permissions with L1 resources instead of using `grant_*` helpers.
- Putting secrets in the template (they end up in CloudFormation in clear text): reference
  Secrets Manager (m_13) instead.
- One giant stack: slow deploys, 500-resource limit, large blast radius.
- Committing `cdk.out/` or leaving test stacks running.

Production notes
- Commit `cdk.context.json`; run `cdk synth` + tests + policy checks (cdk-nag) in CI (m_11).
- Use `cdk deploy` from a pipeline role assumed via OIDC, never from laptops, in prod.
- Test with the `assertions` module (`Template.from_stack(stack).has_resource_properties`).
- Enable termination protection for stateful production stacks.

Cost notes
- CDK and CloudFormation are free; the resources they create are not. Tag everything
  (`Tags.of(app).add("cost-center", ...)`) and `cdk destroy` sandbox stacks.
- NAT gateways, load balancers and idle databases are the usual surprise bills.
"""

import re
from pathlib import Path
from typing import Any

CDK_APP = Path(__file__).resolve().parent / "iac" / "cdk_app.py"
ENVIRONMENTS = {"dev", "staging", "prod"}
REQUIRED_TAGS = ("owner", "env", "cost-center")


# Example 1: naming convention
def resource_name(env: str, service: str, resource: str) -> str:
    if env not in ENVIRONMENTS:
        raise ValueError(f"env must be one of {sorted(ENVIRONMENTS)}")
    parts = [env, service, resource]
    for part in parts:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", part):
            raise ValueError(f"invalid name part {part!r}: use lowercase letters, digits, '-'")
    name = "-".join(parts)
    if len(name) > 63:  # S3 bucket / many AWS name limits
        raise ValueError("name longer than 63 characters")
    return name


# Example 2: mandatory tags
def standard_tags(env: str, owner: str, cost_center: str) -> dict[str, str]:
    if env not in ENVIRONMENTS:
        raise ValueError(f"env must be one of {sorted(ENVIRONMENTS)}")
    return {"owner": owner, "env": env, "cost-center": cost_center, "managed-by": "cdk"}


def missing_tags(tags: dict[str, str], required: tuple[str, ...] = REQUIRED_TAGS) -> list[str]:
    return [key for key in required if not tags.get(key)]


# Example 3: what `cdk synth` produces for a secure bucket (CloudFormation as a dict)
def synth_bucket_template(
    logical_id: str, bucket_name: str, versioned: bool, tags: dict[str, str]
) -> dict[str, Any]:
    props: dict[str, Any] = {
        "BucketName": bucket_name,
        "BucketEncryption": {
            "ServerSideEncryptionConfiguration": [
                {"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
            ]
        },
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True,
            "BlockPublicPolicy": True,
            "IgnorePublicAcls": True,
            "RestrictPublicBuckets": True,
        },
        "Tags": [{"Key": k, "Value": v} for k, v in sorted(tags.items())],
    }
    if versioned:
        props["VersioningConfiguration"] = {"Status": "Enabled"}
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {logical_id: {"Type": "AWS::S3::Bucket", "Properties": props}},
    }


# Example 4: policy-as-code check on a synthesized template (what cdk-nag does, in miniature)
def unprotected_buckets(template: dict[str, Any]) -> list[str]:
    flags = ("BlockPublicAcls", "BlockPublicPolicy", "IgnorePublicAcls", "RestrictPublicBuckets")
    bad = []
    for logical_id, res in template.get("Resources", {}).items():
        if res.get("Type") != "AWS::S3::Bucket":
            continue
        block = res.get("Properties", {}).get("PublicAccessBlockConfiguration", {})
        if not all(block.get(flag) is True for flag in flags):
            bad.append(logical_id)
    return sorted(bad)


# Example 5: read the real CDK program as text and list the constructs it uses
def constructs_used(source: str) -> list[str]:
    return sorted(set(re.findall(r"\b(?:s3|sqs|_lambda)\.([A-Z]\w+)\(", source)))


if __name__ == "__main__":
    name = resource_name("dev", "ingest", "uploads")
    tags = standard_tags("dev", "platform-team", "cc-100")
    print("name:", name)
    print("tags:", tags, "| missing:", missing_tags(tags))

    template = synth_bucket_template("UploadsBucket", name, True, tags)
    print("resources:", {k: v["Type"] for k, v in template["Resources"].items()})
    print("unprotected (secure):", unprotected_buckets(template))
    del template["Resources"]["UploadsBucket"]["Properties"]["PublicAccessBlockConfiguration"]
    print("unprotected (broken):", unprotected_buckets(template))

    for bad_env in ("test", "prod"):
        try:
            print(bad_env, "->", resource_name(bad_env, "Ingest", "x"))
        except ValueError as exc:
            print(bad_env, "-> error:", exc)

    print("cdk_app.py constructs:", constructs_used(CDK_APP.read_text()))
