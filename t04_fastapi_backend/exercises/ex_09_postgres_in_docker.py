"""Exercise 09: Database configuration for SQLite and PostgreSQL.

No Docker or Postgres is needed: you only build URLs and options. (To try the real thing:
`docker compose -f t04_fastapi_backend/docker/compose.postgres.yaml up -d`.)

Tasks
1. normalize_database_url: rewrite "postgres://..." and "postgresql://..." to
   "postgresql+psycopg://..."; leave every other URL (already-qualified, sqlite...) untouched.
2. get_database_url: read DATABASE_URL from the given mapping (default "sqlite:///./dev.db")
   and return it normalized.
3. engine_kwargs: options for `create_engine(url, **kwargs)`:
   - sqlite: {"connect_args": {"check_same_thread": False}}, plus "poolclass": StaticPool
     when the database is in-memory (no database part, or ":memory:").
   - anything else: {"pool_size": 5, "max_overflow": 10, "pool_pre_ping": True}.
4. redact_url: return the URL with the password replaced by "***" (safe for logs).
   Use `sqlalchemy.engine.make_url`. URLs without a password come back unchanged.
5. db_is_healthy: True if `SELECT 1` works on a connection from the engine, False if
   SQLAlchemy raises an error. (Used by the /health/db route in `create_app`.)

Run: uv run pytest t04_fastapi_backend -k ex_09
"""

from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI
from sqlalchemy import Engine, text  # noqa: F401
from sqlalchemy.engine import make_url  # noqa: F401
from sqlalchemy.exc import SQLAlchemyError  # noqa: F401
from sqlalchemy.pool import StaticPool  # noqa: F401


def normalize_database_url(url: str) -> str:
    raise NotImplementedError


def get_database_url(environ: Mapping[str, str]) -> str:
    raise NotImplementedError


def engine_kwargs(url: str) -> dict[str, Any]:
    raise NotImplementedError


def redact_url(url: str) -> str:
    raise NotImplementedError


def db_is_healthy(engine: Engine) -> bool:
    raise NotImplementedError


def create_app(engine: Engine) -> FastAPI:
    app = FastAPI(title="Exercise 09")

    @app.get("/health/db")
    def health_db() -> dict[str, str]:
        return {"database": "up" if db_is_healthy(engine) else "down"}

    return app
