import importlib
from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jwt")
import jwt
from fastapi.testclient import TestClient

from _loader import load

ex = load("t04_fastapi_backend", "ex_10_auth_oauth2_jwt")
lesson = importlib.import_module("t04_fastapi_backend.m_10_auth_oauth2_jwt")
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
    assert h1.startswith("$argon2id$")  # the id variant (not plain argon2i/argon2d)
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


def test_decode_token_requires_exp_iat_and_sub():
    """A signed token without `exp` would otherwise be valid forever."""
    now = datetime.now(UTC)
    no_exp = jwt.encode({"sub": "ada", "iat": now}, SECRET, algorithm="HS256")
    with pytest.raises(ex.AuthError):
        ex.decode_token(no_exp, SECRET)
    no_iat = jwt.encode({"sub": "ada", "exp": now + timedelta(minutes=5)}, SECRET, "HS256")
    with pytest.raises(ex.AuthError):
        ex.decode_token(no_iat, SECRET)
    bare = jwt.encode({"sub": "ada"}, SECRET, algorithm="HS256")
    with pytest.raises(ex.AuthError):
        ex.decode_token(bare, SECRET)


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


# ---- the lesson itself (m_10): secret handling and claim requirements ---------------------
def test_lesson_missing_secret_outside_dev_is_an_error(monkeypatch):
    """Importing is fine; the first sign/verify without a key raises (no committed fallback)."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    for env in ("prod", "staging", ""):
        monkeypatch.setenv("APP_ENV", env)
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            lesson.create_access_token("ada")
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            lesson.decode_token("a.b.c")
    monkeypatch.delenv("APP_ENV")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):  # APP_ENV unset is NOT "dev"
        lesson.create_access_token("ada")


def test_lesson_dev_fallback_requires_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "dev")
    with pytest.warns(UserWarning, match="INSECURE"):
        token = lesson.create_access_token("ada")
    with pytest.warns(UserWarning, match="INSECURE"):
        assert lesson.decode_token(token) == "ada"


def test_lesson_configured_secret_is_used(monkeypatch):
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("SECRET_KEY", SECRET)
    token = lesson.create_access_token("ada")
    assert jwt.decode(token, SECRET, algorithms=["HS256"])["sub"] == "ada"
    assert lesson.decode_token(token) == "ada"


def test_lesson_rejects_token_without_exp(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", SECRET)
    forever = jwt.encode({"sub": "ada", "iat": datetime.now(UTC)}, SECRET, algorithm="HS256")
    with pytest.raises(jwt.InvalidTokenError):
        lesson.decode_token(forever)
