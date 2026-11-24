import base64
import hashlib
import importlib
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import sessionmaker

from _loader import load

ex = load("t04_fastapi_backend", "ex_20_auth_schema_sessions")
# The lesson itself (m_20): it has extra hardening (OAuth state/PKCE, signed-out link rules,
# password-reset rules, secret handling) that the smaller exercise app does not.
lesson = importlib.import_module("t04_fastapi_backend.m_20_auth_schema_sessions")

PASSWORD = "correct-horse-battery"
EMAIL = "ada@example.com"
ORIGIN = {"Origin": "https://app.example.com"}  # cookie routes demand a trusted Origin


class Clock:
    """Controllable clock: tests advance time instead of sleeping."""

    def __init__(self) -> None:
        self.now = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)

    def advance(self, **kwargs: float) -> None:
        self.now += timedelta(**kwargs)


@contextmanager
def open_env(mod, *, alembic: bool = False):
    """A fresh in-memory database + fake clock wired into `mod.app` (exercise app or lesson)."""
    engine = mod.make_engine()
    if alembic:
        mod.migrate(engine)  # the lesson's schema comes from its Alembic migration
    else:
        mod.Base.metadata.create_all(engine)
    session_local = sessionmaker(engine, expire_on_commit=False)
    clock = Clock()

    def override_db():
        with session_local() as db:
            yield db

    mod.app.dependency_overrides[mod.get_db] = override_db
    mod.app.dependency_overrides[mod.get_now] = lambda: clock.now
    mod.OUTBOX.clear()
    mod.reset_rate_limits()
    with TestClient(mod.app, base_url="https://testserver", headers=ORIGIN) as client:
        yield SimpleNamespace(
            mod=mod, client=client, clock=clock, session_local=session_local, engine=engine
        )
    mod.app.dependency_overrides.clear()
    mod.OUTBOX.clear()
    mod.reset_rate_limits()


@pytest.fixture
def env():
    with open_env(ex) as e:
        yield e


@pytest.fixture(params=["ex", "lesson"])
def both(request):
    """The same test against the exercise/solution app AND the lesson app."""
    with open_env(ex) if request.param == "ex" else open_env(lesson, alembic=True) as e:
        yield e


@pytest.fixture
def lesson_env():
    with open_env(lesson, alembic=True) as e:
        yield e


@pytest.fixture
def db(env):
    with env.session_local() as session:
        yield session


def make_user(db, email=EMAIL, verified=False):
    user = ex.User(name="Ada", email=email, email_verified=verified)
    db.add(user)
    db.flush()
    return user


def register(env, email=EMAIL):
    r = env.client.post("/auth/sign-up", json={"name": "Ada", "email": email, "password": PASSWORD})
    assert r.status_code == 201
    return r.json()


def count(env, model, *where):
    with env.session_local() as db:
        return db.scalar(select(func.count()).select_from(model).where(*where))


def dump_database(env) -> str:
    """Every value of every row of every table, as one searchable string."""
    parts = []
    with env.session_local() as db:
        for table in ex.Base.metadata.sorted_tables:
            parts += [str(value) for row in db.execute(select(table)) for value in row]
    return "\n".join(parts)


# ---- task 1: hash_token ----------------------------------------------------------------
def test_hash_token_is_sha256_hex():
    assert ex.hash_token("abc") == hashlib.sha256(b"abc").hexdigest()
    assert len(ex.hash_token("another")) == 64


# ---- task 2: create_session --------------------------------------------------------------
def test_create_session_stores_only_the_hash(env, db):
    user = make_user(db)
    now = env.clock.now
    raw = ex.create_session(db, user.id, now=now, ip_address="203.0.113.9", user_agent="pytest")
    db.commit()
    row = db.scalar(select(ex.UserSession))
    assert row.token_hash == ex.hash_token(raw) and row.token_hash != raw
    assert row.user_id == user.id
    assert row.expires_at == now + ex.SESSION_TTL
    assert row.created_at == now and row.updated_at == now
    assert (row.ip_address, row.user_agent) == ("203.0.113.9", "pytest")
    assert raw not in dump_database(env)
    assert len(raw) >= 32


def test_create_session_tokens_are_unique(env, db):
    user = make_user(db)
    tokens = {ex.create_session(db, user.id, now=env.clock.now) for _ in range(5)}
    assert len(tokens) == 5


# ---- task 3: get_valid_session -----------------------------------------------------------
def test_get_valid_session_accepts_a_live_token(env, db):
    user = make_user(db)
    raw = ex.create_session(db, user.id, now=env.clock.now)
    row = ex.get_valid_session(db, raw, now=env.clock.now + timedelta(days=6))
    assert row is not None and row.user_id == user.id


def test_get_valid_session_rejects_unknown_token(env, db):
    assert ex.get_valid_session(db, "no-such-token", now=env.clock.now) is None


