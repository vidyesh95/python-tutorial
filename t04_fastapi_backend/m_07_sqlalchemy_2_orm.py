# SQLAlchemy 2.0 ORM
"""
SQLAlchemy maps Python classes to tables. The 2.0 style is fully typed:

- `class Base(DeclarativeBase)`: the registry/base for all models.
- `Mapped[int]` + `mapped_column(...)`: a typed column. `Mapped[str | None]` = nullable.
- `relationship(back_populates=...)`: navigate between objects (`author.books`).
- ENGINE = connection pool + dialect. SESSION = a unit of work (identity map + transaction).
  `sessionmaker(engine)` is a factory; use ONE SESSION PER REQUEST.
- Queries use `select()`: `session.scalars(select(User).where(User.id == 1)).all()`;
  `session.get(User, 1)` is the shortcut for primary-key lookup.
- Writes: `session.add(obj)`, then `session.commit()` (flush + COMMIT) or `session.rollback()`.
- `selectinload(...)` eager-loads a relationship in one extra query (avoids the N+1 trap).

SQLite in memory: every new connection to "sqlite://" would get its own EMPTY database, so
we use `StaticPool` (one shared connection) + `check_same_thread=False` (FastAPI runs sync
handlers in worker threads). This is a testing/demo setup, not a production one.

Serve it live:  uv run fastapi dev t04_fastapi_backend/m_07_sqlalchemy_2_orm.py
Run the offline demo: uv run python -m t04_fastapi_backend.m_07_sqlalchemy_2_orm
"""

from collections.abc import Iterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict
from sqlalchemy import ForeignKey, String, create_engine, func, select
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    selectinload,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool


# Example: models
class Base(DeclarativeBase):
    pass


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    books: Mapped[list[Book]] = relationship(back_populates="author", cascade="all, delete-orphan")


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    year: Mapped[int | None] = mapped_column(default=None)  # nullable
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"))
    author: Mapped[Author] = relationship(back_populates="books")


# Example: engine + session factory
engine = create_engine(
    "sqlite://",  # in-memory
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


# Example: session-per-request dependency (commit in handlers, rollback on error)
def get_session() -> Iterator[Session]:
    with SessionLocal() as session:  # closes the session at the end
        try:
            yield session
        except Exception:
            session.rollback()
            raise


SessionDep = Annotated[Session, Depends(get_session)]


# Pydantic schemas (from_attributes lets them read ORM objects)
class BookIn(BaseModel):
    title: str
    year: int | None = None


class BookOut(BookIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AuthorIn(BaseModel):
    name: str


class AuthorOut(AuthorIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    books: list[BookOut] = []


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)  # fine for demos; real apps use Alembic (lesson 08)
    yield


app = FastAPI(title="Library ORM", lifespan=lifespan)


@app.post("/authors", response_model=AuthorOut, status_code=201)
def create_author(data: AuthorIn, session: SessionDep) -> Author:
    if session.scalar(select(Author).where(Author.name == data.name)):
        raise HTTPException(409, "Author exists")
    author = Author(name=data.name)
    session.add(author)
    session.commit()
    return author


@app.post("/authors/{author_id}/books", response_model=BookOut, status_code=201)
def add_book(author_id: int, data: BookIn, session: SessionDep) -> Book:
    author = session.get(Author, author_id)  # primary-key lookup
    if author is None:
        raise HTTPException(404, "Author not found")
    book = Book(**data.model_dump(), author=author)  # sets author_id via the relationship
    session.add(book)
    session.commit()
    return book


@app.get("/authors/{author_id}", response_model=AuthorOut)
def read_author(author_id: int, session: SessionDep) -> Author:
    stmt = select(Author).where(Author.id == author_id).options(selectinload(Author.books))
    author = session.scalars(stmt).first()
    if author is None:
        raise HTTPException(404, "Author not found")
    return author


@app.get("/books", response_model=list[BookOut])
def search_books(session: SessionDep, title: str | None = None, limit: int = 20):
    stmt = select(Book).order_by(Book.id).limit(limit)
    if title:
        stmt = stmt.where(Book.title.ilike(f"%{title}%"))
    return session.scalars(stmt).all()


@app.get("/stats")
def stats(session: SessionDep) -> dict[str, int]:
    # Aggregate in SQL, not in Python: SELECT authors.name, count(books.id) ... GROUP BY
    rows = session.execute(
        select(Author.name, func.count(Book.id)).join(Book, isouter=True).group_by(Author.id)
    ).all()
    return {name: count for name, count in rows}


"""
Common mistakes:
- Sharing one global Session between requests/threads: sessions are NOT thread-safe.
- Forgetting `commit()` - changes vanish when the session closes.
- Lazy-loading relationships after the session closed (DetachedInstanceError). Eager-load
  (`selectinload`) what the response needs, or set `expire_on_commit=False`.
- N+1 queries: looping over authors and touching `author.books` fires one query each.
- Using the legacy 1.x `session.query(...)` style instead of `select()`.
- In-memory SQLite without StaticPool: tables "disappear" because each connection is new.

Production notes:
- Create the engine once per process; tune `pool_size`/`pool_pre_ping=True` for Postgres.
- Don't call `create_all` in production: use migrations (next lesson).
- Return ORM objects only through response models; never expose columns by accident.
- Async stack: `create_async_engine("sqlite+aiosqlite://")`/`AsyncSession` for fully async
  handlers; keep sync SQLAlchemy in plain `def` handlers (runs in the thread pool).
- Add indexes for columns you filter on (`mapped_column(index=True)`), and unique constraints
  in the DB - app-level "check then insert" races under concurrency.
"""

if __name__ == "__main__":
    with TestClient(app) as client:  # `with` runs the lifespan -> tables get created
        a = client.post("/authors", json={"name": "Ursula Le Guin"}).json()
        print(a)
        client.post(f"/authors/{a['id']}/books", json={"title": "The Dispossessed", "year": 1974})
        client.post(f"/authors/{a['id']}/books", json={"title": "A Wizard of Earthsea"})
        client.post("/authors", json={"name": "Nobody"})
        print(client.get(f"/authors/{a['id']}").json())
        print(client.get("/books", params={"title": "wizard"}).json())
        print(client.get("/stats").json())
        print(client.post("/authors", json={"name": "Nobody"}).status_code)  # 409
        print(client.get("/authors/99").status_code)  # 404
