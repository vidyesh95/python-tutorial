import pytest

pytest.importorskip("alembic")
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect

from _loader import load

ex = load("t04_fastapi_backend", "ex_08_alembic_migrations")


@pytest.fixture
def conn():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        yield connection
    engine.dispose()


def test_create_products_table(conn):
    ex.create_products_table(conn)
    insp = inspect(conn)
    assert "products" in insp.get_table_names()
    cols = {c["name"]: c for c in insp.get_columns("products")}
    assert set(cols) == {"id", "name"}
    assert cols["name"]["nullable"] is False
    assert insp.get_pk_constraint("products")["constrained_columns"] == ["id"]


def test_add_price_column(conn):
    ex.create_products_table(conn)
    ex.add_price_column(conn)
    cols = {c["name"]: c for c in inspect(conn).get_columns("products")}
    assert "price" in cols and cols["price"]["nullable"] is True


def test_add_name_index(conn):
    ex.create_products_table(conn)
    ex.add_name_index(conn)
    indexes = {i["name"]: i for i in inspect(conn).get_indexes("products")}
    assert indexes["ix_products_name"]["column_names"] == ["name"]
    assert not indexes["ix_products_name"]["unique"]


def test_schema_diff(conn):
    ex.create_products_table(conn)
    metadata = MetaData()
    Table(
        "products",
        metadata,
        Column("id", Integer, primary_key=True),
        # "name" is gone from the models, "sku" is new
        Column("sku", String(20)),
    )
    Table("orders", metadata, Column("id", Integer, primary_key=True))
    assert ex.schema_diff(conn, metadata) == [
        "add_column:products.sku",
        "add_table:orders",
        "remove_column:products.name",
    ]


def test_schema_diff_in_sync(conn):
    ex.create_products_table(conn)
    metadata = MetaData()
    Table(
        "products",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(100), nullable=False),
    )
    assert ex.schema_diff(conn, metadata) == []


def test_schema_diff_remove_table(conn):
    ex.create_products_table(conn)
    assert ex.schema_diff(conn, MetaData()) == ["remove_table:products"]


def test_revision_order():
    shuffled = [("c", "b"), ("a", None), ("b", "a")]
    assert ex.revision_order(shuffled) == ["a", "b", "c"]
    assert ex.revision_order([("only", None)]) == ["only"]


def test_revision_order_multiple_heads():
    with pytest.raises(ValueError):
        ex.revision_order([("a", None), ("b", "a"), ("c", "a")])


def test_revision_order_two_roots_or_broken_chain():
    with pytest.raises(ValueError):
        ex.revision_order([("a", None), ("b", None)])
    with pytest.raises(ValueError):
        ex.revision_order([("a", None), ("c", "b")])  # b is missing
