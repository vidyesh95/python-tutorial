# Auth Schema, Database Sessions and Rotating Refresh Tokens
"""
Lesson 10 kept users in a dict. Real systems need a schema. This lesson implements, in Python,
the core data model of Better Auth (a TypeScript auth library): four tables - `user`,
`session`, `account`, `verification` - plus a `refresh_token` table for the JWT alternative.

Better Auth column -> our column (SQLAlchemy 2 typed models below)
  user          id, name, email, emailVerified, image, createdAt, updatedAt
                -> id (UUIDv7 str), name, email (UNIQUE, lowercased), email_verified,
                   image, created_at, updated_at
  session       id, userId, token, expiresAt, ipAddress, userAgent, createdAt, updatedAt
                -> id, user_id (FK ON DELETE CASCADE), token_hash (SHA-256 of the opaque
                   token, UNIQUE; the raw token only ever lives in the cookie), expires_at,
                   ip_address, user_agent, created_at, updated_at
  account       id, userId, providerId, accountId, accessToken, refreshToken, idToken,
                accessTokenExpiresAt, scope, password, createdAt, updatedAt
                -> same names in snake_case; UNIQUE(provider_id, account_id).
                   provider_id is "credential" for email+password or "github"/"google"/...;
                   `password` holds an Argon2id hash and only exists for "credential".
  verification  id, identifier, value, expiresAt, createdAt, updatedAt
                -> id, identifier ("email-verify:<email>" / "password-reset:<user_id>"),
                   value_hash (SHA-256 of the emailed token), expires_at, created_at
  (not in Better Auth core) refresh_token: id, user_id, token_hash, family_id, expires_at,
                family_expires_at, revoked_at, replaced_by - the standard "rotating refresh
                token" pattern. `family_expires_at` is an ABSOLUTE cap (90 days) copied to every
                successor, so a stolen-but-never-reused chain cannot be refreshed forever.

One person can have SEVERAL accounts (password + GitHub + Google). `account` is the login
method, `user` is the human. Real deployments encrypt provider tokens (access/refresh/id
token) at rest - envelope encryption with a KMS-held key. We store them plain to stay small.

Passwords: `PasswordHash.recommended()` is Argon2**id** (v=19, m=65536 KiB, t=3, p=4). The hash
string embeds variant + params + salt, so `verify_and_update` can detect weaker params and hand
back a fresh hash to store on the next successful login. Unknown emails still verify against a
dummy hash so response time does not reveal which emails exist.

Timezones: we use `datetime.now(UTC)` everywhere. SQLite has no timezone support and returns
NAIVE datetimes, which crash when compared with aware ones. `UTCDateTime` (a TypeDecorator)
refuses naive values on the way in and re-attaches UTC on the way out. Postgres
(`timestamptz`) needs no such help, but the decorator is harmless there.

Part 1 - database sessions (Better Auth's default). Sign-in creates a `session` row and sets
an opaque random token in an HttpOnly cookie. Every request hashes the cookie and looks the
row up. Revocation is a DELETE.
Part 2 - short-lived JWT access token + opaque rotating refresh token (mobile apps, APIs).

                       DB session cookie           JWT access + refresh token
  Revoke now           delete row (instant)        access token lives until `exp` (15 min)
  Per-request cost     1 indexed DB lookup         signature check, no DB
  Client               browsers (cookie, CSRF)     mobile / SPAs / other services
  Leak of one token    session until revoked       access 15 min; refresh reuse is detected
  Scaling              DB/cache on hot path        stateless reads, DB only on refresh
Most web apps should start with sessions: simpler and safer.

CSRF: cookies are sent automatically by the browser, so state-changing cookie routes need
SameSite=Lax (blocks cross-site POSTs) AND an `Origin` allow-list check (below). Bearer tokens
in an `Authorization` header are not sent automatically, so they are not CSRF-prone.

Secrets: the JWT signing key comes from `JWT_SECRET`. It is read lazily by `get_secret()` (when a
token is signed or verified), and a missing key is a hard error (RuntimeError) unless you opt in
to the insecure development key with `APP_ENV=dev` (or `test`). No silent fallback in production.

Serve it live:  APP_ENV=dev COOKIE_SECURE=0 uv run fastapi dev t04_fastapi_backend/m_20_auth_schema_sessions.py
                (Secure cookies are not sent over plain http://localhost, hence the switch)
Run the offline demo: uv run python -m t04_fastapi_backend.m_20_auth_schema_sessions
                (the demo sets APP_ENV=dev itself and says so)
"""

import base64
import hashlib
import hmac
import os
import secrets
import tempfile
import threading
import uuid
import warnings
from collections import OrderedDict, deque
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import parse_qs, urlencode, urlparse

import jwt
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi import APIRouter, Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pydantic import BaseModel, Field
from sqlalchemy import (
    DateTime,
    Engine,
    ForeignKey,
    String,
    UniqueConstraint,
    create_engine,
    delete,
    event,
    inspect,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator

# Example: configuration
COOKIE_NAME = "session_token"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "1") != "0"  # keep ON outside local http dev
ALLOWED_ORIGINS = {"https://app.example.com"}  # the front-ends allowed to use cookie auth
SESSION_TTL = timedelta(days=7)
SESSION_UPDATE_AGE = timedelta(days=1)  # slide expiry at most once a day (Better Auth updateAge)
ACCESS_TTL = timedelta(minutes=15)
REFRESH_TTL = timedelta(days=30)
REFRESH_FAMILY_TTL = timedelta(days=90)  # absolute cap: rotation never extends past this
OAUTH_STATE_TTL = timedelta(minutes=10)
VERIFY_TTL = timedelta(hours=1)
RESET_TTL = timedelta(minutes=15)
MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH = 8, 128
# The max length caps request size/memory and stops DoS against KDFs whose cost grows with the
# input (PBKDF2 hashes every byte; bcrypt silently truncates at 72 bytes). It does NOT bound
# Argon2's cost: that is driven by its m/t/p parameters (memory, iterations, lanes).
MAX_FAILURES, FAILURE_WINDOW = 5, timedelta(minutes=15)
MAX_TRACKED_EMAILS = 10_000  # bound on the in-process limiter's memory
DEV_SECRET = "dev-only-jwt-secret-change-me-0123456789abcdef"


