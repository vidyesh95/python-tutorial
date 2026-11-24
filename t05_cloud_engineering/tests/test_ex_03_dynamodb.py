from decimal import Decimal

import pytest

boto3 = pytest.importorskip("boto3")
from moto import mock_aws  # noqa: E402

from _loader import load  # noqa: E402

ex = load("t05_cloud_engineering", "ex_03_dynamodb")


@pytest.fixture
def ddb(monkeypatch):
    for key, value in {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": "us-east-1",
    }.items():
        monkeypatch.setenv(key, value)
    with mock_aws():
        yield boto3.resource("dynamodb", region_name="us-east-1")


@pytest.fixture
def table(ddb):
    return ex.create_orders_table(ddb)


def order(customer: str, oid: str, status: str = "NEW", version: int = 1) -> dict:
    return {
        "customer_id": customer,
        "order_id": oid,
        "status": status,
        "version": version,
        "total": Decimal("9.99"),
    }


def test_create_orders_table_schema(ddb):
    table = ex.create_orders_table(ddb, "my-orders")
    assert table.table_name == "my-orders"
    keys = {k["AttributeName"]: k["KeyType"] for k in table.key_schema}
    assert keys == {"customer_id": "HASH", "order_id": "RANGE"}
    gsis = {g["IndexName"]: g for g in table.global_secondary_indexes}
    assert "status-index" in gsis
    assert {k["AttributeName"]: k["KeyType"] for k in gsis["status-index"]["KeySchema"]} == {
        "status": "HASH",
        "order_id": "RANGE",
    }


def test_put_order_if_new(table):
    assert ex.put_order_if_new(table, order("c1", "o1")) is True
    assert ex.put_order_if_new(table, order("c1", "o1", status="PAID")) is False
    stored = table.get_item(Key={"customer_id": "c1", "order_id": "o1"})["Item"]
    assert stored["status"] == "NEW"  # second put did not overwrite


def test_orders_for_customer_newest_first(table):
    for oid in ("2026-01", "2026-03", "2026-02"):
        ex.put_order_if_new(table, order("c1", oid))
    ex.put_order_if_new(table, order("c2", "2026-09"))
    got = [o["order_id"] for o in ex.orders_for_customer(table, "c1")]
    assert got == ["2026-03", "2026-02", "2026-01"]
    assert ex.orders_for_customer(table, "nobody") == []


def test_orders_by_status_uses_gsi(table):
    ex.put_order_if_new(table, order("c1", "o1", "NEW"))
    ex.put_order_if_new(table, order("c2", "o2", "PAID"))
    ex.put_order_if_new(table, order("c3", "o3", "NEW"))
    assert sorted(o["order_id"] for o in ex.orders_by_status(table, "NEW")) == ["o1", "o3"]
    assert [o["customer_id"] for o in ex.orders_by_status(table, "PAID")] == ["c2"]


def test_update_status_if_version(table):
    ex.put_order_if_new(table, order("c1", "o1", "NEW", version=1))
    assert ex.update_status_if_version(table, "c1", "o1", "PAID", 1) is True
    item = table.get_item(Key={"customer_id": "c1", "order_id": "o1"})["Item"]
    assert item["status"] == "PAID" and item["version"] == 2
    # stale writer still thinks version is 1
    assert ex.update_status_if_version(table, "c1", "o1", "CANCELLED", 1) is False
    item = table.get_item(Key={"customer_id": "c1", "order_id": "o1"})["Item"]
    assert item["status"] == "PAID"
    assert ex.update_status_if_version(table, "c1", "o1", "SHIPPED", 2) is True
