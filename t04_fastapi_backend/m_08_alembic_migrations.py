# Database Migrations with Alembic
"""
A migration is a versioned, ordered script that changes the database SCHEMA. Alembic keeps a
table `alembic_version` holding the current revision id, so every environment (laptop, CI,
production) can be moved to the same schema by running the same scripts in order.

Concepts:
- REVISION: one script in `alembic/versions/` with `revision`, `down_revision`
  (the parent - together they form a linked list/graph), `upgrade()` and `downgrade()`.
- HEAD: the newest revision. `upgrade head` applies everything not yet applied.
- AUTOGENERATE: Alembic compares your models' `MetaData` with the live database and drafts
  the script. ALWAYS read it: it can miss renames (sees drop + add), column type tweaks,
  and server defaults.
- `op.*` (create_table, add_column, create_index, execute...) are the operations you call.

Everyday commands:
    uv run alembic init alembic                         # one-time scaffold (alembic.ini + env.py)
    #   edit alembic/env.py:  target_metadata = Base.metadata ; URL from your settings
    uv run alembic revision --autogenerate -m "add users"
    uv run alembic upgrade head                         # apply
    uv run alembic downgrade -1                         # undo last
    uv run alembic current / history                    # inspect
    uv run alembic upgrade head --sql                   # print SQL instead of running it
    uv run alembic stamp head                           # mark DB as up to date w/o running

This lesson runs a REAL tiny migration environment from a temp directory (nothing is left
behind) and also shows the lower-level `Operations` + autogenerate APIs.
We pass the live connection to Alembic via `config.attributes["connection"]` - the standard
trick for running migrations inside an app or a test (and needed for in-memory SQLite).

Serve it live:  uv run fastapi dev t04_fastapi_backend/m_08_alembic_migrations.py
Run the offline demo: uv run python -m t04_fastapi_backend.m_08_alembic_migrations
"""

import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import alembic
from alembic import command
from alembic.autogenerate import compare_metadata, produce_migrations, render_python_code
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect
from sqlalchemy.engine import Connection
from sqlalchemy.pool import StaticPool

# Example: files a migration environment needs (normally created by `alembic init`)
ENV_PY = """
from alembic import context

config = context.config
connection = config.attributes["connection"]  # handed in by our code
context.configure(connection=connection, target_metadata=config.attributes.get("metadata"))
with context.begin_transaction():
    context.run_migrations()
"""

REVISION_1 = '''"""create users"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("users")
'''

REVISION_2 = '''"""add users.email"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"  # parent: runs after 0001
branch_labels = None
depends_on = None


def upgrade() -> None:
    # nullable (or with a server_default) so existing rows stay valid
    op.add_column("users", sa.Column("email", sa.String(100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:  # SQLite needs "batch" to drop a column
        batch.drop_column("email")
'''


def make_config(root: Path, connection: Connection, metadata: MetaData | None = None) -> Config:
    """Write a throwaway migration environment under `root` and return an Alembic Config."""
    (root / "versions").mkdir(parents=True)
    (root / "env.py").write_text(ENV_PY)
    (root / "versions" / "0001_create_users.py").write_text(REVISION_1)
    (root / "versions" / "0002_add_email.py").write_text(REVISION_2)
    cfg = Config()
    cfg.set_main_option("script_location", str(root))
    cfg.attributes["connection"] = connection
    cfg.attributes["metadata"] = metadata
    return cfg


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # "Migrate on startup" - fine for small apps; big ones run `alembic upgrade head` as a
    # separate deploy step so N replicas don't race.
    with tempfile.TemporaryDirectory() as tmp, engine.begin() as conn:
        command.upgrade(make_config(Path(tmp) / "alembic", conn), "head")
    yield


app = FastAPI(title="Alembic Demo", lifespan=lifespan)


@app.get("/schema")
def schema() -> dict[str, list[str]]:
    insp = inspect(engine)
    return {t: [c["name"] for c in insp.get_columns(t)] for t in sorted(insp.get_table_names())}


"""
Common mistakes:
- Editing a migration that was already applied elsewhere. Add a NEW revision instead.
- Trusting autogenerate blindly (renames become drop+add = DATA LOSS).
- Forgetting to import all models before `target_metadata = Base.metadata`, so autogenerate
  sees an empty schema and wants to drop everything.
- Adding a NOT NULL column without a default to a table that already has rows.
- Using `Base.metadata.create_all()` AND Alembic: pick one (Alembic) for real databases.
- Two developers creating revisions from the same parent -> multiple heads
  (`alembic merge heads` fixes it).

Production notes:
- Run migrations before the new app version receives traffic, once, from CI/CD or an init job.
- Keep migrations backward compatible (expand -> deploy -> contract) so rollouts can overlap.
- Big tables: adding indexes/columns can lock; use `CREATE INDEX CONCURRENTLY` on Postgres.
- Test `upgrade head` and `downgrade base` in CI against the same engine as production.
- SQLite can't ALTER most things; use `op.batch_alter_table` (or `render_as_batch=True`).
"""

if __name__ == "__main__":
    print("alembic", alembic.__version__)
    with tempfile.TemporaryDirectory() as tmp, create_engine("sqlite://").begin() as conn:
        cfg = make_config(Path(tmp) / "alembic", conn)
        command.upgrade(cfg, "0001")
        print("after 0001:", [c["name"] for c in inspect(conn).get_columns("users")])
        command.upgrade(cfg, "head")
        print("after head:", [c["name"] for c in inspect(conn).get_columns("users")])
        print("version row:", conn.exec_driver_sql("SELECT version_num FROM alembic_version").all())
        command.downgrade(cfg, "-1")
        print("after downgrade:", [c["name"] for c in inspect(conn).get_columns("users")])

        # Autogenerate: what differs between the DB and our "desired" models?
        command.upgrade(cfg, "head")
        wanted = MetaData()
        Table(
            "users",
            wanted,
            Column("id", Integer, primary_key=True),
            Column("name", String(50), nullable=False),
            Column("email", String(100)),
            Column("nickname", String(30)),  # new in our "models"
        )
        ctx = MigrationContext.configure(conn)
        print("diff:", [d[0] + ":" + d[3].name for d in compare_metadata(ctx, wanted)])
        script = render_python_code(produce_migrations(ctx, wanted).upgrade_ops)
        print("autogenerated upgrade():\n" + script)

    # Low level: Operations works on any connection, no script files involved
    with create_engine("sqlite://").begin() as conn:
        op = Operations(MigrationContext.configure(conn))
        op.create_table("notes", Column("id", Integer, primary_key=True))
        op.add_column("notes", Column("body", String(200)))
        print("Operations:", [c["name"] for c in inspect(conn).get_columns("notes")])

    with TestClient(app) as client:  # lifespan migrates the in-memory DB at startup
        print(client.get("/schema").json())