def test_get_valid_session_rejects_expired_token(env, db):
    user = make_user(db)
    raw = ex.create_session(db, user.id, now=env.clock.now)
    expiry = env.clock.now + ex.SESSION_TTL
    assert ex.get_valid_session(db, raw, now=expiry - timedelta(seconds=1)) is not None
    assert ex.get_valid_session(db, raw, now=expiry) is None  # boundary: expired
    assert ex.get_valid_session(db, raw, now=expiry + timedelta(days=1)) is None


# ---- task 4: rotate_refresh_token --------------------------------------------------------
def test_rotate_refresh_token_issues_successor_in_same_family(env, db):
    user = make_user(db)
    old_raw, old_row = ex.issue_refresh_token(db, user.id, now=env.clock.now)
    env.clock.advance(minutes=20)
    user_id, new_raw = ex.rotate_refresh_token(db, old_raw, now=env.clock.now)
    db.commit()
    assert user_id == user.id and new_raw != old_raw
    new_row = db.scalar(
        select(ex.RefreshToken).where(ex.RefreshToken.token_hash == ex.hash_token(new_raw))
    )
    db.refresh(old_row)
    assert old_row.revoked_at == env.clock.now
    assert old_row.replaced_by == new_row.id
    assert new_row.family_id == old_row.family_id and new_row.revoked_at is None
    assert ex.rotate_refresh_token(db, new_raw, now=env.clock.now)[0] == user.id  # chain continues


def test_rotate_refresh_token_rejects_unknown_and_expired(env, db):
    user = make_user(db)
    with pytest.raises(ex.InvalidTokenError):
        ex.rotate_refresh_token(db, "nope", now=env.clock.now)
    raw, _ = ex.issue_refresh_token(db, user.id, now=env.clock.now)
    with pytest.raises(ex.InvalidTokenError):
        ex.rotate_refresh_token(db, raw, now=env.clock.now + ex.REFRESH_TTL)


def test_refresh_token_reuse_revokes_the_whole_family(env, db):
    user = make_user(db)
    t1, _ = ex.issue_refresh_token(db, user.id, now=env.clock.now)
    _, t2 = ex.rotate_refresh_token(db, t1, now=env.clock.now)
    _, t3 = ex.rotate_refresh_token(db, t2, now=env.clock.now)
    other_raw, other_row = ex.issue_refresh_token(db, user.id, now=env.clock.now)  # other device
    db.commit()
    with pytest.raises(ex.InvalidTokenError):  # the thief replays an old token
        ex.rotate_refresh_token(db, t1, now=env.clock.now)
    with env.session_local() as fresh:  # the revocation was COMMITTED despite the exception
        rows = fresh.scalars(select(ex.RefreshToken)).all()
        family = [r for r in rows if r.id != other_row.id]
        assert len(family) == 3 and all(r.revoked_at is not None for r in family)
        assert fresh.get(ex.RefreshToken, other_row.id).revoked_at is None  # other login untouched
    with pytest.raises(ex.InvalidTokenError):  # even the newest legitimate token is dead
        ex.rotate_refresh_token(db, t3, now=env.clock.now)
    assert ex.rotate_refresh_token(db, other_raw, now=env.clock.now)[0] == user.id


# ---- task 5: consume_verification --------------------------------------------------------
def test_consume_verification_is_single_use(env, db):
    token = ex.issue_verification(
        db, "email-verify:ada@example.com", ex.VERIFY_TTL, now=env.clock.now
    )
    db.commit()
    assert (
        ex.consume_verification(db, token, "email-verify:", now=env.clock.now) == "ada@example.com"
    )
    db.commit()
    assert ex.consume_verification(db, token, "email-verify:", now=env.clock.now) is None
    assert count(env, ex.Verification) == 0


def test_consume_verification_expires(env, db):
    token = ex.issue_verification(db, "password-reset:u1", ex.RESET_TTL, now=env.clock.now)
    inside = env.clock.now + ex.RESET_TTL - timedelta(seconds=1)
    assert (
        ex.consume_verification(db, token, "password-reset:", now=env.clock.now + ex.RESET_TTL)
        is None
    )
    assert ex.consume_verification(db, token, "password-reset:", now=inside) == "u1"


def test_consume_verification_wrong_prefix_does_not_consume(env, db):
    token = ex.issue_verification(
        db, "email-verify:ada@example.com", ex.VERIFY_TTL, now=env.clock.now
    )
    assert ex.consume_verification(db, token, "password-reset:", now=env.clock.now) is None
    assert ex.consume_verification(db, "unknown-token", "email-verify:", now=env.clock.now) is None
    assert (
        ex.consume_verification(db, token, "email-verify:", now=env.clock.now) == "ada@example.com"
    )


# ---- task 6: link_oauth_account ----------------------------------------------------------
def profile(**overrides):
    base = {
        "provider_id": "github",
        "account_id": "gh-1",
        "email": "Ada@Example.com",
        "email_verified": True,
        "name": "Ada",
        "access_token": "at-1",
    }
    return ex.OAuthProfile(**{**base, **overrides})


def test_link_oauth_creates_new_user_and_account(env, db):
    user = ex.link_oauth_account(db, profile(email="New@Example.com"), now=env.clock.now)
    db.commit()
    assert user.email == "new@example.com" and user.email_verified is True
    account = db.scalar(select(ex.Account))
    assert (account.provider_id, account.account_id, account.user_id) == ("github", "gh-1", user.id)
    assert account.access_token == "at-1" and account.password is None


