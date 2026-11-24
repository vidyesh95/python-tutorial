# Object Storage with boto3 and S3
"""
S3 stores OBJECTS (bytes + metadata) under KEYS inside BUCKETS. Keys are flat strings:
`reports/2026/q1.json` is one key, the "/" is only a convention (a PREFIX) the console shows
as folders.

boto3 gives you two API styles
- CLIENT (`boto3.client("s3")`): thin 1:1 wrapper over the HTTP API. Returns dicts. Complete,
  stable, and what this track uses.
- RESOURCE (`boto3.resource("s3")`): object-oriented (`bucket.objects.all()`). Convenient but
  in maintenance mode (no new features); prefer clients for new code.
- SESSION (`boto3.Session(profile_name=..., region_name=...)`): holds credentials and
  region; `session.client("s3")` builds clients from it. The default session reads the
  credential chain from m_01. Clients are thread-safe; Sessions are not (one per thread).

Core calls
- `put_object(Bucket, Key, Body, ContentType=...)`, `get_object(...)["Body"].read()`
- `list_objects_v2` returns at most 1000 keys per call -> use a PAGINATOR
  (`client.get_paginator("list_objects_v2")`) instead of hand-rolling continuation tokens.
- `generate_presigned_url("get_object", Params=..., ExpiresIn=300)`: a time-limited URL that
  lets a caller without AWS credentials GET (or PUT) exactly one object. Signed LOCALLY, no
  network call; it carries the permissions of whoever signed it. Use
  `Config(signature_version="s3v4")` so the URL uses modern SigV4 signing.
- Multipart upload: for big files (> ~100 MB, required > 5 GB) the object is split in parts
  (5 MiB - 5 GiB each, up to 10,000 parts) uploaded in parallel and retried independently.
  `upload_file`/`upload_fileobj` do this automatically (tune with `TransferConfig`).
  Abort incomplete uploads with a lifecycle rule, or they bill silently.

Errors: failed calls raise `botocore.exceptions.ClientError`. Inspect
`err.response["Error"]["Code"]` ("NoSuchKey", "NoSuchBucket", "AccessDenied", "404" from
`head_object`), never the message text. Network trouble raises `EndpointConnectionError`;
botocore already retries throttling and 5xx (configure with `Config(retries=...)`).

This lesson runs against moto (`mock_aws`), an in-memory fake of AWS: no account, no network.

Common mistakes
- Making a bucket public to share a file; use presigned URLs or CloudFront instead.
- Hand-looping `list_objects_v2` and silently reading only the first 1000 keys.
- Catching bare `Exception`, or matching error strings instead of error codes.
- Loading a huge object with `.read()`; stream it (`iter_chunks`) or use `download_fileobj`.
- Creating clients inside a hot loop (slow); create once and reuse.
- Bucket names are GLOBAL and DNS-like: lowercase, 3-63 chars, no underscores.

Production notes
- Turn on Block Public Access, default encryption (SSE-S3 or KMS) and versioning.
- Add lifecycle rules: expire temp data, move cold data to cheaper classes, abort multipart.
- Grant each service a role scoped to `bucket/prefix*` (m_01), never `s3:*` on `*`.
- Use a different key prefix per tenant/date to keep listings short and policies simple.

Cost notes
- You pay for storage (GB-month), requests (PUT/LIST cost ~10x GET), and data TRANSFER OUT.
  Transfer inside the same region to EC2/Lambda is free; cross-region and internet are not.
- LIST-heavy code is a classic surprise bill: keep an index (DynamoDB, m_03) instead.
- Small objects cost more in request fees than storage; batch them.
"""

import json
import os
from typing import Any
from unittest.mock import patch

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from moto import mock_aws

FAKE_AWS_ENV = {
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "AWS_SESSION_TOKEN": "testing",
    "AWS_DEFAULT_REGION": "us-east-1",
}


# Example 1: put / get JSON, with error handling on ClientError codes
def put_json(s3: Any, bucket: str, key: str, data: dict[str, Any]) -> None:
    s3.put_object(
        Bucket=bucket, Key=key, Body=json.dumps(data).encode(), ContentType="application/json"
    )


def get_json(s3: Any, bucket: str, key: str) -> dict[str, Any] | None:
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
    except ClientError as err:
        if err.response["Error"]["Code"] == "NoSuchKey":
            return None  # expected case: handle it
        raise  # AccessDenied, NoSuchBucket, throttling...: let the caller see it
    return json.loads(obj["Body"].read())


# Example 2: paginate a listing (never assume < 1000 keys)
def list_keys(s3: Any, bucket: str, prefix: str = "") -> list[str]:
    keys: list[str] = []
    pages = s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix)
    for page in pages:
        keys.extend(obj["Key"] for obj in page.get("Contents", []))  # no "Contents" if empty
    return keys


# Example 3: presigned URL (signed locally, no network call)
def presign_get(s3: Any, bucket: str, key: str, expires: int = 300) -> str:
    return s3.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires
    )


# Example 4: multipart concept: how a big file is split into parts
def plan_parts(total_size: int, part_size: int = 8 * 1024 * 1024) -> list[tuple[int, int, int]]:
    """Return (part_number, start, end_exclusive); S3 part numbers start at 1."""
    return [
        (i + 1, start, min(start + part_size, total_size))
        for i, start in enumerate(range(0, total_size, part_size))
    ]


def run_demo() -> None:
    # SigV4 makes presigned URLs carry X-Amz-Expires; required for KMS and newer regions.
    s3 = boto3.client("s3", region_name="us-east-1", config=Config(signature_version="s3v4"))
    s3.create_bucket(Bucket="lesson-bucket")
    put_json(s3, "lesson-bucket", "reports/a.json", {"n": 1})
    put_json(s3, "lesson-bucket", "reports/b.json", {"n": 2})
    print("get:", get_json(s3, "lesson-bucket", "reports/a.json"))
    print("missing:", get_json(s3, "lesson-bucket", "reports/zzz.json"))
    print("keys:", list_keys(s3, "lesson-bucket", "reports/"))
    url = presign_get(s3, "lesson-bucket", "reports/a.json", 60)
    print("presigned has expiry:", "X-Amz-Expires=60" in url)
    print("parts for 20 MiB:", plan_parts(20 * 1024 * 1024))
    try:
        s3.get_object(Bucket="no-such-bucket", Key="x")
    except ClientError as err:
        print("error code:", err.response["Error"]["Code"])


if __name__ == "__main__":
    with patch.dict(os.environ, FAKE_AWS_ENV), mock_aws():
        run_demo()
