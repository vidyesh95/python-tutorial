import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from _loader import load

ex = load("t04_fastapi_backend", "ex_07_sqlalchemy_2_orm")


@pytest.fixture
def factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    ex.Base.metadata.create_all(engine)
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def session(factory):
    with factory() as s:
        yield s


def test_add_project(session):
    p = ex.add_project(session, "Alpha")
    assert p.id is not None and p.name == "Alpha"
    assert session.get(ex.Project, p.id).name == "Alpha"


def test_add_task_and_missing_project(session):
    p = ex.add_project(session, "Alpha")
    t = ex.add_task(session, p.id, "write tests")
    assert t.id is not None and t.done is False and t.project_id == p.id
    with pytest.raises(LookupError):
        ex.add_task(session, 999, "orphan")


def test_list_tasks_filter_and_order(session):
    a = ex.add_project(session, "A")
    b = ex.add_project(session, "B")
    t1 = ex.add_task(session, a.id, "one")
    t2 = ex.add_task(session, a.id, "two")
    ex.add_task(session, b.id, "other project")
    t2.done = True
    session.commit()
    assert [t.title for t in ex.list_tasks(session, a.id)] == ["one", "two"]
    assert [t.id for t in ex.list_tasks(session, a.id, done=True)] == [t2.id]
    assert [t.id for t in ex.list_tasks(session, a.id, done=False)] == [t1.id]
    assert ex.list_tasks(session, 12345) == []


def test_task_counts_includes_empty_projects(session):
    a = ex.add_project(session, "A")
    ex.add_project(session, "Empty")
    ex.add_task(session, a.id, "x")
    ex.add_task(session, a.id, "y")
    assert ex.task_counts(session) == {"A": 2, "Empty": 0}


def test_session_dependency_closes(factory):
    dep = ex.make_session_dependency(factory)
    gen = dep()
    s = next(gen)
    ex.add_project(s, "P")
    with pytest.raises(StopIteration):
        next(gen)
    # After close, the session is reusable but holds no open transaction.
    assert not s.in_transaction()


def test_session_dependency_rolls_back_on_error(factory):
    dep = ex.make_session_dependency(factory)
    gen = dep()
    s = next(gen)
    s.add(ex.Project(name="never committed"))
    s.flush()
    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("boom"))
    with factory() as check:
        assert ex.task_counts(check) == {}


def test_route_uses_dependency(factory):
    with factory() as s:
        p = ex.add_project(s, "A")
        ex.add_task(s, p.id, "one")
        t = ex.add_task(s, p.id, "two")
        t.done = True
        s.commit()
        pid = p.id
    client = TestClient(ex.create_app(factory))
    r = client.get(f"/projects/{pid}/tasks")
    assert [x["title"] for x in r.json()] == ["one", "two"]
    r = client.get(f"/projects/{pid}/tasks", params={"done": "true"})
    assert [x["title"] for x in r.json()] == ["two"]