def test_link_oauth_returns_existing_account_and_updates_tokens(env, db):
    first = ex.link_oauth_account(db, profile(), now=env.clock.now)
    again = ex.link_oauth_account(
        db, profile(email="changed@example.com", access_token="at-2"), now=env.clock.now
    )
    db.commit()
    assert again.id == first.id
    assert count(env, ex.User) == 1 and count(env, ex.Account) == 1
    assert db.scalar(select(ex.Account.access_token)) == "at-2"


def test_link_oauth_links_verified_matching_email(env, db):
    user = make_user(db, verified=True)
    linked = ex.link_oauth_account(db, profile(), now=env.clock.now)
    db.commit()
    assert linked.id == user.id and count(env, ex.User) == 1
    assert db.scalar(select(ex.Account.user_id)) == user.id


def test_unverified_provider_email_does_not_link_to_existing_user(env, db):
    make_user(db, verified=True)
    db.commit()
    with pytest.raises(ex.OAuthLinkError):
        ex.link_oauth_account(db, profile(email_verified=False), now=env.clock.now)
    db.rollback()
    assert count(env, ex.User) == 1 and count(env, ex.Account) == 0


def test_verified_oauth_login_evicts_unverified_password_owner(env, db):
    """Pre-hijacking: the attacker pre-registered the victim's email with their own password."""
    user = make_user(db, verified=False)
    db.add(ex.Account(user_id=user.id, provider_id="credential", account_id=user.id, password="x"))
    attacker_session = ex.create_session(db, user.id, now=env.clock.now)
    db.commit()
    linked = ex.link_oauth_account(db, profile(), now=env.clock.now)
    db.commit()
    assert linked.id == user.id and linked.email_verified is True
    assert count(env, ex.Account, ex.Account.provider_id == "credential") == 0
    assert ex.get_valid_session(db, attacker_session, now=env.clock.now) is None


# ---- end to end through the HTTP API -----------------------------------------------------
def test_password_is_stored_as_argon2id_hash(env):
    register(env)
    with env.session_local() as db:
        stored = db.scalar(
            select(ex.Account.password).where(ex.Account.provider_id == "credential")
        )
    assert stored.startswith("$argon2id$")
    assert PASSWORD not in stored


def test_database_never_contains_raw_tokens(env):
    register(env)
    verify_token = ex.OUTBOX[-1]["token"]
    assert (
        env.client.post("/auth/sign-in", json={"email": EMAIL, "password": PASSWORD}).status_code
        == 200
    )
    cookie_token = env.client.cookies.get(ex.COOKIE_NAME)
    pair = env.client.post("/auth/token", json={"email": EMAIL, "password": PASSWORD}).json()
    env.client.post("/auth/forgot-password", json={"email": EMAIL})
    reset_token = ex.OUTBOX[-1]["token"]
    stored = dump_database(env)
    for raw in (verify_token, cookie_token, pair["refresh_token"], reset_token):
        assert raw not in stored
        assert ex.hash_token(raw) in stored  # but their hashes are


def test_sign_in_sets_a_hardened_cookie_and_wrong_password_is_rejected(env):
    register(env)
    bad = env.client.post("/auth/sign-in", json={"email": EMAIL, "password": "wrong-password"})
    assert bad.status_code == 401 and "set-cookie" not in bad.headers
    unknown = env.client.post(
        "/auth/sign-in", json={"email": "who@example.com", "password": PASSWORD}
    )
    assert unknown.status_code == 401 and unknown.json() == bad.json()  # no enumeration
    ok = env.client.post("/auth/sign-in", json={"email": "ADA@example.com", "password": PASSWORD})
    cookie = ok.headers["set-cookie"].lower()
    assert ok.status_code == 200
    for flag in ("httponly", "secure", "samesite=lax", "path=/", "max-age="):
        assert flag in cookie
    assert env.client.get("/auth/me").json()["email"] == EMAIL


def test_expired_session_is_rejected_over_http(env):
    register(env)
    env.client.post("/auth/sign-in", json={"email": EMAIL, "password": PASSWORD})
    env.clock.advance(days=6)
    assert env.client.get("/auth/me").status_code == 200
    env.clock.advance(days=2)
    assert env.client.get("/auth/me").status_code == 401


def test_sign_in_rotates_the_session(env):
    register(env)
    env.client.post("/auth/sign-in", json={"email": EMAIL, "password": PASSWORD})
    first = env.client.cookies.get(ex.COOKIE_NAME)
    env.client.post("/auth/sign-in", json={"email": EMAIL, "password": PASSWORD})
    assert env.client.cookies.get(ex.COOKIE_NAME) != first
    assert count(env, ex.UserSession) == 1  # the old one was deleted, not left behind


