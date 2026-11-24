import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from _loader import load

ex = load("t04_fastapi_backend", "ex_09_postgres_in_docker")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgres://u:p@h:5432/d", "postgresql+psycopg://u:p@h:5432/d"),
        ("postgresql://u:p@h/d", "postgresql+psycopg://u:p@h/d"),
        ("postgresql+asyncpg://u:p@h/d", "postgresql+asyncpg://u:p@h/d"),
        ("sqlite:///x.db", "sqlite:///x.db"),
    ],
)
def test_normalize_database_url(raw, expected):
    assert ex.normalize_database_url(raw) == expected


def test_get_database_url():
    assert ex.get_database_url({}) == "sqlite:///./dev.db"
    assert (
        ex.get_database_url({"DATABASE_URL": "postgres://a:b@db/app"})
        == "postgresql+psycopg://a:b@db/app"
    )


def test_engine_kwargs_sqlite_memory():
    for url in ("sqlite://", "sqlite:///:memory:"):
        kw = ex.engine_kwargs(url)
        assert kw["connect_args"] == {"check_same_thread": False}
        assert kw["poolclass"] is StaticPool


def test_engine_kwargs_sqlite_file():
    kw = ex.engine_kwargs("sqlite:///./dev.db")
    assert kw == {"connect_args": {"check_same_thread": False}}


def test_engine_kwargs_postgres():
    kw = ex.engine_kwargs("postgresql+psycopg://u:p@h/d")
    assert kw == {"pool_size": 5, "max_overflow": 10, "pool_pre_ping": True}


def test_engine_kwargs_actually_work_for_sqlite():
    engine = create_engine("sqlite://", **ex.engine_kwargs("sqlite://"))
    assert ex.db_is_healthy(engine)


def test_redact_url():
    assert (
        ex.redact_url("postgresql+psycopg://app:s3cret@localhost:5432/appdb")
        == "postgresql+psycopg://app:***@localhost:5432/appdb"
    )
    assert "s3cret" not in ex.redact_url("postgres://app:s3cret@h/d")
    assert ex.redact_url("sqlite:///x.db") == "sqlite:///x.db"


def test_db_is_healthy_false_when_broken():
    class BrokenEngine:
        def connect(self):
            from sqlalchemy.exc import OperationalError

            raise OperationalError("SELECT 1", {}, Exception("db is down"))

    assert ex.db_is_healthy(BrokenEngine()) is False


def test_health_route():
    engine = create_engine("sqlite://", **ex.engine_kwargs("sqlite://"))
    assert TestClient(ex.create_app(engine)).get("/health/db").json() == {"database": "up"}
