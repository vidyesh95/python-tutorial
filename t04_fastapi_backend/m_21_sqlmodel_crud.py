# SQLModel CRUD
"""
SQLModel = Pydantic + SQLAlchemy in one class. A `SQLModel` subclass is a Pydantic model
(validation, JSON schema, `model_dump`); add `table=True` and it is ALSO a SQLAlchemy mapped
class (a table, `session.add(...)`). Under the hood it IS SQLAlchemy: `Session` subclasses
SQLAlchemy's Session, `create_engine` is SQLAlchemy's, and `select()` comes from SQLAlchemy.

The "multiple models" pattern (one model per job, so secrets never leak):
- `HeroBase`:   fields shared by everything (name, age).
- `Hero(table=True)`: the DB row. Adds `id` and the private `secret_name`.
- `HeroCreate`: what clients POST. Base + `secret_name`. No `id`: the DB assigns it.
- `HeroPublic`: what the API RETURNS. Base + a required `id`. No `secret_name`.
- `HeroUpdate`: what clients PATCH. Every field optional.

CRUD recipe
- Create: `Hero.model_validate(hero_create)` -> `add` -> `commit` -> `refresh` (reloads `id`).
- Read:   `session.get(Hero, id)` (None if missing -> raise 404); lists use
          `session.exec(select(Hero).offset(o).limit(n)).all()`.
- Update: `data.model_dump(exclude_unset=True)` keeps ONLY fields the client sent, then
          `db_obj.sqlmodel_update(patch)` copies them onto the row. Omitted != null.
- Delete: `session.delete(obj)` + `commit`.
- `response_model=HeroPublic` is needed here: we return a `Hero` row but publish a
  narrower schema, which also strips `secret_name`.

SQLModel vs SQLAlchemy ORM (lesson 07)
- Pick SQLModel for CRUD-style APIs where table, request and response shapes mostly overlap:
  less duplication (no separate ORM class + Pydantic schema) and the FastAPI-recommended path.
- Pick plain SQLAlchemy 2.0 for complex mappings: rich relationships/eager-loading control,
  composite keys, advanced typing, or when you want the DB layer free of Pydantic.
- You can mix them: drop down to SQLAlchemy constructs whenever SQLModel lacks a feature.

SQLite in memory needs `StaticPool` + `check_same_thread=False` (see lesson 07), otherwise
each connection sees a different empty database and FastAPI's worker threads trip on it.

Serve it live:  uv run fastapi dev t04_fastapi_backend/m_21_sqlmodel_crud.py
Run the offline demo: uv run python -m t04_fastapi_backend.m_21_sqlmodel_crud
"""

from collections.abc import Iterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Field, Session, SQLModel, create_engine, select


# Example: the multiple-models pattern
class HeroBase(SQLModel):
    name: str = Field(index=True, min_length=1)
    age: int | None = Field(default=None, index=True, ge=0)


class Hero(HeroBase, table=True):
    # Explicit name: SQLModel.metadata is process-global, so keep lesson tables distinct.
    __tablename__ = "lesson21_hero"

    id: int | None = Field(default=None, primary_key=True)
    secret_name: str


class HeroCreate(HeroBase):
    secret_name: str


class HeroPublic(HeroBase):
    id: int


class HeroUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1)
    age: int | None = Field(default=None, ge=0)
    secret_name: str | None = None


# Example: engine (in-memory SQLite shared across threads)
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:  # one session per request, closed afterwards
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(_: FastAPI):
    SQLModel.metadata.create_all(engine)  # demos only; real apps use Alembic (lesson 08)
    yield


app = FastAPI(title="Hero SQLModel CRUD", lifespan=lifespan)


@app.post("/heroes/", response_model=HeroPublic, status_code=201)
def create_hero(hero: HeroCreate, session: SessionDep) -> Hero:
    db_hero = Hero.model_validate(hero)  # HeroCreate -> table model
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)  # populate the DB-generated id
    return db_hero


@app.get("/heroes/", response_model=list[HeroPublic])
def read_heroes(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[Hero]:
    return list(session.exec(select(Hero).order_by(Hero.id).offset(offset).limit(limit)).all())


@app.get("/heroes/{hero_id}", response_model=HeroPublic)
def read_hero(hero_id: int, session: SessionDep) -> Hero:
    hero = session.get(Hero, hero_id)
    if hero is None:
        raise HTTPException(status_code=404, detail="Hero not found")
    return hero


@app.patch("/heroes/{hero_id}", response_model=HeroPublic)
def update_hero(hero_id: int, hero: HeroUpdate, session: SessionDep) -> Hero:
    db_hero = session.get(Hero, hero_id)
    if db_hero is None:
        raise HTTPException(status_code=404, detail="Hero not found")
    patch = hero.model_dump(exclude_unset=True)  # only what the client actually sent
    db_hero.sqlmodel_update(patch)
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero


@app.delete("/heroes/{hero_id}")
def delete_hero(hero_id: int, session: SessionDep) -> dict[str, bool]:
    hero = session.get(Hero, hero_id)
    if hero is None:
        raise HTTPException(status_code=404, detail="Hero not found")
    session.delete(hero)
    session.commit()
    return {"ok": True}


"""
Common mistakes:
- Returning the table model without `response_model=HeroPublic`: `secret_name` leaks.
- Using `HeroCreate` as the table model: clients could then send their own `id`.
- Using `hero.model_dump()` (no `exclude_unset=True`) in PATCH: omitted fields become
  their defaults (None) and silently wipe stored data.
- Expecting validation on `table=True` models: SQLModel table classes do NOT validate on
  `__init__`. Validate with a plain SQLModel (HeroCreate) and convert via `model_validate`.
- Forgetting `session.refresh(obj)` after commit: attributes are expired / `id` is stale
  (SQLModel's Session expires on commit by default).
- Calling `session.query(...)`/`session.execute(select(...))`: prefer `session.exec(...)`,
  which returns typed scalars for single-entity selects.
- In-memory SQLite without StaticPool: tables "disappear" between connections.

Production notes:
- Use migrations (Alembic, lesson 08) instead of `create_all`, and a real DB (Postgres).
- Cap `limit` with `Query(le=...)` (as here) so one request cannot dump the whole table.
  For big tables prefer keyset pagination over large offsets.
- Hash anything secret (passwords) before storing; `secret_name` here only demonstrates
  hiding a column from the public schema.
- Handlers here are sync `def` (run in the threadpool), which suits the sync Session.
- The `engine` is module-level for the demo; for tests build a fresh engine and inject it
  (see the exercise's `create_app(engine)` factory).
"""

if __name__ == "__main__":
    with TestClient(app) as client:  # `with` runs the lifespan -> tables get created
        created = client.post(
            "/heroes/", json={"name": "Deadpond", "age": 30, "secret_name": "Dive Wilson"}
        )
        print(created.status_code, created.json())  # no secret_name in the response
        client.post("/heroes/", json={"name": "Spider-Boy", "secret_name": "Pedro Parqueador"})
        client.post("/heroes/", json={"name": "Rusty-Man", "age": 48, "secret_name": "Tommy"})
        print([h["name"] for h in client.get("/heroes/", params={"offset": 1, "limit": 2}).json()])
        print(client.patch("/heroes/2", json={"age": 17}).json())  # name is untouched
        print(client.delete("/heroes/3").json())
        print(client.get("/heroes/3").status_code)  # 404
        print(client.post("/heroes/", json={"name": "NoSecret"}).status_code)  # 422
        print(client.get("/heroes/", params={"limit": 1000}).status_code)  # 422 (le=100)