def get_secret() -> str:
    """The JWT signing key, resolved when signing/verifying (never silently insecure).

    Checked lazily, not at import, so importing the module (tests, docs, `fastapi dev` reload)
    stays cheap, but the first token operation in a misconfigured deployment fails loudly.
    The committed DEV_SECRET is only used when you explicitly say APP_ENV=dev (or test).
    """
    secret = os.environ.get("JWT_SECRET")
    if secret:
        if len(secret) < 32:
            raise RuntimeError("JWT_SECRET must be at least 32 characters")
        return secret
    if os.environ.get("APP_ENV") in {"dev", "test"}:
        warnings.warn("JWT_SECRET not set: using the INSECURE development key", stacklevel=2)
        return DEV_SECRET
    raise RuntimeError("JWT_SECRET is not set (set it, or APP_ENV=dev for local lessons only)")


# Example: timezone-safe datetime column + typed models
class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime: use datetime.now(UTC)")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid.uuid7())  # time-ordered: friendlier to B-tree indexes than uuid4


class Base(DeclarativeBase):
    type_annotation_map = {datetime: UTCDateTime}


class User(Base):
    __tablename__ = "user"  # quoted automatically; "user" is reserved in Postgres
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)  # stored lowercased
    email_verified: Mapped[bool] = mapped_column(default=False)
    image: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)


class UserSession(Base):
    __tablename__ = "session"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime]
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)


class Account(Base):
    __tablename__ = "account"
    __table_args__ = (UniqueConstraint("provider_id", "account_id", name="uq_account_provider"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    provider_id: Mapped[str] = mapped_column(String(50))  # "credential", "github", "google"
    account_id: Mapped[str] = mapped_column(String(255))  # provider's user id (credential: ours)
    access_token: Mapped[str | None]  # encrypt at rest in production (KMS envelope encryption)
    refresh_token: Mapped[str | None]
    id_token: Mapped[str | None]
    access_token_expires_at: Mapped[datetime | None]
    scope: Mapped[str | None] = mapped_column(String(500))
    password: Mapped[str | None]  # Argon2id hash, credential accounts only
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)


class Verification(Base):
    __tablename__ = "verification"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    identifier: Mapped[str] = mapped_column(String(255), index=True)
    value_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class RefreshToken(Base):
    __tablename__ = "refresh_token"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    family_id: Mapped[str] = mapped_column(String(36), index=True)  # one login = one family
    expires_at: Mapped[datetime]
    family_expires_at: Mapped[datetime]  # absolute cap, set on the first token, inherited
    revoked_at: Mapped[datetime | None]
    replaced_by: Mapped[str | None] = mapped_column(String(36))  # id of the rotated successor
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


# Example: migration - the schema is created by Alembic (same recipe as m_08), not create_all
ENV_PY = """
from alembic import context

context.configure(connection=context.config.attributes["connection"])
with context.begin_transaction():
    context.run_migrations()
"""

REVISION_1 = '''"""auth core schema"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None
TS = sa.DateTime(timezone=True)


def cascade() -> sa.ForeignKey:  # a ForeignKey object can only belong to one column
    return sa.ForeignKey("user.id", ondelete="CASCADE")


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("email_verified", sa.Boolean, nullable=False),
        sa.Column("image", sa.String, nullable=True),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("updated_at", TS, nullable=False),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)
    op.create_table(
        "session",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), cascade(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", TS, nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("updated_at", TS, nullable=False),
    )
    op.create_index("ix_session_user_id", "session", ["user_id"])
    op.create_index("ix_session_token_hash", "session", ["token_hash"], unique=True)
    op.create_table(
        "account",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), cascade(), nullable=False),
        sa.Column("provider_id", sa.String(50), nullable=False),
        sa.Column("account_id", sa.String(255), nullable=False),
        sa.Column("access_token", sa.String, nullable=True),
        sa.Column("refresh_token", sa.String, nullable=True),
        sa.Column("id_token", sa.String, nullable=True),
        sa.Column("access_token_expires_at", TS, nullable=True),
        sa.Column("scope", sa.String(500), nullable=True),
        sa.Column("password", sa.String, nullable=True),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("updated_at", TS, nullable=False),
        sa.UniqueConstraint("provider_id", "account_id", name="uq_account_provider"),
    )
    op.create_index("ix_account_user_id", "account", ["user_id"])
    op.create_table(
        "verification",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("identifier", sa.String(255), nullable=False),
        sa.Column("value_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", TS, nullable=False),
        sa.Column("created_at", TS, nullable=False),
    )
    op.create_index("ix_verification_identifier", "verification", ["identifier"])
    op.create_index("ix_verification_value_hash", "verification", ["value_hash"], unique=True)
    op.create_table(
        "refresh_token",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), cascade(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("expires_at", TS, nullable=False),
        sa.Column("family_expires_at", TS, nullable=False),
        sa.Column("revoked_at", TS, nullable=True),
        sa.Column("replaced_by", sa.String(36), nullable=True),
        sa.Column("created_at", TS, nullable=False),
    )
    op.create_index("ix_refresh_token_user_id", "refresh_token", ["user_id"])
    op.create_index("ix_refresh_token_token_hash", "refresh_token", ["token_hash"], unique=True)
    op.create_index("ix_refresh_token_family_id", "refresh_token", ["family_id"])


def downgrade() -> None:
    for table in ("refresh_token", "verification", "account", "session", "user"):
        op.drop_table(table)
'''


def migrate(eng: Engine) -> None:
    """Run `alembic upgrade head` against `eng` from a throwaway migration environment."""
    with tempfile.TemporaryDirectory() as tmp, eng.begin() as conn:
        root = Path(tmp) / "alembic"
        (root / "versions").mkdir(parents=True)
        (root / "env.py").write_text(ENV_PY)
        (root / "versions" / "0001_auth_core.py").write_text(REVISION_1)
        cfg = Config()
        cfg.set_main_option("script_location", str(root))
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")


def make_engine() -> Engine:
    # DEMO ONLY: StaticPool hands every request the SAME SQLite connection (and so the same
    # transaction), which is what lets an in-memory database be shared across threads. It means
    # concurrent requests are not truly isolated: the "atomic claim" in rotate_refresh_token is
    # not really contended here, and one request's rollback() can discard another's pending
    # work. Real deployments use Postgres with a pool that gives each session its own connection.
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(eng, "connect")
    def _enforce_foreign_keys(dbapi_conn: Any, _record: Any) -> None:
        dbapi_conn.execute("PRAGMA foreign_keys=ON")  # SQLite ignores ON DELETE CASCADE otherwise

    return eng


engine = make_engine()
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db


def get_now() -> datetime:
    return datetime.now(UTC)  # a dependency, so tests and demos can inject a fake clock


DB = Annotated[Session, Depends(get_db)]
Now = Annotated[datetime, Depends(get_now)]


# Example: passwords (Argon2id) and tokens (opaque random, stored as SHA-256)
password_hasher = PasswordHash.recommended()  # Argon2id v=19 m=65536 KiB t=3 p=4
DUMMY_HASH = password_hasher.hash("not-a-real-password")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def new_token() -> str:
    return secrets.token_urlsafe(32)  # 256 bits from the OS CSPRNG


def hash_token(token: str) -> str:
    # Plain SHA-256 is right HERE: the input already has 256 bits of entropy, so there is
    # nothing to brute-force (unlike passwords) and we need a fast, indexable lookup key.
    return hashlib.sha256(token.encode()).hexdigest()


class InvalidTokenError(Exception):
    """A refresh/verification token is unknown, expired, or was reused."""


# Example: database sessions
def create_session(
    db: Session, user_id: str, now: datetime, ip: str | None = None, ua: str | None = None
) -> str:
    token = new_token()
    db.add(
        UserSession(
            user_id=user_id,
            token_hash=hash_token(token),
            expires_at=now + SESSION_TTL,
            ip_address=ip,
            user_agent=ua,
            created_at=now,
            updated_at=now,
        )
    )
    return token  # raw token goes to the cookie; the DB only has the hash


def get_valid_session(db: Session, token: str, now: datetime) -> UserSession | None:
    row = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    return row if row is not None and row.expires_at > now else None


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,  # JavaScript (and so XSS) cannot read it
        secure=COOKIE_SECURE,  # HTTPS only; switch off just for local http development
        samesite="lax",  # not sent on cross-site POSTs
        path="/",
    )


