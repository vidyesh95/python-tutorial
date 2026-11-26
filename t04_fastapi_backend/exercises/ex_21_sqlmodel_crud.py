"""Exercise 21: SQLModel CRUD.

The models and the FastAPI wiring (`create_app(engine)`) are written for you. Implement the
data-access helpers and the session dependency. Tests build a fresh in-memory SQLite engine
(StaticPool) for every test and pass it to `create_app`.

Tasks
1. make_session_dependency(engine): return a generator function (a yield dependency) that
   opens `Session(engine)`, yields it, and closes it afterwards (use `with`).
2. create_hero(session, data): convert the HeroCreate into a `Hero` row with
   `Hero.model_validate(data)`, add, commit, refresh, and return the row (id populated).
3. list_heroes(session, offset=0, limit=100): heroes ordered by id, using `select()` with
   `.offset()` / `.limit()`, executed with `session.exec(...)`. Return a list.
4. update_hero(session, hero_id, data): return None if the hero does not exist. Otherwise
   apply ONLY the fields the client sent (`data.model_dump(exclude_unset=True)` +
   `hero.sqlmodel_update(...)`), commit, refresh and return the row.
5. delete_hero(session, hero_id): delete the hero and return True; return False if missing.

The routes in `create_app` call these helpers and use `response_model=HeroPublic`, so
`secret_name` is never returned to clients.

Run: uv run pytest t04_fastapi_backend -k ex_21
"""

from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, select  # noqa: F401


class HeroBase(SQLModel):
    name: str = Field(index=True, min_length=1)
    age: int | None = Field(default=None, index=True, ge=0)


class Hero(HeroBase, table=True):
    # Distinct table name: SQLModel.metadata is process-global.
    __tablename__ = "ex21_hero"

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


def make_session_dependency(engine: Engine) -> Callable[[], Iterator[Session]]:
    raise NotImplementedError


def create_hero(session: Session, data: HeroCreate) -> Hero:
    raise NotImplementedError


def list_heroes(session: Session, offset: int = 0, limit: int = 100) -> list[Hero]:
    raise NotImplementedError


def update_hero(session: Session, hero_id: int, data: HeroUpdate) -> Hero | None:
    raise NotImplementedError


def delete_hero(session: Session, hero_id: int) -> bool:
    raise NotImplementedError


def create_app(engine: Engine) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        SQLModel.metadata.create_all(engine)
        yield

    app = FastAPI(title="Exercise 21", lifespan=lifespan)
    get_session = make_session_dependency(engine)
    SessionDep = Annotated[Session, Depends(get_session)]

    @app.post("/heroes/", response_model=HeroPublic, status_code=201)
    def post_hero(hero: HeroCreate, session: SessionDep) -> Hero:
        return create_hero(session, hero)

    @app.get("/heroes/", response_model=list[HeroPublic])
    def get_heroes(
        session: SessionDep,
        offset: int = 0,
        limit: Annotated[int, Query(le=100)] = 100,
    ) -> list[Hero]:
        return list_heroes(session, offset, limit)

    @app.get("/heroes/{hero_id}", response_model=HeroPublic)
    def get_hero(hero_id: int, session: SessionDep) -> Hero:
        hero = session.get(Hero, hero_id)
        if hero is None:
            raise HTTPException(status_code=404, detail="Hero not found")
        return hero

    @app.patch("/heroes/{hero_id}", response_model=HeroPublic)
    def patch_hero(hero_id: int, hero: HeroUpdate, session: SessionDep) -> Hero:
        updated = update_hero(session, hero_id, hero)
        if updated is None:
            raise HTTPException(status_code=404, detail="Hero not found")
        return updated

    @app.delete("/heroes/{hero_id}")
    def remove_hero(hero_id: int, session: SessionDep) -> dict[str, bool]:
        if not delete_hero(session, hero_id):
            raise HTTPException(status_code=404, detail="Hero not found")
        return {"ok": True}

    return app
