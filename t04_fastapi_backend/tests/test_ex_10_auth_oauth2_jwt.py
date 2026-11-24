from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jwt")
import jwt
from fastapi.testclient import TestClient

from _loader import load

ex = load("t04_fastapi_backend", "ex_10_auth_oauth2_jwt")
SECRET = "unit-test-secret-key-0123456789-abcdef"


@pytest.fixture
def client():
    ex.seed_users()
    yield TestClient(ex.app)
    ex.USERS.clear()


def test_password_hashing():
    h1 = ex.hash_password("hunter2hunter2")
    h2 = ex.hash_password("hunter2hunter2")
    assert h1 != "hunter2hunter2" and h1 != h2  # salted
    assert ex.verify_password("hunter2hunter2", h1)
    assert not ex.verify_password("wrong", h1)


def test_create_access_token_claims():
    now = datetime(2020, 1, 1, tzinfo=UTC)
    token = ex.create_access_token("ada", SECRET, timedelta(minutes=5), now=now)
    claims = jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_exp": False})
    assert claims["sub"] == "ada"
    assert claims["iat"] == int(now.timestamp())
    assert claims["exp"] == int((now + timedelta(minutes=5)).timestamp())
    assert jwt.get_unverified_header(token)["alg"] == "HS256"


def test_create_access_token_default_expiry_about_30_minutes():
    token = ex.create_access_token("ada", SECRET)
    claims = jwt.decode(token, SECRET, algorithms=["HS256"])
    assert 29 * 60 <= claims["exp"] - claims["iat"] <= 31 * 60


def test_decode_token_roundtrip():
    assert ex.decode_token(ex.create_access_token("ada", SECRET), SECRET) == "ada"


def test_decode_token_rejects_bad_tokens():
    with pytest.raises(ex.AuthError):
        ex.decode_token(ex.create_access_token("ada", SECRET, timedelta(seconds=-10)), SECRET)
    with pytest.raises(ex.AuthError):
        ex.decode_token(
            ex.create_access_token("ada", "another-secret-key-0123456789-abcdef"), SECRET
        )
    with pytest.raises(ex.AuthError):
        ex.decode_token("not.a.jwt", SECRET)
    no_sub = jwt.encode({"exp": datetime.now(UTC) + timedelta(minutes=1)}, SECRET, "HS256")
    with pytest.raises(ex.AuthError):
        ex.decode_token(no_sub, SECRET)


def test_decode_token_rejects_other_algorithms():
    # A token signed with HS512 must not be accepted when we expect HS256.
    other = jwt.encode({"sub": "ada"}, SECRET, algorithm="HS512")
    with pytest.raises(ex.AuthError):
        ex.decode_token(other, SECRET)


def test_authenticate():
    users = {"ada": {"username": "ada", "password_hash": ex.hash_password("pw-pw-pw-pw")}}
    assert ex.authenticate(users, "ada", "pw-pw-pw-pw") is users["ada"]
    assert ex.authenticate(users, "ada", "nope") is None
    assert ex.authenticate(users, "bob", "pw-pw-pw-pw") is None


def test_login_and_me(client):
    r = client.post("/token", data={"username": "ada", "password": "analytical-engine"})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"
    token = r.json()["access_token"]
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json() == {"username": "ada"}


def test_login_wrong_password(client):
    r = client.post("/token", data={"username": "ada", "password": "bad"})
    assert r.status_code == 401


def test_me_requires_valid_token(client):
    assert client.get("/users/me").status_code == 401
    r = client.get("/users/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401
    assert r.json() == {"detail": "Could not validate credentials"}
    assert r.headers["www-authenticate"] == "Bearer"


def test_me_rejects_expired_and_unknown_user(client):
    expired = ex.create_access_token("ada", ex.SECRET_KEY, timedelta(seconds=-5))
    r = client.get("/users/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401
    ghost = ex.create_access_token("ghost", ex.SECRET_KEY)
    r = client.get("/users/me", headers={"Authorization": f"Bearer {ghost}"})
    assert r.status_code == 401