def test_sign_out_clears_cookie_and_deletes_session(env):
    register(env)
    env.client.post("/auth/sign-in", json={"email": EMAIL, "password": PASSWORD})
    assert count(env, ex.UserSession) == 1
    out = env.client.post("/auth/sign-out")
    assert out.status_code == 200
    assert "max-age=0" in out.headers["set-cookie"].lower()
    assert env.client.cookies.get(ex.COOKIE_NAME) is None
    assert count(env, ex.UserSession) == 0
    assert env.client.get("/auth/me").status_code == 401


def test_email_verification_flow(env):
    register(env)
    token = ex.OUTBOX[-1]["token"]
    assert env.client.post("/auth/verify-email", json={"token": token}).json() == {"verified": True}
    assert (
        env.client.post("/auth/verify-email", json={"token": token}).status_code == 400
    )  # single use
    with env.session_local() as db:
        assert db.scalar(select(ex.User.email_verified)) is True


def test_email_verification_token_expires(env):
    register(env)
    env.clock.advance(hours=2)
    assert (
        env.client.post("/auth/verify-email", json={"token": ex.OUTBOX[-1]["token"]}).status_code
        == 400
    )


def test_forgot_password_does_not_reveal_whether_the_email_exists(env):
    register(env)
    known = env.client.post("/auth/forgot-password", json={"email": EMAIL})
    mails_after_known = len(ex.OUTBOX)
    unknown = env.client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert (known.status_code, known.json()) == (unknown.status_code, unknown.json())
    assert known.status_code == 202
    assert len(ex.OUTBOX) == mails_after_known  # nothing is mailed to unknown addresses


def test_password_reset_revokes_sessions_and_refresh_tokens(env):
    register(env)
    creds = {"email": EMAIL, "password": PASSWORD}
    env.client.post("/auth/sign-in", json=creds)
    pair = env.client.post("/auth/token", json=creds).json()
    env.client.post("/auth/forgot-password", json={"email": EMAIL})
    reset = {"token": ex.OUTBOX[-1]["token"], "new_password": "a-brand-new-passphrase"}
    assert env.client.post("/auth/reset-password", json=reset).status_code == 200
    assert count(env, ex.UserSession) == 0
    assert env.client.get("/auth/me").status_code == 401
    refresh = env.client.post("/auth/token/refresh", json={"refresh_token": pair["refresh_token"]})
    assert refresh.status_code == 401
    assert env.client.post("/auth/sign-in", json=creds).status_code == 401  # old password dead
    new = {"email": EMAIL, "password": "a-brand-new-passphrase"}
    assert env.client.post("/auth/sign-in", json=new).status_code == 200
    assert env.client.post("/auth/reset-password", json=reset).status_code == 400  # single use


def test_refresh_endpoint_rotates_and_detects_reuse(env):
    register(env)
    pair = env.client.post("/auth/token", json={"email": EMAIL, "password": PASSWORD}).json()
    second = env.client.post("/auth/token/refresh", json={"refresh_token": pair["refresh_token"]})
    assert second.status_code == 200 and second.json()["refresh_token"] != pair["refresh_token"]
    replay = env.client.post("/auth/token/refresh", json={"refresh_token": pair["refresh_token"]})
    assert replay.status_code == 401
    successor = env.client.post(
        "/auth/token/refresh", json={"refresh_token": second.json()["refresh_token"]}
    )
    assert successor.status_code == 401  # family revoked


def test_oauth_callback_links_only_verified_emails(env):
    register(env)
    env.client.post("/auth/verify-email", json={"token": ex.OUTBOX[-1]["token"]})
    evil = env.client.post("/auth/oauth/github/callback", json={"code": "code-evil"})
    assert evil.status_code == 409
    assert count(env, ex.UserSession) == 0 and count(env, ex.User) == 1
    good = env.client.post("/auth/oauth/google/callback", json={"code": "code-ada"})
    assert good.status_code == 200 and good.json()["email"] == EMAIL
    assert count(env, ex.User) == 1 and count(env, ex.Account) == 2  # password + google
    assert env.client.get("/auth/me").json()["email"] == EMAIL


# =========================================================================================
# Security regressions (audit). `both` runs a test on the exercise/solution app AND the lesson.
# =========================================================================================
def oauth_login(e, provider, code, *, state=None):
    """Drive the OAuth callback; the lesson app also needs the /start step (state cookie)."""
    body = {"code": code}
    if hasattr(e.mod, "OAUTH_STATE_COOKIE"):
        start = e.client.get(f"/auth/oauth/{provider}/start")
        assert start.status_code == 200
        body["state"] = state or parse_qs(urlparse(start.json()["authorize_url"]).query)["state"][0]
    return e.client.post(f"/auth/oauth/{provider}/callback", json=body)


def oauth_profile(mod, **overrides):
    base = {
        "provider_id": "github",
        "account_id": "gh-1",
        "email": "ada@example.com",
        "email_verified": True,
        "name": "Ada",
    }
    return mod.OAuthProfile(**{**base, **overrides})


def add_credential_user(e, db, *, verified, email=EMAIL):
    mod = e.mod
    user = mod.User(name="Ada", email=email, email_verified=verified)
    db.add(user)
    db.flush()
    db.add(mod.Account(user_id=user.id, provider_id="credential", account_id=user.id, password="x"))
    return user


