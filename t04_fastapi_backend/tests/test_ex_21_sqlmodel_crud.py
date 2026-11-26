import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlmodel")
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from _loader import load

ex = load("t04_fastapi_backend", "ex_21_sqlmodel_crud")


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(engine):
    with TestClient(ex.create_app(engine)) as c:
        yield c


def hero(name="Deadpond", age=30, secret="Dive Wilson"):
    return {"name": name, "age": age, "secret_name": secret}


def test_create_hero_helper(session):
    h = ex.create_hero(session, ex.HeroCreate(name="A", age=1, secret_name="s"))
    assert h.id is not None and h.name == "A" and h.secret_name == "s"
    assert session.get(ex.Hero, h.id).age == 1


def test_list_heroes_helper_order_offset_limit(session):
    for n in "abcde":
        ex.create_hero(session, ex.HeroCreate(name=n, secret_name="s"))
    assert [h.name for h in ex.list_heroes(session)] == list("abcde")
    assert [h.name for h in ex.list_heroes(session, offset=1, limit=2)] == ["b", "c"]
    assert ex.list_heroes(session, offset=10) == []


def test_update_and_delete_helpers(session):
    h = ex.create_hero(session, ex.HeroCreate(name="A", age=5, secret_name="s"))
    updated = ex.update_hero(session, h.id, ex.HeroUpdate(age=6))
    assert updated.age == 6 and updated.name == "A"
    assert ex.update_hero(session, 999, ex.HeroUpdate(age=1)) is None
    assert ex.delete_hero(session, h.id) is True
    assert ex.delete_hero(session, h.id) is False


def test_session_dependency_closes(engine):
    gen = ex.make_session_dependency(engine)()
    s = next(gen)
    assert isinstance(s, Session)
    ex.create_hero(s, ex.HeroCreate(name="A", secret_name="s"))
    with pytest.raises(StopIteration):
        next(gen)
    assert not s.in_transaction()


def test_create_hero_route_hides_secret(client):
    r = client.post("/heroes/", json=hero())
    assert r.status_code == 201
    body = r.json()
    assert body == {"id": 1, "name": "Deadpond", "age": 30}
    assert "secret_name" not in body


def test_read_one_and_404(client):
    hero_id = client.post("/heroes/", json=hero()).json()["id"]
    r = client.get(f"/heroes/{hero_id}")
    assert r.status_code == 200 and r.json()["name"] == "Deadpond"
    assert "secret_name" not in r.json()
    assert client.get("/heroes/999").status_code == 404


def test_list_pagination(client):
    for i in range(5):
        client.post("/heroes/", json=hero(name=f"h{i}"))
    assert len(client.get("/heroes/").json()) == 5
    page = client.get("/heroes/", params={"offset": 1, "limit": 2}).json()
    assert [h["name"] for h in page] == ["h1", "h2"]
    assert all("secret_name" not in h for h in page)
    assert client.get("/heroes/", params={"offset": 5}).json() == []


def test_limit_above_100_is_422(client):
    assert client.get("/heroes/", params={"limit": 101}).status_code == 422


def test_patch_partial_update_keeps_other_fields(client, engine):
    hero_id = client.post("/heroes/", json=hero()).json()["id"]
    r = client.patch(f"/heroes/{hero_id}", json={"age": 31})
    assert r.status_code == 200
    assert r.json() == {"id": hero_id, "name": "Deadpond", "age": 31}
    with Session(engine) as s:
        assert s.get(ex.Hero, hero_id).secret_name == "Dive Wilson"  # untouched
    # An explicit null IS a sent field, so it clears the value.
    assert client.patch(f"/heroes/{hero_id}", json={"age": None}).json()["age"] is None
    assert client.patch("/heroes/999", json={"age": 1}).status_code == 404


def test_delete(client):
    hero_id = client.post("/heroes/", json=hero()).json()["id"]
    r = client.delete(f"/heroes/{hero_id}")
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert client.get(f"/heroes/{hero_id}").status_code == 404
    assert client.delete(f"/heroes/{hero_id}").status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "NoSecret"},
        {"name": "", "secret_name": "s"},
        {"name": "Old", "age": -1, "secret_name": "s"},
        {"name": "Bad", "age": "old", "secret_name": "s"},
    ],
)
def test_validation_422(client, payload):
    assert client.post("/heroes/", json=payload).status_code == 422
    assert client.get("/heroes/").json() == []


def test_each_client_gets_a_fresh_database(client):
    assert client.get("/heroes/").json() == []
