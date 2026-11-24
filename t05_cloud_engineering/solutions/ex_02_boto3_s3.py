"""Exercise 02: S3 with boto3 (tests inject a moto-backed client).

Tasks
1. put_json / get_json: store and fetch a dict; get_json returns None for a missing key.
2. list_keys: all keys under a prefix, using a paginator (works beyond 1000 keys).
3. presign_get: presigned GET URL with the given expiry.
4. plan_parts: split a size into multipart-upload part ranges.

Run: uv run pytest t05_cloud_engineering -k boto3_s3
"""

import json
from typing import Any

from botocore.exceptions import ClientError


def put_json(s3: Any, bucket: str, key: str, data: dict[str, Any]) -> None:
    """Store `data` as JSON bytes with ContentType "application/json"."""
    s3.put_object(
        Bucket=bucket, Key=key, Body=json.dumps(data).encode(), ContentType="application/json"
    )


def get_json(s3: Any, bucket: str, key: str) -> dict[str, Any] | None:
    """Return the decoded JSON, or None when the error code is "NoSuchKey".

    Any other ClientError (e.g. NoSuchBucket) must propagate.
    """
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
    except ClientError as err:
        if err.response["Error"]["Code"] == "NoSuchKey":
            return None
        raise
    return json.loads(obj["Body"].read())


def list_keys(s3: Any, bucket: str, prefix: str = "") -> list[str]:
    """Return every key starting with `prefix` (empty list if none). Use a paginator."""
    keys: list[str] = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        keys.extend(obj["Key"] for obj in page.get("Contents", []))
    return keys


def presign_get(s3: Any, bucket: str, key: str, expires: int = 300) -> str:
    """Return a presigned get_object URL valid for `expires` seconds."""
    return s3.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires
    )


def plan_parts(total_size: int, part_size: int) -> list[tuple[int, int, int]]:
    """Return [(part_number, start, end_exclusive), ...]; part numbers start at 1.

    plan_parts(10, 4) -> [(1, 0, 4), (2, 4, 8), (3, 8, 10)]; plan_parts(0, 4) -> [].
    Raise ValueError if part_size <= 0.
    """
    if part_size <= 0:
        raise ValueError("part_size must be positive")
    return [
        (i + 1, start, min(start + part_size, total_size))
        for i, start in enumerate(range(0, total_size, part_size))
    ]