# ---- 1. OAuth account takeover (unverified provider email, then a verified sign-in) --------
def test_oauth_takeover_sequence_is_blocked(both):
    """code-evil (unverified) -> victim signs in with google -> code-evil again."""
    e = both
    first = oauth_login(e, "github", "code-evil")
    assert first.status_code == 409  # an unverified provider email cannot claim the address
    assert count(e, e.mod.User) == 0 and count(e, e.mod.Account) == 0
    e.client.cookies.clear()
    victim = oauth_login(e, "google", "code-ada")
    assert victim.status_code == 200
    victim_id = victim.json()["id"]
    e.client.cookies.clear()
    again = oauth_login(e, "github", "code-evil")
    assert again.status_code == 409 and again.json().get("id") != victim_id
    assert e.client.cookies.get(e.mod.COOKIE_NAME) is None
    assert e.client.get("/auth/me").status_code == 401
    assert count(e, e.mod.Account, e.mod.Account.provider_id == "github") == 0


def test_unverified_provider_email_cannot_create_a_user(both):
    e = both
    with e.session_local() as db:
        with pytest.raises(e.mod.OAuthLinkError):
            e.mod.link_oauth_account(
                db,
                oauth_profile(e.mod, email="new@example.com", email_verified=False),
                now=e.clock.now,
            )
        db.rollback()
    assert count(e, e.mod.User) == 0


def test_verified_login_evicts_every_login_method_of_an_unverified_user(both):
    """Even a provider identity linked earlier (legacy data) is dropped, not just the password."""
    e = both
    mod = e.mod
    with e.session_local() as db:
        user = add_credential_user(e, db, verified=False)
        db.add(mod.Account(user_id=user.id, provider_id="github", account_id="gh-6666"))
        attacker_session = mod.create_session(db, user.id, now=e.clock.now)
        refresh_raw, _ = mod.issue_refresh_token(db, user.id, now=e.clock.now)
        db.commit()
        linked = mod.link_oauth_account(
            db, oauth_profile(mod, provider_id="google", account_id="g-42"), now=e.clock.now
        )
        db.commit()
        assert linked.id == user.id and linked.email_verified is True
        rows = db.execute(select(mod.Account.provider_id, mod.Account.account_id)).all()
        assert rows == [("google", "g-42")]  # password AND the attacker's github are gone
        assert mod.get_valid_session(db, attacker_session, now=e.clock.now) is None
        with pytest.raises(mod.InvalidTokenError):
            mod.rotate_refresh_token(db, refresh_raw, now=e.clock.now)
        with pytest.raises(mod.OAuthLinkError):  # the evicted identity cannot come back unverified
            mod.link_oauth_account(
                db,
                oauth_profile(mod, account_id="gh-6666", email_verified=False),
                now=e.clock.now,
            )


# ---- 2. brute-force limiter: atomic under concurrency, bounded memory -----------------------
def test_rate_limit_cap_holds_under_concurrency(both):
    mod, now = both.mod, both.clock.now
    sys.setswitchinterval(1e-6)  # make thread switches frequent: exposes any read/modify/write gap

    def attempt(_):
        try:
            mod.check_rate_limit("bob@example.com", now)
        except HTTPException as exc:
            return exc.status_code
        return 200

    try:
        with ThreadPoolExecutor(max_workers=64) as pool:
            codes = list(pool.map(attempt, range(400)))
    finally:
        sys.setswitchinterval(0.005)
    assert codes.count(200) == mod.MAX_FAILURES  # never more than the cap slip through
    assert codes.count(429) == 400 - mod.MAX_FAILURES
    assert len(mod._attempts["bob@example.com"]) == mod.MAX_FAILURES  # nothing lost either


def test_rate_limit_window_slides_and_memory_is_bounded(both, monkeypatch):
    mod, now = both.mod, both.clock.now
    for _ in range(mod.MAX_FAILURES):
        mod.check_rate_limit("bob@example.com", now)
    with pytest.raises(HTTPException) as blocked:
        mod.check_rate_limit("bob@example.com", now)
    assert blocked.value.status_code == 429
    mod.check_rate_limit("bob@example.com", now + mod.FAILURE_WINDOW)  # expired entries are pruned
    assert len(mod._attempts["bob@example.com"]) == 1
    monkeypatch.setattr(mod, "MAX_TRACKED_EMAILS", 50)
    for i in range(500):  # an attacker spraying distinct emails cannot grow memory without limit
        mod.check_rate_limit(f"user{i}@example.com", now)
    assert len(mod._attempts) <= 50
    assert "user499@example.com" in mod._attempts  # most recently used are the ones kept


def test_sign_in_is_throttled_even_with_the_right_password(both):
    e = both
    register(e)
    bad = {"email": EMAIL, "password": "wrong-password"}
    assert [e.client.post("/auth/sign-in", json=bad).status_code for _ in range(5)] == [401] * 5
    good = {"email": EMAIL, "password": PASSWORD}
    blocked = e.client.post("/auth/sign-in", json=good)
    assert blocked.status_code == 429 and "set-cookie" not in blocked.headers
    assert e.client.post("/auth/token", json=good).status_code == 429  # same limiter
    e.clock.advance(minutes=16)
    assert e.client.post("/auth/sign-in", json=good).status_code == 200


