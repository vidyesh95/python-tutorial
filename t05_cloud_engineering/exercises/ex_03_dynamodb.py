"""Exercise 03: DynamoDB key design, queries, GSI and conditional writes.

`ddb` is a boto3 DynamoDB *resource*; `table` is a `ddb.Table(...)`. Tests use moto.

Tasks
1. create_orders_table: composite key + a GSI.
2. put_order_if_new: conditional put; False if the order already exists.
3. orders_for_customer / orders_by_status: query by key (newest first) and via the GSI.
4. update_status_if_version: optimistic locking with a `version` attribute.

Run: uv run pytest t05_cloud_engineering -k dynamodb
"""

from typing import Any

from boto3.dynamodb.conditions import Key  # noqa: F401  (handy for task 3)
from botocore.exceptions import ClientError  # noqa: F401  (handy for tasks 2 and 4)


def create_orders_table(ddb: Any, name: str = "orders") -> Any:
    """Create and return the table `name`.

    - Key: customer_id (S, HASH) + order_id (S, RANGE)
    - GSI "status-index": status (S, HASH) + order_id (S, RANGE), Projection ALL
    - BillingMode PAY_PER_REQUEST
    """
    raise NotImplementedError


def put_order_if_new(table: Any, order: dict[str, Any]) -> bool:
    """Put `order` only if no item with the same (customer_id, order_id) exists.

    Return True when written, False when it already existed
    (error code ConditionalCheckFailedException). Re-raise other errors.
    """
    raise NotImplementedError


def orders_for_customer(table: Any, customer_id: str) -> list[dict[str, Any]]:
    """All orders of a customer, NEWEST order_id first (sort key descending)."""
    raise NotImplementedError


def orders_by_status(table: Any, status: str) -> list[dict[str, Any]]:
    """All orders with this status, using the "status-index" GSI."""
    raise NotImplementedError


def update_status_if_version(
    table: Any, customer_id: str, order_id: str, new_status: str, expected_version: int
) -> bool:
    """Set status=new_status and version=expected_version+1, but only if the stored
    version equals `expected_version`. Return True on success, False if the condition fails.

    Hint: `status` is a DynamoDB reserved word; use ExpressionAttributeNames.
    """
    raise NotImplementedError
