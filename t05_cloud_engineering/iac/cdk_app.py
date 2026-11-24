# GUARD: EXAMPLE ONLY. This file is NOT imported by any lesson or test and is NOT meant to run
# inside this repo. `aws-cdk-lib` is deliberately not installed here. To try it for real:
#   mkdir cdk-demo && cd cdk-demo && cp <this file> app.py
#   npm install -g aws-cdk && pip install aws-cdk-lib constructs
#   cdk bootstrap && cdk synth && cdk diff && cdk deploy && cdk destroy
"""CDK (Python) app: a private bucket, a queue with DLQ, and a Lambda wired with grants."""

import aws_cdk as cdk
from aws_cdk import Duration, RemovalPolicy, Stack, Tags
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sqs as sqs
from constructs import Construct


class IngestStack(Stack):
    """One stack = one CloudFormation stack = one deployable unit."""

    def __init__(self, scope: Construct, construct_id: str, *, env_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # L2 constructs apply secure, sensible defaults and generate IAM for you.
        bucket = s3.Bucket(
            self,
            "UploadsBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN if env_name == "prod" else RemovalPolicy.DESTROY,
            auto_delete_objects=env_name != "prod",
        )

        dlq = sqs.Queue(self, "JobsDlq", retention_period=Duration.days(14))
        queue = sqs.Queue(
            self,
            "JobsQueue",
            visibility_timeout=Duration.seconds(60),  # > function timeout
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=3, queue=dlq),
        )

        fn = _lambda.Function(
            self,
            "Worker",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="app.handler",
            code=_lambda.Code.from_asset("lambda_src"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={"BUCKET_NAME": bucket.bucket_name, "QUEUE_URL": queue.queue_url},
        )

        # Grants generate a least-privilege policy: s3:GetObject* on THIS bucket only, etc.
        bucket.grant_read(fn)
        queue.grant_consume_messages(fn)

        cdk.CfnOutput(self, "BucketName", value=bucket.bucket_name)


def main() -> None:
    app = cdk.App()
    env_name = app.node.try_get_context("env") or "dev"  # cdk deploy -c env=prod
    IngestStack(
        app,
        f"ingest-{env_name}",
        env_name=env_name,
        env=cdk.Environment(region="us-east-1"),  # account comes from your credentials
    )
    # Tags on the app propagate to every taggable resource (cost allocation).
    Tags.of(app).add("owner", "platform-team")
    Tags.of(app).add("env", env_name)
    app.synth()


if __name__ == "__main__":
    main()