# ---- 9. CSRF Origin check and sign-up race --------------------------------------------------
def test_cookie_routes_reject_missing_or_untrusted_origin(both):
    e = both
    register(e)
    creds = {"email": EMAIL, "password": PASSWORD}
    no_origin = TestClient(e.mod.app, base_url="https://testserver")  # no Origin header at all
    for client, extra in ((e.client, {"Origin": "https://evil.example"}), (no_origin, {})):
        assert client.post("/auth/sign-in", json=creds, headers=extra).status_code == 403
        signup = {"name": "Eve", "email": "eve@example.com", "password": PASSWORD}
        assert client.post("/auth/sign-up", json=signup, headers=extra).status_code == 403
        assert client.post("/auth/sign-out", headers=extra).status_code == 403
    assert count(e, e.mod.User) == 1  # the forged sign-up created nothing
    assert e.client.post("/auth/sign-in", json=creds).status_code == 200  # trusted origin works


def test_duplicate_sign_up_is_a_409_not_a_500(both):
    e = both
    register(e)
    for email in (EMAIL, "ADA@Example.com"):  # same address, any case: unique index decides
        body = {"name": "Ada", "email": email, "password": PASSWORD}
        assert e.client.post("/auth/sign-up", json=body).status_code == 409
    assert count(e, e.mod.User) == 1 and count(e, e.mod.Account) == 1


# ---- 10. repeat provider logins must not wipe stored provider tokens ------------------------
def test_repeat_oauth_login_keeps_stored_provider_tokens(both):
    e = both
    mod = e.mod
    first = oauth_profile(
        mod, access_token="at-1", refresh_token="rt-1", id_token="id-1", scope="email"
    )
    with e.session_local() as db:
        mod.link_oauth_account(db, first, now=e.clock.now)
        db.commit()
        second = oauth_profile(mod, access_token="at-2")  # Google omits the refresh token now
        mod.link_oauth_account(db, second, now=e.clock.now)
        db.commit()
        account = db.scalar(select(mod.Account))
        assert account.access_token == "at-2"  # new values still replace old ones
        assert (account.refresh_token, account.id_token, account.scope) == ("rt-1", "id-1", "email")


# ---- 11. refresh tokens: replay after expiry, absolute family lifetime ----------------------
def test_replaying_an_expired_rotated_token_still_revokes_the_family(both):
    e = both
    mod = e.mod
    with e.session_local() as db:
        user = add_credential_user(e, db, verified=True)
        t1, _ = mod.issue_refresh_token(db, user.id, now=e.clock.now)
        _, t2 = mod.rotate_refresh_token(db, t1, now=e.clock.now)
        db.commit()
        late = e.clock.now + mod.REFRESH_TTL + timedelta(days=1)  # everything has expired by now
        with pytest.raises(mod.InvalidTokenError):
            mod.rotate_refresh_token(db, t1, now=late)  # t1 was already used: this is a replay
    with e.session_local() as fresh:  # reuse detection ran (and committed), expired or not
        assert all(r.revoked_at is not None for r in fresh.scalars(select(mod.RefreshToken)))


def test_refresh_family_has_an_absolute_lifetime(both):
    e = both
    mod = e.mod
    start = e.clock.now
    deadline = start + mod.REFRESH_FAMILY_TTL
    with e.session_local() as db:
        user = add_credential_user(e, db, verified=True)
        raw, first = mod.issue_refresh_token(db, user.id, now=start)
        assert first.family_expires_at == deadline
        assert first.expires_at == start + mod.REFRESH_TTL
        now, rotations = start, 0
        while now + timedelta(days=20) < deadline:  # a client that keeps refreshing every 20 days
            now += timedelta(days=20)
            _, raw = mod.rotate_refresh_token(db, raw, now=now)
            db.commit()
            row = db.scalar(
                select(mod.RefreshToken).where(mod.RefreshToken.token_hash == mod.hash_token(raw))
            )
            assert row.family_expires_at == deadline and row.expires_at <= deadline  # inherited
            rotations += 1
        assert rotations >= 3 and row.expires_at == deadline  # last token capped, not +30 days
        with pytest.raises(mod.InvalidTokenError):  # the chain cannot be extended past the cap
            mod.rotate_refresh_token(db, raw, now=deadline)


def test_family_deadline_is_enforced_even_if_the_token_looks_live(both):
    e = both
    mod = e.mod
    with e.session_local() as db:
        user = add_credential_user(e, db, verified=True)
        raw, row = mod.issue_refresh_token(db, user.id, now=e.clock.now)
        row.family_expires_at = e.clock.now + timedelta(days=1)  # e.g. the cap was lowered
        db.commit()
        assert row.expires_at > e.clock.now + timedelta(days=2)
        with pytest.raises(mod.InvalidTokenError):
            mod.rotate_refresh_token(db, raw, now=e.clock.now + timedelta(days=2))


