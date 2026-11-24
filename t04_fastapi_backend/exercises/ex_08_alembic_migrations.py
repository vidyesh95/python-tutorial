"""Exercise 08: Alembic migrations (programmatic).

Tests use an in-memory SQLite connection. Use `alembic.operations.Operations` bound to a
`MigrationContext` for tasks 1-3, and `alembic.autogenerate.compare_metadata` for task 4.

Tasks
1. create_products_table(conn): op.create_table("products", id Integer primary key,
   name String(100) NOT NULL).
2. add_price_column(conn): add a nullable Integer column "price" to "products".
3. add_name_index(conn): create a (non-unique) index "ix_products_name" on products.name.
4. schema_diff(conn, metadata): compare the live DB with `metadata` and return a SORTED list of
   strings for these diff kinds (ignore every other kind):
       "add_table:<table>", "remove_table:<table>",
       "add_column:<table>.<column>", "remove_column:<table>.<column>"
   Hint: compare_metadata returns tuples like ("add_table", Table) and
   ("add_column", schema, table_name, Column); entries can also be nested lists.
5. revision_order(revisions): `revisions` is a list of (revision, down_revision) pairs in any
   order (down_revision None = the first migration). Return the revision ids ordered from
   first to head. Raise ValueError if there is not exactly one head (a "multiple heads"
   situation) or the chain is otherwise not a single line.

Run: uv run pytest t04_fastapi_backend -k ex_08
"""

from alembic.autogenerate import compare_metadata  # noqa: F401
from alembic.migration import MigrationContext  # noqa: F401
from alembic.operations import Operations  # noqa: F401
from sqlalchemy import Column, Integer, MetaData, String  # noqa: F401
from sqlalchemy.engine import Connection


def create_products_table(conn: Connection) -> None:
    raise NotImplementedError


def add_price_column(conn: Connection) -> None:
    raise NotImplementedError


def add_name_index(conn: Connection) -> None:
    raise NotImplementedError


def schema_diff(conn: Connection, metadata: MetaData) -> list[str]:
    raise NotImplementedError


def revision_order(revisions: list[tuple[str, str | None]]) -> list[str]:
    raise NotImplementedError