def check_origin(request: Request) -> None:
    """CSRF defense in depth: state-changing cookie routes need a trusted Origin header."""
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if request.headers.get("origin") not in ALLOWED_ORIGINS:
            raise HTTPException(403, "Untrusted origin")


@dataclass
class Auth:
    user: User
    session: UserSession


def get_auth(
    db: DB,
    now: Now,
    response: Response,
    session_token: Annotated[str | None, Cookie()] = None,
) -> Auth:
    row = get_valid_session(db, session_token, now) if session_token else None
    user = db.get(User, row.user_id) if row else None
    if row is None or user is None or session_token is None:
        raise HTTPException(401, "Not authenticated")
    if now - row.updated_at >= SESSION_UPDATE_AGE:  # sliding expiration, not on every request
        row.expires_at, row.updated_at = now + SESSION_TTL, now
        db.commit()
        set_session_cookie(response, session_token)  # extend the browser's Max-Age too
    return Auth(user, row)


CurrentAuth = Annotated[Auth, Depends(get_auth)]


# Example: sign-in brute-force limiter (DEMO: in-process; production uses Redis, see below)
_attempts: OrderedDict[str, deque[datetime]] = OrderedDict()  # email -> attempt times, LRU order
_attempts_lock = threading.Lock()


def check_rate_limit(email: str, now: datetime) -> None:
    """Atomically count one sign-in attempt for `email`, or raise 429 when over the limit.

    Sync routes run in a threadpool, so two requests can be in here at once. The whole
    read-check-append happens under one lock, and the attempt is recorded BEFORE the slow
    password verification: counting only after the verify (read, hash for 100 ms, then write)
    lets a burst of parallel guesses all read "0 failures" and sail through. A successful sign-in
    calls `clear_rate_limit`. Memory is bounded: expired attempts are pruned on access and at
    most MAX_TRACKED_EMAILS keys are kept (least recently used evicted first).

    This is a single-process DEMO. Each worker/host has its own counters, so the real limit is
    N times higher, and restarting resets it. Production: a shared atomic counter in Redis (m_15)
    keyed by email AND client IP, e.g. with redis-py:

        key = f"signin:{email}:{ip}"
        pipe = redis.pipeline()          # INCR + EXPIRE in one round trip
        pipe.incr(key)
        pipe.expire(key, int(FAILURE_WINDOW.total_seconds()), nx=True)  # TTL set once per window
        attempts, _ = pipe.execute()
        if attempts > MAX_FAILURES:
            raise HTTPException(429, "Too many attempts, try again later")
    """
    with _attempts_lock:
        recent = _attempts.pop(email, None) or deque()
        while recent and now - recent[0] >= FAILURE_WINDOW:
            recent.popleft()
        if len(recent) >= MAX_FAILURES:
            _attempts[email] = recent  # keep tracking; the window slides as entries expire
            raise HTTPException(429, "Too many attempts, try again later")
        recent.append(now)  # append in place; never rebuild-and-reassign a shared list
        _attempts[email] = recent  # re-inserted at the end: most recently used
        while len(_attempts) > MAX_TRACKED_EMAILS:
            _attempts.popitem(last=False)  # evict the least recently used key


def clear_rate_limit(email: str) -> None:
    with _attempts_lock:
        _attempts.pop(email, None)


def reset_rate_limits() -> None:  # for tests and demos
    with _attempts_lock:
        _attempts.clear()


def authenticate(db: Session, email: str, password: str, now: datetime) -> User | None:
    email = normalize_email(email)
    check_rate_limit(email, now)  # counts this attempt; raises 429 when over the limit
    user = db.scalar(select(User).where(User.email == email))
    account = user and db.scalar(
        select(Account).where(Account.user_id == user.id, Account.provider_id == "credential")
    )
    stored = (account.password if account else None) or DUMMY_HASH  # always burn one verify
    ok, upgraded = password_hasher.verify_and_update(password, stored)
    if user is None or account is None or not ok:
        return None
    if upgraded:  # hash used weaker params than today's defaults: store the stronger one
        account.password = upgraded
    clear_rate_limit(email)
    return user


