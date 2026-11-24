"""Reference solution for Exercise 09: Database configuration for SQLite and PostgreSQL."""

from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI
from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool


def normalize_database_url(url: str) -> str:
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


def get_database_url(environ: Mapping[str, str]) -> str:
    return normalize_database_url(environ.get("DATABASE_URL", "sqlite:///./dev.db"))


def engine_kwargs(url: str) -> dict[str, Any]:
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        kwargs: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
        if parsed.database in (None, "", ":memory:"):
            kwargs["poolclass"] = StaticPool
        return kwargs
    return {"pool_size": 5, "max_overflow": 10, "pool_pre_ping": True}


def redact_url(url: str) -> str:
    return make_url(url).render_as_string(hide_password=True)


def db_is_healthy(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True


def create_app(engine: Engine) -> FastAPI:
    app = FastAPI(title="Exercise 09")

    @app.get("/health/db")
    def health_db() -> dict[str, str]:
        return {"database": "up" if db_is_healthy(engine) else "down"}

    return app
