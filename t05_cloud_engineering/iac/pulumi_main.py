# GUARD: EXAMPLE ONLY. This file is NOT imported by any lesson or test and is NOT meant to run
# inside this repo. `pulumi` and `pulumi-aws` are deliberately not installed here. To try it:
#   mkdir pulumi-demo && cd pulumi-demo && pulumi new aws-python    # creates Pulumi.yaml
#   cp <this file> __main__.py && pip install pulumi pulumi-aws
#   pulumi stack init dev && pulumi config set aws:region us-east-1
#   pulumi config set --secret dbPassword '<value>'     # stored ENCRYPTED in Pulumi.dev.yaml
#   pulumi preview && pulumi up && pulumi destroy
"""Pulumi program (Python): a private bucket, a queue, a log group, and a secret-backed output."""

import pulumi
import pulumi_aws as aws


def main() -> None:
    config = pulumi.Config()  # values for THIS stack (Pulumi.<stack>.yaml)
    env = pulumi.get_stack()  # "dev", "staging", "prod"
    retention_days = config.get_int("logRetentionDays") or 14
    db_password = config.require_secret("dbPassword")  # Output[str], masked in logs/state

    tags = {"env": env, "owner": "platform-team", "managed-by": "pulumi"}

    # Resources are ordinary Python objects. Arguments that are Outputs create dependencies.
    bucket = aws.s3.BucketV2(f"uploads-{env}", tags=tags)
    aws.s3.BucketPublicAccessBlock(
        f"uploads-{env}-pab",
        bucket=bucket.id,  # Output: Pulumi orders creation automatically
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True,
    )
    aws.s3.BucketServerSideEncryptionConfigurationV2(
        f"uploads-{env}-sse",
        bucket=bucket.id,
        rules=[
            aws.s3.BucketServerSideEncryptionConfigurationV2RuleArgs(
                apply_server_side_encryption_by_default=(
                    aws.s3.BucketServerSideEncryptionConfigurationV2RuleApplyServerSideEncryptionByDefaultArgs(
                        sse_algorithm="AES256"
                    )
                )
            )
        ],
    )

    queue = aws.sqs.Queue(f"jobs-{env}", visibility_timeout_seconds=60, tags=tags)
    aws.cloudwatch.LogGroup(f"app-{env}", retention_in_days=retention_days, tags=tags)

    # Outputs resolve only after `pulumi up`; use .apply / Output.concat to transform them.
    pulumi.export("bucket_name", bucket.bucket)
    pulumi.export("queue_url", queue.url)
    pulumi.export("db_password_length", db_password.apply(len))  # secret stays secret


main()  # Pulumi imports/runs the program file; the resource graph is built as a side effect
