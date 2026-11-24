# DynamoDB Data Modeling
"""
DynamoDB is a managed key-value / document store built for predictable single-digit
millisecond reads at any scale. The price: you must design tables around your ACCESS
PATTERNS up front. There are no joins and almost no ad-hoc queries.

Keys
- PARTITION KEY (PK): hashed to choose the partition. All reads must supply it.
- SORT KEY (SK, optional): items with the same PK are stored ordered by SK, so you can do
  range queries (`begins_with`, `between`, newest-first with `ScanIndexForward=False`).
- Good PKs have high cardinality and even traffic (customer_id, not "status"). A "hot"
  partition throttles you however much capacity you buy.

Operations
- `put_item` / `get_item` / `update_item` / `delete_item`: single-item, by full key. Cheap.
- `query`: one PK + optional SK condition. Cheap and fast. Use this.
- `scan`: reads the WHOLE table. Slow and expensive; avoid outside tooling/small tables.
- GSI (global secondary index): an extra copy of the data under a different PK/SK so you
  can query another access pattern ("orders by status"). Eventually consistent.
- Conditional writes: `ConditionExpression="attribute_not_exists(pk)"` makes put atomic
  "create if new". A `version` attribute checked in the condition gives OPTIMISTIC LOCKING:
  concurrent writers lose with `ConditionalCheckFailedException` instead of overwriting.
- Items are limited to 400 KB. Numbers are `Decimal` in Python (floats are rejected).

Single-table design (intro): store several entity types in ONE table with generic `pk`/`sk`
(`CUSTOMER#1` / `PROFILE`, `CUSTOMER#1` / `ORDER#2026-01-02#001`). One `query` on the PK then
returns a customer and all their orders in one round trip. It trades flexibility for speed;
start with one table per entity if you are unsure, and only fold tables together when an
access pattern demands it.

Capacity modes: ON-DEMAND (`PAY_PER_REQUEST`, pay per read/write, zero planning) or
PROVISIONED (set RCU/WCU, cheaper at steady high load, throttles if exceeded).

Common mistakes
- Using `scan` in request paths, or filtering with `FilterExpression` and expecting it to
  reduce cost (the read cost is paid BEFORE the filter).
- Low-cardinality or time-based partition keys that create a hot partition.
- Passing Python `float` (raises TypeError); use `Decimal("9.99")` or integers (cents).
- Read-modify-write without a condition (lost updates).
- Forgetting pagination: `query` returns at most 1 MB; follow `LastEvaluatedKey`.
- Using reserved words (`status`, `name`) in expressions without `ExpressionAttributeNames`.

Production notes
- Model access patterns first, write them down, then pick keys and indexes.
- Enable point-in-time recovery and TTL (auto-expire items) where appropriate.
- Use `batch_writer()` for bulk loads and exponential backoff on throttling (boto3 retries).
- Give a service a role limited to `dynamodb:GetItem/PutItem/Query` on ONE table ARN.

Cost notes
- On-demand: ~ $1.25 per million writes, ~ $0.25 per million reads (check current pricing);
  an eventually consistent read costs half a strongly consistent one.
- Every GSI is another copy you pay to store and write to. Add only what you query.
- Free tier covers 25 GB and some provisioned capacity; on-demand has no free quota.
"""

import os
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from moto import mock_aws

FAKE_AWS_ENV = {
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "AWS_SESSION_TOKEN": "testing",
    "AWS_DEFAULT_REGION": "us-east-1",
}


# Example 1: create a table with a composite key and a GSI
def create_orders_table(ddb: Any, name: str = "orders") -> Any:
    table = ddb.create_table(
        TableName=name,
        KeySchema=[
            {"AttributeName": "customer_id", "KeyType": "HASH"},
            {"AttributeName": "order_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "customer_id", "AttributeType": "S"},
            {"AttributeName": "order_id", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "status-index",
                "KeySchema": [
                    {"AttributeName": "status", "KeyType": "HASH"},
                    {"AttributeName": "order_id", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()
    return table


# Example 2: conditional put ("create if new") and optimistic locking
def put_order_if_new(table: Any, order: dict[str, Any]) -> bool:
    try:
        table.put_item(
            Item=order,
            ConditionExpression="attribute_not_exists(customer_id) AND attribute_not_exists(order_id)",
        )
    except ClientError as err:
        if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise
    return True


def update_status_if_version(
    table: Any, customer_id: str, order_id: str, new_status: str, expected_version: int
) -> bool:
    try:
        table.update_item(
            Key={"customer_id": customer_id, "order_id": order_id},
            UpdateExpression="SET #s = :s, version = :next",
            ConditionExpression="version = :expected",
            ExpressionAttributeNames={"#s": "status"},  # `status` is a reserved word
            ExpressionAttributeValues={
                ":s": new_status,
                ":next": expected_version + 1,
                ":expected": expected_version,
            },
        )
    except ClientError as err:
        if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False  # someone else updated first: re-read and retry
        raise
    return True


# Example 3: query by key, newest first, and by GSI
def orders_for_customer(table: Any, customer_id: str) -> list[dict[str, Any]]:
    resp = table.query(
        KeyConditionExpression=Key("customer_id").eq(customer_id), ScanIndexForward=False
    )
    return resp["Items"]  # real code: follow resp.get("LastEvaluatedKey")


def orders_by_status(table: Any, status: str) -> list[dict[str, Any]]:
    resp = table.query(IndexName="status-index", KeyConditionExpression=Key("status").eq(status))
    return resp["Items"]


# Example 4: single-table design: profile + orders under one partition key
def single_table_demo(ddb: Any) -> list[str]:
    table = ddb.create_table(
        TableName="app",
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    with table.batch_writer() as batch:
        batch.put_item(Item={"pk": "CUSTOMER#1", "sk": "PROFILE", "name": "Ada"})
        batch.put_item(Item={"pk": "CUSTOMER#1", "sk": "ORDER#2026-01-02#001", "total": 500})
        batch.put_item(Item={"pk": "CUSTOMER#1", "sk": "ORDER#2026-02-03#002", "total": 900})
    everything = table.query(KeyConditionExpression=Key("pk").eq("CUSTOMER#1"))["Items"]
    orders = table.query(
        KeyConditionExpression=Key("pk").eq("CUSTOMER#1") & Key("sk").begins_with("ORDER#")
    )["Items"]
    return [f"all={len(everything)}", f"orders={len(orders)}"]


if __name__ == "__main__":
    with patch.dict(os.environ, FAKE_AWS_ENV), mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        table = create_orders_table(ddb)
        o1 = {
            "customer_id": "c1",
            "order_id": "2026-01-01#a",
            "status": "NEW",
            "version": 1,
            "total": Decimal("19.99"),
        }
        o2 = {
            "customer_id": "c1",
            "order_id": "2026-02-01#b",
            "status": "PAID",
            "version": 1,
            "total": Decimal("5.00"),
        }
        print("put o1:", put_order_if_new(table, o1), "| again:", put_order_if_new(table, o1))
        put_order_if_new(table, o2)
        print("newest first:", [o["order_id"] for o in orders_for_customer(table, "c1")])
        print("status NEW:", [o["order_id"] for o in orders_by_status(table, "NEW")])
        print("update v1:", update_status_if_version(table, "c1", o1["order_id"], "PAID", 1))
        print("stale update v1:", update_status_if_version(table, "c1", o1["order_id"], "X", 1))
        print("single table:", single_table_demo(ddb))