# Example: JWT access token + rotating refresh token (Part 2)
def create_access_token(user_id: str, now: datetime) -> str:
    claims = {"sub": user_id, "iat": now, "exp": now + ACCESS_TTL, "jti": uuid.uuid4().hex}
    return jwt.encode(claims, get_secret(), algorithm="HS256")


def decode_access_token(token: str) -> str:
    claims = jwt.decode(
        token, get_secret(), algorithms=["HS256"], options={"require": ["exp", "iat", "sub"]}
    )
    return claims["sub"]


def issue_refresh_token(
    db: Session,
    user_id: str,
    now: datetime,
    family_id: str | None = None,
    family_expires_at: datetime | None = None,
) -> tuple[str, RefreshToken]:
    """First token of a login starts a family with an absolute deadline; successors inherit it."""
    family_expires_at = family_expires_at or now + REFRESH_FAMILY_TTL
    token = new_token()
    row = RefreshToken(
        user_id=user_id,
        token_hash=hash_token(token),
        family_id=family_id or new_id(),
        expires_at=min(now + REFRESH_TTL, family_expires_at),  # never outlives the family
        family_expires_at=family_expires_at,
        created_at=now,
    )
    db.add(row)
    db.flush()
    return token, row


def revoke_family(db: Session, family_id: str, now: datetime) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


def rotate_refresh_token(db: Session, raw_token: str, now: datetime) -> tuple[str, str]:
    """Exchange a refresh token for a new one. Returns (user_id, new_raw_token)."""
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token)))
    if row is None:
        raise InvalidTokenError("unknown refresh token")
    user_id, family_id = row.user_id, row.family_id
    if row.revoked_at is None:
        # Expiry is only checked for a token that was never used. Checking it FIRST would let an
        # attacker replay a stolen, already-rotated token after it expired without raising the
        # reuse alarm that revokes the family.
        if row.expires_at <= now or row.family_expires_at <= now:
            raise InvalidTokenError("expired refresh token")
        new_raw, new_row = issue_refresh_token(
            db, user_id, now, family_id, family_expires_at=row.family_expires_at
        )
        # Atomic claim: only ONE concurrent request can flip revoked_at from NULL (with a real
        # connection per request; see make_engine for why the demo only imitates this).
        claimed = db.execute(
            update(RefreshToken)
            .where(RefreshToken.id == row.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now, replaced_by=new_row.id)
        )
        if claimed.rowcount == 1:
            return user_id, new_raw
        db.rollback()  # lost the race: discard the successor, treat it as reuse
    # An already-used token came back: it was stolen (or replayed). Kill the whole family so
    # neither the thief nor the victim's latest token works; the real user must sign in again.
    revoke_family(db, family_id, now)
    db.commit()
    raise InvalidTokenError("refresh token reuse detected: family revoked")


def revoke_all_for_user(db: Session, user_id: str, now: datetime) -> None:
    db.execute(delete(UserSession).where(UserSession.user_id == user_id))
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


# Example: email verification and password reset share the `verification` table
OUTBOX: list[dict[str, str]] = []  # fake mail server; tests/demos read tokens from here


def issue_verification(db: Session, identifier: str, ttl: timedelta, now: datetime) -> str:
    token = new_token()
    db.execute(delete(Verification).where(Verification.identifier == identifier))  # 1 live token
    db.add(
        Verification(
            identifier=identifier,
            value_hash=hash_token(token),
            expires_at=now + ttl,
            created_at=now,
        )
    )
    return token


def consume_verification(db: Session, token: str, prefix: str, now: datetime) -> str | None:
    """Single use: returns the identifier suffix and deletes the row; the caller commits."""
    digest = hash_token(token)
    row = db.scalar(
        select(Verification).where(
            Verification.value_hash == digest, Verification.identifier.startswith(prefix)
        )
    )
    # No hmac.compare_digest here: we looked the row up BY HASH, so the database already did the
    # matching, an index probe on a hash of a 256-bit secret leaks nothing useful, and comparing
    # the digest with the value we just selected by it would be comparing a string to itself.
    # Constant-time comparison matters when PYTHON compares an attacker-supplied value with a
    # secret it holds: webhook HMAC signatures, API keys in memory, the OAuth `state` cookie
    # (see oauth_callback).
    if row is None or row.expires_at <= now:
        return None  # (expired rows are left for a periodic cleanup job)
    if db.execute(delete(Verification).where(Verification.id == row.id)).rowcount != 1:
        return None  # a concurrent request consumed it first
    return row.identifier.removeprefix(prefix)


# Example: OAuth account linking (the provider HTTP exchange is mocked away)
@dataclass(frozen=True)
class OAuthProfile:
    provider_id: str
    account_id: str  # the provider's stable user id (never use the email as the key)
    email: str
    email_verified: bool
    name: str = ""
    access_token: str | None = None
    refresh_token: str | None = None
    id_token: str | None = None
    scope: str | None = None


class OAuthLinkError(Exception):
    """The provider has not verified the email, so it may neither join nor create an account."""