# =========================================================================================
# The lesson itself (m_20 only): hardening that the small exercise app does not carry.
# =========================================================================================
# ---- 3. pre-hijacking through email verification --------------------------------------------
def test_lesson_verification_email_warns_the_real_owner(lesson_env):
    register(lesson_env)
    text = lesson.OUTBOX[-1]["text"].lower()
    assert "someone created an account" in text and "not you" in text and "reset" in text


def test_lesson_signed_out_oauth_link_removes_a_planted_password(lesson_env):
    e = lesson_env
    attacker = {"email": EMAIL, "password": "attacker-chosen-password"}
    e.client.post("/auth/sign-up", json={"name": "Ada", **attacker})
    victim_click = {"token": lesson.OUTBOX[-1]["token"]}  # the victim verifies the planted account
    assert e.client.post("/auth/verify-email", json=victim_click).status_code == 200
    assert e.client.post("/auth/sign-in", json=attacker).status_code == 200
    planted_session = e.client.cookies.get(lesson.COOKIE_NAME)
    e.client.cookies.clear()  # the victim's browser: signed out
    google = oauth_login(e, "google", "code-ada")
    assert google.status_code == 200
    assert e.client.post("/auth/sign-in", json=attacker).status_code == 401  # password is gone
    with e.session_local() as db:
        assert lesson.get_valid_session(db, planted_session, now=e.clock.now) is None
        providers = db.scalars(select(lesson.Account.provider_id)).all()
        assert providers == ["google"]
    # The legitimate owner recovers a password through the inbox: forgot + reset.
    e.client.post("/auth/forgot-password", json={"email": EMAIL})
    reset = {"token": lesson.OUTBOX[-1]["token"], "new_password": "the-owners-new-passphrase"}
    assert e.client.post("/auth/reset-password", json=reset).status_code == 200
    owner = {"email": EMAIL, "password": "the-owners-new-passphrase"}
    assert e.client.post("/auth/sign-in", json=owner).status_code == 200


def test_lesson_signed_in_owner_can_link_a_provider_and_keeps_their_password(lesson_env):
    e = lesson_env
    register(e)
    e.client.post("/auth/verify-email", json={"token": lesson.OUTBOX[-1]["token"]})
    creds = {"email": EMAIL, "password": PASSWORD}
    e.client.post("/auth/sign-in", json=creds)
    before = e.client.cookies.get(lesson.COOKIE_NAME)
    assert oauth_login(e, "google", "code-ada").status_code == 200
    assert count(e, lesson.Account) == 2  # password + google
    assert e.client.cookies.get(lesson.COOKIE_NAME) != before  # and the session was rotated
    assert count(e, lesson.UserSession) == 1
    assert e.client.post("/auth/sign-in", json=creds).status_code == 200


def test_lesson_oauth_only_user_is_not_logged_out_by_a_second_provider(lesson_env):
    e = lesson_env
    with e.session_local() as db:
        user = lesson.link_oauth_account(
            db, oauth_profile(lesson, provider_id="google"), now=e.clock.now
        )
        old = lesson.create_session(db, user.id, e.clock.now)
        db.commit()
        lesson.link_oauth_account(db, oauth_profile(lesson, account_id="gh-2"), now=e.clock.now)
        db.commit()
        assert lesson.get_valid_session(db, old, now=e.clock.now) is not None  # nothing to evict


# ---- 7. OAuth state (login CSRF) and PKCE, session rotation ---------------------------------
def test_lesson_oauth_callback_requires_the_matching_state(lesson_env):
    e = lesson_env
    post = e.client.post
    assert post("/auth/oauth/google/callback", json={"code": "code-ada"}).status_code == 400
    forged = {"code": "code-ada", "state": "attacker-state"}
    assert post("/auth/oauth/google/callback", json=forged).status_code == 400  # no cookie at all
    e.client.get("/auth/oauth/google/start")
    assert post("/auth/oauth/google/callback", json=forged).status_code == 400  # wrong state
    assert post("/auth/oauth/google/callback", json={"code": "code-ada"}).status_code == 400
    assert count(e, lesson.User) == 0 and e.client.cookies.get(lesson.COOKIE_NAME) is None


def test_lesson_oauth_state_is_single_use_and_pkce_is_s256(lesson_env):
    e = lesson_env
    start = e.client.get("/auth/oauth/google/start")
    cookies = [c.lower() for c in start.headers.get_list("set-cookie")]
    assert len(cookies) == 2 and all("httponly" in c and "samesite=lax" in c for c in cookies)
    query = parse_qs(urlparse(start.json()["authorize_url"]).query)
    verifier = e.client.cookies.get(lesson.OAUTH_VERIFIER_COOKIE)
    digest = hashlib.sha256(verifier.encode()).digest()
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"] == [base64.urlsafe_b64encode(digest).rstrip(b"=").decode()]
    assert 43 <= len(verifier) <= 128
    body = {"code": "code-ada", "state": query["state"][0]}
    assert e.client.post("/auth/oauth/google/callback", json=body).status_code == 200
    assert e.client.cookies.get(lesson.OAUTH_STATE_COOKIE) is None  # state cookie deleted
    assert e.client.post("/auth/oauth/google/callback", json=body).status_code == 400  # no replay


