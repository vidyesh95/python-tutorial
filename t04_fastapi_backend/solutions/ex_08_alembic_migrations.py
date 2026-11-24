"""Reference solution for Exercise 08: Alembic migrations (programmatic)."""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, Integer, MetaData, String
from sqlalchemy.engine import Connection


def _ops(conn: Connection) -> Operations:
    return Operations(MigrationContext.configure(conn))


def create_products_table(conn: Connection) -> None:
    _ops(conn).create_table(
        "products",
        Column("id", Integer, primary_key=True),
        Column("name", String(100), nullable=False),
    )


def add_price_column(conn: Connection) -> None:
    _ops(conn).add_column("products", Column("price", Integer, nullable=True))


def add_name_index(conn: Connection) -> None:
    _ops(conn).create_index("ix_products_name", "products", ["name"], unique=False)


def _flatten(diffs: list) -> list[tuple]:
    flat: list[tuple] = []
    for d in diffs:
        if isinstance(d, list):
            flat.extend(_flatten(d))
        else:
            flat.append(d)
    return flat


def schema_diff(conn: Connection, metadata: MetaData) -> list[str]:
    ctx = MigrationContext.configure(conn)
    result: list[str] = []
    for diff in _flatten(compare_metadata(ctx, metadata)):
        kind = diff[0]
        if kind in ("add_table", "remove_table"):
            result.append(f"{kind}:{diff[1].name}")
        elif kind in ("add_column", "remove_column"):
            result.append(f"{kind}:{diff[2]}.{diff[3].name}")
    return sorted(result)


def revision_order(revisions: list[tuple[str, str | None]]) -> list[str]:
    children: dict[str | None, list[str]] = {}
    for rev, parent in revisions:
        children.setdefault(parent, []).append(rev)
    if any(len(kids) > 1 for kids in children.values()):
        raise ValueError("multiple heads: a revision has more than one child")
    order: list[str] = []
    current = children.get(None, [None])[0]
    while current is not None:
        order.append(current)
        nxt = children.get(current)
        current = nxt[0] if nxt else None
    if len(order) != len(revisions):
        raise ValueError("revisions do not form a single chain")
    return order
