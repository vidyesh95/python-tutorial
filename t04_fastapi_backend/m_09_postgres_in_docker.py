# PostgreSQL in Docker
"""
SQLite is great for learning and tests; production services usually run PostgreSQL: real
concurrency, rich types, replication, strict constraints. Locally you run it in Docker so
your laptop stays clean and everyone gets the same version.

1) Start Postgres (compose file: t04_fastapi_backend/docker/compose.postgres.yaml):
       docker compose -f t04_fastapi_backend/docker/compose.postgres.yaml up -d
       docker compose -f t04_fastapi_backend/docker/compose.postgres.yaml ps      # wait: healthy
       docker compose -f t04_fastapi_backend/docker/compose.postgres.yaml down    # stop
   `up -d` = create + start in the background; `-f` selects the compose file; named volume
   `pgdata` keeps your data between restarts (`down -v` deletes it).

2) Tell the app where the database is with ONE environment variable (12-factor config):
       export DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/appdb
   URL shape: dialect+driver://user:password@host:port/database
   With no DATABASE_URL the app falls back to in-memory SQLite, so tests and this lesson
   work with no Docker at all.

3) Driver note: SQLAlchemy needs a DBAPI driver. Use psycopg 3 (`postgresql+psycopg://`;
   `uv add "psycopg[binary]"`) - it is NOT installed in this repo's `backend` group, which
   is why the demo below never opens a Postgres connection. For async engines use
   `postgresql+asyncpg://` (asyncpg) or `postgresql+psycopg://` with `create_async_engine`.
   Many hosts hand out `postgres://...` URLs - normalize them (see `normalize_database_url`).

The app code stays identical across databases: only the URL and a few engine options change.

Serve it live:  uv run fastapi dev t04_fastapi_backend/m_09_postgres_in_docker.py
Run the offline demo: uv run python -m t04_fastapi_backend.m_09_postgres_in_docker
"""

import os
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool

DEFAULT_URL = "sqlite://"  # in-memory


# Example: read config from the environment, with a safe local default
def get_database_url(environ: Mapping[str, str] = os.environ) -> str:
    return normalize_database_url(environ.get("DATABASE_URL", DEFAULT_URL))


def normalize_database_url(url: str) -> str:
    """Heroku/Render-style `postgres://` -> SQLAlchemy + psycopg3 driver URL."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


# Example: engine options differ per database
def engine_kwargs(url: str) -> dict[str, Any]:
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        kwargs: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
        if parsed.database in (None, "", ":memory:"):
            kwargs["poolclass"] = StaticPool  # share the one in-memory DB across threads
        return kwargs
    return {"pool_size": 5, "max_overflow": 10, "pool_pre_ping": True}  # server databases


def make_engine(url: str | None = None) -> Engine:
    url = url or get_database_url()
    return create_engine(url, **engine_kwargs(url))


def safe_url(url: str) -> str:
    """For logs: never print the password."""
    return make_url(url).render_as_string(hide_password=True)


engine = make_engine()
app = FastAPI(title="Postgres Config")


@app.get("/health/db")
def health_db() -> dict[str, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))  # cheapest possible round trip
    except SQLAlchemyError:
        return {"database": "down"}
    return {"database": "up", "url": safe_url(str(engine.url))}


"""
Common mistakes:
- Hardcoding credentials in source (they end up in git). Read them from the environment.
- Using `localhost` inside a container: the database is at its service name (`db`) on the
  compose network; `localhost` there means the app container itself.
- Forgetting `pool_pre_ping=True`: after a DB restart, the first requests fail on dead
  pooled connections.
- Running `docker compose down -v` and wondering where the data went (-v deletes volumes).
- Using the SQLite-only `check_same_thread` argument with Postgres (it is a TypeError).

Production notes:
- Don't use these compose credentials anywhere real. Use a managed Postgres (RDS, Cloud SQL,
  Neon...) and inject the URL via a secret manager.
- Size pools: (workers x pool_size) must stay below Postgres `max_connections`; put PgBouncer
  in front when you scale out.
- Use `sslmode=require` (in the URL query) for anything that crosses a network.
- Pin the Postgres major version (`postgres:17`) and test upgrades on a copy.
- Back up with `pg_dump` / managed snapshots; a Docker volume is NOT a backup.
- Run migrations (lesson 08) against Postgres in CI so SQLite-only assumptions get caught.
"""

if __name__ == "__main__":
    print("active URL:", safe_url(str(engine.url)), engine_kwargs(str(engine.url)))
    for raw in ("postgres://app:s3cret@db:5432/appdb", "postgresql://u:p@h/db", "sqlite:///x.db"):
        url = normalize_database_url(raw)
        print(raw, "->", safe_url(url))
    print(engine_kwargs("postgresql+psycopg://app:app@localhost:5432/appdb"))
    print(get_database_url({}), "|", get_database_url({"DATABASE_URL": "postgres://a:b@h/d"}))
    with TestClient(app) as client:
        print(client.get("/health/db").json())