def link_oauth_account(
    db: Session, profile: OAuthProfile, now: datetime, signed_in_user_id: str | None = None
) -> User:
    tokens = {
        k: getattr(profile, k) for k in ("access_token", "refresh_token", "id_token", "scope")
    }
    account = db.scalar(
        select(Account).where(
            Account.provider_id == profile.provider_id, Account.account_id == profile.account_id
        )
    )
    if account is not None:  # 1. known login method: refresh stored tokens, done
        for key, value in tokens.items():
            if value is not None:  # Google returns a refresh_token only on the FIRST consent;
                setattr(account, key, value)  # a later login must not wipe the one we stored
        account.updated_at = now
        return db.get_one(User, account.user_id)
    if not profile.email_verified:
        # An unverified provider email may neither LINK to an existing user (anyone can register
        # "victim@x.com" at a sloppy provider and walk into the victim's account) nor CREATE a
        # user: that row would claim the address, with the attacker's identity already attached,
        # and when the real owner later signs in with a verified identity we would be handing them
        # an account the attacker can still enter. We refuse; the user verifies the email first.
        raise OAuthLinkError("provider email is not verified")
    email = normalize_email(profile.email)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:  # 2. brand new person (the provider verified the address)
        user = User(
            name=profile.name or email.split("@")[0],
            email=email,
            email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        db.flush()
    elif not user.email_verified:
        # Pre-hijacking: an attacker may have signed up with the victim's email + THEIR
        # password. The provider just proved the real owner controls the address, so nothing
        # attached by whoever created the row can be trusted: drop EVERY existing login method
        # (password and any other linked identity; the new one is added below) and all sessions.
        db.execute(delete(Account).where(Account.user_id == user.id))
        revoke_all_for_user(db, user.id, now)
        user.email_verified, user.updated_at = True, now
    elif signed_in_user_id != user.id:
        # 3. Verified user, linked from an ANONYMOUS request. The attacker variant: they
        # pre-registered the victim's address with their password; the victim clicked the
        # verification link (marking the attacker's account verified); now a Google login would
        # auto-link while the attacker's password still works. We cannot tell a legitimate
        # password from a planted one, so any credential login is removed and every session and
        # refresh token revoked; the owner sets a fresh password via "forgot password" (their
        # inbox proves ownership). Trade-off: a genuine user who signed up with a password and
        # first meets "Sign in with Google" while signed out loses that password and must reset
        # it. Signed in as this user -> they are linking deliberately and keep everything. Only
        # users that HAVE a credential login are affected; OAuth-only users are not logged out.
        credentials = delete(Account).where(
            Account.user_id == user.id, Account.provider_id == "credential"
        )
        if db.execute(credentials).rowcount:
            revoke_all_for_user(db, user.id, now)
            user.updated_at = now
    db.add(
        Account(
            user_id=user.id,
            provider_id=profile.provider_id,
            account_id=profile.account_id,
            created_at=now,
            updated_at=now,
            **tokens,
        )
    )
    return user


# Example: HTTP layer - schemas
Email = Annotated[str, Field(max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]


class SignUpIn(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    email: Email
    password: Annotated[str, Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)]


class SignInIn(BaseModel):
    email: Email
    password: Annotated[str, Field(max_length=MAX_PASSWORD_LENGTH)]


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    email_verified: bool


class SessionOut(BaseModel):  # never includes token_hash
    id: str
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    expires_at: datetime
    current: bool


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = int(ACCESS_TTL.total_seconds())


class RefreshIn(BaseModel):
    refresh_token: str


class TokenIn(BaseModel):
    token: str


class ForgotIn(BaseModel):
    email: Email


class ResetIn(BaseModel):
    token: str
    new_password: Annotated[
        str, Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    ]


class OAuthCallbackIn(BaseModel):
    code: str
    state: str | None = None  # echoed back by the provider; must equal the state cookie


# Example: HTTP layer - routes. Cookie routes get the Origin check; token routes do not need it.
cookie_api = APIRouter(
    prefix="/auth", tags=["cookie sessions"], dependencies=[Depends(check_origin)]
)
public_api = APIRouter(prefix="/auth", tags=["tokens and account recovery"])
bearer = HTTPBearer(auto_error=False)


def invalid_credentials() -> HTTPException:  # same answer for unknown email and wrong password
    return HTTPException(401, "Invalid email or password")


VERIFY_EMAIL_TEXT = (
    "Someone created an account with this address. If that was you, use the token below to "
    "verify it. If it was NOT you, do not verify: someone else may know that account's password. "
    "Reset your password (forgot-password) so only you can sign in."
)


@cookie_api.post("/sign-up", status_code=201)
def sign_up(body: SignUpIn, db: DB, now: Now) -> UserOut:
    email = normalize_email(body.email)
    user = User(name=body.name, email=email, created_at=now, updated_at=now)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:  # unique email (also covers the race between two sign-ups)
        raise HTTPException(409, "Email already registered") from None
    db.add(
        Account(
            user_id=user.id,
            provider_id="credential",
            account_id=user.id,
            password=password_hasher.hash(body.password),
            created_at=now,
            updated_at=now,
        )
    )
    token = issue_verification(db, f"email-verify:{email}", VERIFY_TTL, now)
    db.commit()
    mail = {"to": email, "kind": "verify-email", "token": token, "text": VERIFY_EMAIL_TEXT}
    OUTBOX.append(mail)  # after the commit
    return UserOut.model_validate(user, from_attributes=True)


@public_api.post("/verify-email")
def verify_email(body: TokenIn, db: DB, now: Now) -> dict[str, bool]:
    email = consume_verification(db, body.token, "email-verify:", now)
    if email is None:
        raise HTTPException(400, "Invalid or expired token")
    # Residual risk, by design: whoever pre-registered this address chose the password, and the
    # owner clicking the link marks THAT account verified. The email text warns the owner, and
    # link_oauth_account removes a credential login when a verified identity is linked later.
    db.execute(update(User).where(User.email == email).values(email_verified=True, updated_at=now))
    db.commit()
    return {"verified": True}


@cookie_api.post("/sign-in")
def sign_in(
    body: SignInIn,
    request: Request,
    response: Response,
    db: DB,
    now: Now,
    session_token: Annotated[str | None, Cookie()] = None,
) -> UserOut:
    user = authenticate(db, body.email, body.password, now)
    if user is None:
        raise invalid_credentials()
    if session_token:  # rotate: fresh token every sign-in, drop whatever came with the request
        db.execute(delete(UserSession).where(UserSession.token_hash == hash_token(session_token)))
    ip = request.client.host if request.client else None
    token = create_session(db, user.id, now, ip, request.headers.get("user-agent"))
    db.commit()
    set_session_cookie(response, token)
    return UserOut.model_validate(user, from_attributes=True)


@cookie_api.post("/sign-out")
def sign_out(
    response: Response, db: DB, session_token: Annotated[str | None, Cookie()] = None
) -> dict[str, bool]:
    if session_token:  # idempotent: signing out twice is fine
        db.execute(delete(UserSession).where(UserSession.token_hash == hash_token(session_token)))
        db.commit()
    # The deletion cookie must repeat path (and should repeat the other attributes) to match.
    response.delete_cookie(
        COOKIE_NAME, path="/", secure=COOKIE_SECURE, httponly=True, samesite="lax"
    )
    return {"signed_out": True}


@cookie_api.get("/me")
def me(auth: CurrentAuth) -> UserOut:
    return UserOut.model_validate(auth.user, from_attributes=True)


@cookie_api.get("/sessions")
def list_sessions(auth: CurrentAuth, db: DB, now: Now) -> list[SessionOut]:
    rows = db.scalars(
        select(UserSession)
        .where(UserSession.user_id == auth.user.id, UserSession.expires_at > now)
        .order_by(UserSession.created_at, UserSession.id)
    )
    return [
        SessionOut(
            id=r.id,
            ip_address=r.ip_address,
            user_agent=r.user_agent,
            created_at=r.created_at,
            expires_at=r.expires_at,
            current=r.id == auth.session.id,
        )
        for r in rows
    ]


@cookie_api.post("/revoke-other-sessions")
def revoke_other_sessions(auth: CurrentAuth, db: DB) -> dict[str, int]:
    result = db.execute(
        delete(UserSession).where(
            UserSession.user_id == auth.user.id, UserSession.id != auth.session.id
        )
    )
    db.commit()
    return {"revoked": result.rowcount}


@public_api.post("/token")
def token_login(body: SignInIn, db: DB, now: Now) -> TokenPair:
    user = authenticate(db, body.email, body.password, now)
    if user is None:
        raise invalid_credentials()
    refresh, _ = issue_refresh_token(db, user.id, now)
    db.commit()
    return TokenPair(access_token=create_access_token(user.id, now), refresh_token=refresh)


@public_api.post("/token/refresh")
def token_refresh(body: RefreshIn, db: DB, now: Now) -> TokenPair:
    try:
        user_id, refresh = rotate_refresh_token(db, body.refresh_token, now)
    except InvalidTokenError:
        raise HTTPException(401, "Invalid refresh token") from None
    db.commit()
    return TokenPair(access_token=create_access_token(user_id, now), refresh_token=refresh)


@public_api.get("/token/me")
def token_me(
    db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> UserOut:
    try:
        user = db.get(User, decode_access_token(creds.credentials)) if creds else None
    except jwt.InvalidTokenError:
        user = None
    if user is None:
        raise HTTPException(401, "Invalid token", headers={"WWW-Authenticate": "Bearer"})
    return UserOut.model_validate(user, from_attributes=True)


@public_api.post("/forgot-password", status_code=202)
def forgot_password(body: ForgotIn, db: DB, now: Now) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == normalize_email(body.email)))
    if user is not None:
        token = issue_verification(db, f"password-reset:{user.id}", RESET_TTL, now)
        db.commit()
        OUTBOX.append({"to": user.email, "kind": "reset-password", "token": token})
    # Identical response either way, or this endpoint becomes an "is this email registered?"
    # oracle. (Timing also differs slightly; real systems enqueue the work in a background job.)
    return {"detail": "If that email is registered, a reset link has been sent."}


@public_api.post("/reset-password")
def reset_password(body: ResetIn, db: DB, now: Now) -> dict[str, bool]:
    user_id = consume_verification(db, body.token, "password-reset:", now)
    user = user_id and db.get(User, user_id)
    if not user:
        raise HTTPException(400, "Invalid or expired token")
    account = db.scalar(
        select(Account).where(Account.user_id == user.id, Account.provider_id == "credential")
    )
    new_hash = password_hasher.hash(body.new_password)
    if account is None:  # e.g. the credential login was removed by link_oauth_account
        account = Account(
            user_id=user.id, provider_id="credential", account_id=user.id, created_at=now
        )
        db.add(account)
    account.password, account.updated_at = new_hash, now
    if not user.email_verified:
        # Nobody had proved this address yet, so every other linked login (a provider identity)
        # was attached by whoever created the row. The reset link just proved the inbox owner:
        # keep only the credential login they just set.
        db.execute(
            delete(Account).where(Account.user_id == user.id, Account.provider_id != "credential")
        )
        user.email_verified = True  # following the emailed link proves they control the address
        user.updated_at = now
    revoke_all_for_user(db, user.id, now)  # a reset means "assume the old password leaked"
    db.commit()
    return {"reset": True}


# Fake provider: authorization code -> profile. A real callback exchanges the code over HTTPS
# (sending the PKCE verifier) and never trusts profile data from the browser.
FAKE_PROVIDER: dict[tuple[str, str], OAuthProfile] = {
    ("github", "code-grace"): OAuthProfile("github", "gh-1001", "grace@example.com", True, "Grace"),
    ("github", "code-evil"): OAuthProfile("github", "gh-6666", "ada@example.com", False, "Evil"),
    ("google", "code-ada"): OAuthProfile("google", "g-42", "Ada@Example.com", True, "Ada", "at-1"),
}
AUTHORIZE_URLS = {
    "github": "https://github.com/login/oauth/authorize",
    "google": "https://accounts.google.com/o/oauth2/v2/auth",
}
OAUTH_STATE_COOKIE, OAUTH_VERIFIER_COOKIE = "oauth_state", "oauth_verifier"
OAUTH_COOKIE_PATH = "/auth/oauth"  # the browser only sends these to the OAuth routes


def pkce_pair() -> tuple[str, str]:
    """PKCE (RFC 7636, method S256): (verifier, challenge). The challenge goes to the provider
    in the authorize URL; the verifier only goes in the later token request. An attacker who
    steals the authorization code from the redirect cannot redeem it without the verifier."""
    verifier = secrets.token_urlsafe(64)  # 86 chars; RFC 7636 allows 43-128
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def exchange_code(provider: str, code: str, verifier: str) -> OAuthProfile | None:
    """Mock of POST <provider>/token. A real provider recomputes S256(verifier) and compares it
    with the challenge it stored at the authorize step; here we only check the shape."""
    if not 43 <= len(verifier) <= 128:
        return None
    return FAKE_PROVIDER.get((provider, code))


def oauth_cookie_args() -> dict[str, Any]:
    return {"httponly": True, "secure": COOKIE_SECURE, "samesite": "lax", "path": OAUTH_COOKIE_PATH}


@public_api.get("/oauth/{provider}/start")
def oauth_start(provider: str, response: Response) -> dict[str, str]:
    """Step 1: remember a random `state` (login-CSRF defense) and a PKCE verifier in short-lived
    HttpOnly cookies, and hand back the URL to send the browser to."""
    if provider not in AUTHORIZE_URLS:
        raise HTTPException(404, "Unknown provider")
    state, (verifier, challenge) = new_token(), pkce_pair()
    max_age = int(OAUTH_STATE_TTL.total_seconds())
    response.set_cookie(OAUTH_STATE_COOKIE, state, max_age=max_age, **oauth_cookie_args())
    response.set_cookie(OAUTH_VERIFIER_COOKIE, verifier, max_age=max_age, **oauth_cookie_args())
    query = urlencode(
        {
            "client_id": "demo-client-id",
            "redirect_uri": "https://app.example.com/auth/callback",
            "response_type": "code",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return {"authorize_url": f"{AUTHORIZE_URLS[provider]}?{query}"}


@public_api.post("/oauth/{provider}/callback")
def oauth_callback(
    provider: str,
    body: OAuthCallbackIn,
    request: Request,
    response: Response,
    db: DB,
    now: Now,
    session_token: Annotated[str | None, Cookie()] = None,
    oauth_state: Annotated[str | None, Cookie()] = None,
    oauth_verifier: Annotated[str | None, Cookie()] = None,
) -> UserOut:
    # Step 2: the state the provider echoes must equal the one OUR browser stored at /start.
    # Without it an attacker could feed the victim's browser a callback carrying the ATTACKER's
    # code and sign the victim into the attacker's account (login CSRF). compare_digest is the
    # right tool here: Python compares an attacker-supplied value with a secret it holds.
    if (
        not oauth_state
        or not oauth_verifier
        or not body.state
        or not hmac.compare_digest(oauth_state.encode(), body.state.encode())
    ):
        raise HTTPException(400, "Invalid OAuth state")
    profile = exchange_code(provider, body.code, oauth_verifier)
    if profile is None:
        raise HTTPException(400, "Invalid authorization code")
    current = get_valid_session(db, session_token, now) if session_token else None
    try:
        user = link_oauth_account(db, profile, now, signed_in_user_id=current and current.user_id)
    except OAuthLinkError:
        db.rollback()
        raise HTTPException(
            409, "account_not_linked: provider has not verified this email"
        ) from None
    if session_token:  # rotate, like sign_in: never keep a session that predates this login
        db.execute(delete(UserSession).where(UserSession.token_hash == hash_token(session_token)))
    token = create_session(db, user.id, now, request.client.host if request.client else None)
    db.commit()
    set_session_cookie(response, token)
    for name in (OAUTH_STATE_COOKIE, OAUTH_VERIFIER_COOKIE):  # single use
        response.delete_cookie(name, **oauth_cookie_args())
    return UserOut.model_validate(user, from_attributes=True)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    migrate(engine)  # in production run `alembic upgrade head` as a separate deploy step
    yield


app = FastAPI(title="Auth Schema Demo", lifespan=lifespan)
app.include_router(cookie_api)
app.include_router(public_api)


"""
Common mistakes:
- Storing raw session/refresh/reset tokens. A leaked DB dump (or a SQL injection read) would
  then hand out working logins. Store SHA-256 of the token; compare by hash.
- Hashing passwords with SHA-256/bcrypt-with-no-limit; use Argon2id, cap the length (DoS), and
  re-hash on login when the parameters change (`verify_and_update`).
- Auto-linking an OAuth login to an existing user by email without `email_verified`: account
  takeover. Key accounts by (provider_id, provider's user id), never by email alone.
- Sessions that survive a password reset or password change. Revoke them all.
- Different responses for known/unknown emails on sign-in or "forgot password".
- Cookie without HttpOnly / Secure / SameSite, or a missing Origin check on cookie POSTs.
- Naive datetimes (`datetime.utcnow()`): compare/serialize wrongly. Use `datetime.now(UTC)`.
- SQLite ignores `ON DELETE CASCADE` unless `PRAGMA foreign_keys=ON` is set on every connection.
- Letting the token choose the JWT algorithm. PyJWT 2 refuses `jwt.decode` without
  `algorithms=[...]` (DecodeError), but older libraries/versions trusted the header's `alg`
  (`alg=none`, RS256->HS256 key confusion). Pin exactly ONE algorithm, and never mix HS* and RS*
  in the list.
- OAuth callbacks without `state` (login CSRF) and PKCE, or that keep a pre-login session.
- Marking a provider-supplied email as usable when the provider did not verify it.

Production notes:
- HTTPS everywhere; keep COOKIE_SECURE on; consider the `__Host-` cookie prefix.
- Encrypt provider tokens at rest (envelope encryption: a KMS-held key wraps per-row data keys).
- Move the failure counter to Redis (INCR + EXPIRE, snippet in `check_rate_limit`; m_15), key
  by email AND IP; pure per-email lockout lets an attacker lock victims out. Add CAPTCHA/step-up.
- Add an absolute session lifetime on top of sliding expiry, and a cleanup job that deletes
  expired sessions, verifications and old revoked refresh tokens.
- Refresh rotation: two tabs refreshing at once look like reuse. Add a short grace window or
  serialize refreshes client-side. Reuse detection is what makes stolen refresh tokens useful
  to attackers only once.
- Access JWTs cannot be revoked before `exp`; keep them short, or check a denylist of `jti`.
- Offer MFA (TOTP/WebAuthn passkeys); require verified email before sensitive actions.
- Sign-up currently reveals "email already registered"; to hide that too, always answer
  "check your inbox" and email the existing owner instead.
- Prefer a managed identity provider if you cannot own this surface area.
"""

if __name__ == "__main__":
    # The insecure dev signing key is opt-in. The demo opts in explicitly (and says so); an
    # APP_ENV you already exported (e.g. "prod") is respected and makes token signing fail.
    os.environ.setdefault("APP_ENV", "dev")
    print(f"NOTICE: demo running with APP_ENV={os.environ['APP_ENV']} (insecure dev JWT key)")
    ORIGIN = {"Origin": "https://app.example.com"}
    with TestClient(app, base_url="https://testserver", headers=ORIGIN) as c:
        clock = [datetime.now(UTC)]
        app.dependency_overrides[get_now] = lambda: clock[0]
        creds = {"email": "Ada@Example.com", "password": "correct-horse-battery"}

        print("-- schema created by Alembic:")
        insp = inspect(engine)
        for table in sorted(insp.get_table_names()):
            print(f"  {table}: {[col['name'] for col in insp.get_columns(table)]}")
        with engine.connect() as conn:
            drift = compare_metadata(MigrationContext.configure(conn), Base.metadata)
        print("  models vs migration drift:", drift)

        print("-- sign-up, verify, sign-in")
        r = c.post("/auth/sign-up", json={"name": "Ada", **creds})
        print(r.status_code, r.json())
        short = {"name": "Ada", "email": "bob@example.com", "password": "short"}
        print("short password:", c.post("/auth/sign-up", json=short).status_code)
        verify_token = OUTBOX[-1]["token"]
        print("verify:", c.post("/auth/verify-email", json={"token": verify_token}).json())
        print("replay:", c.post("/auth/verify-email", json={"token": verify_token}).status_code)
        bad = {**creds, "password": "nope-nope"}
        print("wrong password:", c.post("/auth/sign-in", json=bad).status_code)
        r = c.post("/auth/sign-in", json=creds)
        print(r.status_code, "cookie attrs:", r.headers["set-cookie"].split("; ", 1)[1])
        with SessionLocal() as db:
            acct = db.scalar(select(Account).where(Account.provider_id == "credential"))
            sess = db.scalar(select(UserSession))
            print("password column:", acct.password[:31] + "...")
            print("raw token stored?", c.cookies[COOKIE_NAME] == sess.token_hash)

        print("-- sliding expiry, sessions, CSRF")
        before = c.get("/auth/sessions").json()[0]["expires_at"]
        clock[0] += timedelta(days=2)
        print("expiry moved:", before, "->", c.get("/auth/sessions").json()[0]["expires_at"])
        with TestClient(app, base_url="https://testserver", headers=ORIGIN) as phone:
            phone.post("/auth/sign-in", json=creds)
            print("phone sees sessions:", len(phone.get("/auth/sessions").json()))
            print("phone revokes others:", phone.post("/auth/revoke-other-sessions").json())
        print("laptop after revoke:", c.get("/auth/me").status_code)
        c.post("/auth/sign-in", json=creds)
        evil = {"Origin": "https://evil.example"}
        print("evil origin:", c.post("/auth/sign-out", headers=evil).status_code)
        print("sign-out:", c.post("/auth/sign-out").json(), "->", c.get("/auth/me").status_code)
        c.post("/auth/sign-in", json=creds)
        clock[0] += timedelta(days=8)
        print("after 8 idle days:", c.get("/auth/me").status_code)  # expired server-side

        print("-- rehash on login (weak Argon2 params -> defaults)")
        weak = PasswordHash((Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1),))
        with SessionLocal() as db:
            acct = db.scalar(select(Account).where(Account.provider_id == "credential"))
            acct.password = weak.hash(creds["password"])
            db.commit()
            print("before:", acct.password.split("$")[3])
        c.post("/auth/sign-in", json=creds)
        with SessionLocal() as db:
            print("after: ", db.scalar(select(Account.password)).split("$")[3])

        print("-- JWT access + rotating refresh tokens")
        clock[0] = datetime.now(UTC)  # PyJWT checks iat/exp against the REAL clock: back to now
        pair = c.post("/auth/token", json=creds).json()
        print("claims:", jwt.decode(pair["access_token"], options={"verify_signature": False}))
        auth_hdr = {"Authorization": f"Bearer {pair['access_token']}"}
        print("bearer /token/me:", c.get("/auth/token/me", headers=auth_hdr).status_code)
        second = c.post("/auth/token/refresh", json={"refresh_token": pair["refresh_token"]}).json()
        print("rotated:", second["refresh_token"] != pair["refresh_token"])
        replay = c.post("/auth/token/refresh", json={"refresh_token": pair["refresh_token"]})
        print("replay of old token:", replay.status_code)
        newest = c.post("/auth/token/refresh", json={"refresh_token": second["refresh_token"]})
        print("its successor after reuse detection:", newest.status_code)

        print("-- password reset")
        c.post("/auth/sign-in", json=creds)
        known = c.post("/auth/forgot-password", json={"email": "ada@example.com"}).json()
        unknown = c.post("/auth/forgot-password", json={"email": "nobody@example.com"}).json()
        print("known/unknown email same answer:", known == unknown)
        reset = {"token": OUTBOX[-1]["token"], "new_password": "a-brand-new-passphrase"}
        print("reset:", c.post("/auth/reset-password", json=reset).json())
        print("old session after reset:", c.get("/auth/me").status_code)
        print("old password:", c.post("/auth/sign-in", json=creds).status_code)

        print("-- OAuth linking (state + PKCE)")

        def oauth_login(
            client: TestClient, provider: str, code: str, state: str | None = None
        ) -> Any:
            url = client.get(f"/auth/oauth/{provider}/start").json()["authorize_url"]
            query = parse_qs(urlparse(url).query)
            print(f"  {provider} authorize params:", sorted(query))
            body = {"code": code, "state": state or query["state"][0]}
            return client.post(f"/auth/oauth/{provider}/callback", json=body)

        c.cookies.clear()
        print("wrong state:", oauth_login(c, "github", "code-grace", state="forged").status_code)
        evil_cb = oauth_login(c, "github", "code-evil")
        print("unverified email matching ada:", evil_cb.status_code)
        ok_cb = oauth_login(c, "google", "code-ada")
        print("verified google:", ok_cb.json())
        new_cb = oauth_login(c, "github", "code-grace")
        print("new github user:", new_cb.json()["email"])
        pw = {"email": creds["email"], "password": "a-brand-new-passphrase"}
        print(
            "ada's password after a signed-out Google link:",
            c.post("/auth/sign-in", json=pw).status_code,
        )
        with SessionLocal() as db:
            print("accounts:", sorted(db.execute(select(Account.provider_id, Account.account_id))))
        app.dependency_overrides.clear()