def test_lesson_oauth_callback_rotates_a_pre_existing_session(lesson_env):
    e = lesson_env
    register(e, "bob@example.com")
    e.client.post("/auth/sign-in", json={"email": "bob@example.com", "password": PASSWORD})
    old = e.client.cookies.get(lesson.COOKIE_NAME)
    grace = oauth_login(e, "github", "code-grace")
    assert grace.status_code == 200 and grace.json()["email"] == "grace@example.com"
    assert e.client.cookies.get(lesson.COOKIE_NAME) != old
    with e.session_local() as db:
        assert lesson.get_valid_session(db, old, now=e.clock.now) is None  # not left behind
    assert e.client.get("/auth/me").json()["email"] == "grace@example.com"


# ---- 8. password reset and linked identities ------------------------------------------------
def reset_via_email(e, email=EMAIL, new_password="a-brand-new-passphrase"):
    e.client.post("/auth/forgot-password", json={"email": email})
    body = {"token": lesson.OUTBOX[-1]["token"], "new_password": new_password}
    return e.client.post("/auth/reset-password", json=body)


def test_lesson_reset_of_unverified_account_verifies_it_and_drops_linked_identities(lesson_env):
    e = lesson_env
    register(e)
    with e.session_local() as db:
        user = db.scalar(select(lesson.User))
        db.add(lesson.Account(user_id=user.id, provider_id="github", account_id="gh-6666"))
        db.commit()
    assert reset_via_email(e).status_code == 200
    with e.session_local() as db:
        assert db.scalar(select(lesson.User.email_verified)) is True
        assert db.scalars(select(lesson.Account.provider_id)).all() == ["credential"]
    new = {"email": EMAIL, "password": "a-brand-new-passphrase"}
    assert e.client.post("/auth/sign-in", json=new).status_code == 200


def test_lesson_reset_of_verified_account_keeps_linked_identities(lesson_env):
    e = lesson_env
    register(e)
    e.client.post("/auth/verify-email", json={"token": lesson.OUTBOX[-1]["token"]})
    with e.session_local() as db:
        user = db.scalar(select(lesson.User))
        db.add(lesson.Account(user_id=user.id, provider_id="google", account_id="g-42"))
        db.commit()
    assert reset_via_email(e).status_code == 200
    assert count(e, lesson.Account, lesson.Account.provider_id == "google") == 1


def test_lesson_oauth_only_user_can_set_a_password_by_email(lesson_env):
    e = lesson_env
    assert oauth_login(e, "google", "code-ada").status_code == 200
    assert reset_via_email(e).status_code == 200
    new = {"email": EMAIL, "password": "a-brand-new-passphrase"}
    assert e.client.post("/auth/sign-in", json=new).status_code == 200
    assert count(e, lesson.Account) == 2  # google + the new credential login


# ---- 4. signing secret: explicit opt-in for the dev key -------------------------------------
def test_lesson_missing_jwt_secret_outside_dev_is_an_error(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    for app_env in ("prod", "staging", ""):
        monkeypatch.setenv("APP_ENV", app_env)
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            lesson.create_access_token("user-1", datetime.now(UTC))
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            lesson.decode_access_token("a.b.c")
    monkeypatch.delenv("APP_ENV")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):  # unset APP_ENV is NOT dev
        lesson.create_access_token("user-1", datetime.now(UTC))


def test_lesson_dev_key_is_opt_in_and_configured_secret_wins(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("APP_ENV", "dev")
    with pytest.warns(UserWarning, match="INSECURE"):
        token = lesson.create_access_token("user-1", datetime.now(UTC))
    with pytest.warns(UserWarning, match="INSECURE"):
        assert lesson.decode_access_token(token) == "user-1"
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("JWT_SECRET", "a-real-secret-0123456789-abcdefghijklmnop")
    assert lesson.decode_access_token(lesson.create_access_token("u", datetime.now(UTC))) == "u"
    monkeypatch.setenv("JWT_SECRET", "too-short")
    with pytest.raises(RuntimeError, match="32"):
        lesson.create_access_token("u", datetime.now(UTC))


def test_lesson_access_token_without_exp_is_rejected(monkeypatch):
    import jwt

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET", "a-real-secret-0123456789-abcdefghijklmnop")
    secret = lesson.get_secret()
    forever = jwt.encode({"sub": "u", "iat": datetime.now(UTC)}, secret, algorithm="HS256")
    with pytest.raises(jwt.InvalidTokenError):
        lesson.decode_access_token(forever)


# ---- 11. the lesson's migration matches its models (family_expires_at) ----------------------
def test_lesson_migration_matches_models():
    eng = lesson.make_engine()
    lesson.migrate(eng)
    with eng.connect() as conn:
        assert compare_metadata(MigrationContext.configure(conn), lesson.Base.metadata) == []
    assert "family_expires_at" in {c["name"] for c in inspect(eng).get_columns("refresh_token")}
