"""Exercise 07: SQLAlchemy 2.0 ORM.

Models and the app factory are written for you. Implement the data-access functions.
Tests use an in-memory SQLite database (StaticPool).

Tasks
1. add_project(session, name): insert a Project, commit, return it (with its id populated).
2. add_task(session, project_id, title): insert a Task for that project and return it.
   Raise LookupError("project not found") if the project does not exist.
3. list_tasks(session, project_id, done=None): tasks of a project ordered by id, using
   `select()`. If `done` is not None, filter on it.
4. task_counts(session): {project name: number of tasks} for EVERY project, including those
   with zero tasks. Do it in SQL (outer join + group by + count), not in a Python loop.
5. make_session_dependency(factory): return a generator function (a yield dependency) that
   opens a session from `factory`, yields it, rolls back if an exception is thrown into it,
   and always closes it. `create_app` below uses it for the /projects/{id}/tasks route.

Run: uv run pytest t04_fastapi_backend -k ex_07
"""

from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import ForeignKey, String, func, select  # noqa: F401
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    tasks: Mapped[list[Task]] = relationship(back_populates="project")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    done: Mapped[bool] = mapped_column(default=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    project: Mapped[Project] = relationship(back_populates="tasks")


def add_project(session: Session, name: str) -> Project:
    raise NotImplementedError


def add_task(session: Session, project_id: int, title: str) -> Task:
    raise NotImplementedError


def list_tasks(session: Session, project_id: int, done: bool | None = None) -> list[Task]:
    raise NotImplementedError


def task_counts(session: Session) -> dict[str, int]:
    raise NotImplementedError


def make_session_dependency(factory: sessionmaker[Session]) -> Callable[[], Iterator[Session]]:
    raise NotImplementedError


def create_app(factory: sessionmaker[Session]) -> FastAPI:
    app = FastAPI(title="Exercise 07")
    get_session = make_session_dependency(factory)

    @app.get("/projects/{project_id}/tasks")
    def project_tasks(
        project_id: int,
        session: Annotated[Session, Depends(get_session)],
        done: bool | None = None,
    ) -> list[dict[str, object]]:
        tasks = list_tasks(session, project_id, done)
        return [{"id": t.id, "title": t.title, "done": t.done} for t in tasks]

    return app
