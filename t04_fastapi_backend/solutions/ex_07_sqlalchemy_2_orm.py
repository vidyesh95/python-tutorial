"""Reference solution for Exercise 07: SQLAlchemy 2.0 ORM."""

from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import ForeignKey, String, func, select
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
    tasks: Mapped[list["Task"]] = relationship(back_populates="project")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    done: Mapped[bool] = mapped_column(default=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    project: Mapped[Project] = relationship(back_populates="tasks")


def add_project(session: Session, name: str) -> Project:
    project = Project(name=name)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def add_task(session: Session, project_id: int, title: str) -> Task:
    if session.get(Project, project_id) is None:
        raise LookupError("project not found")
    task = Task(title=title, project_id=project_id)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def list_tasks(session: Session, project_id: int, done: bool | None = None) -> list[Task]:
    stmt = select(Task).where(Task.project_id == project_id).order_by(Task.id)
    if done is not None:
        stmt = stmt.where(Task.done == done)
    return list(session.scalars(stmt))


def task_counts(session: Session) -> dict[str, int]:
    stmt = (
        select(Project.name, func.count(Task.id))
        .join(Task, Task.project_id == Project.id, isouter=True)
        .group_by(Project.id)
        .order_by(Project.id)
    )
    return {name: count for name, count in session.execute(stmt)}


def make_session_dependency(factory: sessionmaker[Session]) -> Callable[[], Iterator[Session]]:
    def get_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return get_session


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
