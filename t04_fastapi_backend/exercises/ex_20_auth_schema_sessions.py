"""Exercise 20: Auth schema, database sessions, refresh rotation, verification, OAuth linking.

The models, app and routes are pre-wired (study m_20_auth_schema_sessions first). Implement the
six stubs below. Every function takes the current time as `now` instead of reading the clock,
so tests can time-travel without sleeping. Functions flush but do not commit unless stated.

Tasks
1. hash_token(token): SHA-256 hex digest (64 chars) of the token. Tokens are 256-bit random
   values, so a fast hash is correct (passwords are different: those use Argon2id).
2. create_session(db, user_id, *, now, ip_address=None, user_agent=None): create a UserSession
   whose `token_hash` is hash_token(raw), `expires_at` is now + SESSION_TTL and created_at /
   updated_at are `now`. Flush, and return the RAW token (it goes in the cookie). The raw token
   must never be stored.
3. get_valid_session(db, token, *, now): the UserSession whose token_hash matches, or None when
   the token is unknown OR expired (expires_at <= now means expired).
4. rotate_refresh_token(db, raw_token, *, now): unknown token -> raise InvalidTokenError.
   A token that is ALREADY revoked is reuse: revoke every token of its family (revoke_family),
   COMMIT, then raise InvalidTokenError. Check this BEFORE expiry, so replaying a stolen,
   already-rotated token after it expired still burns the family.
   A live (never used) token that is expired (expires_at <= now) or whose family is past its
   absolute deadline (family_expires_at <= now) -> raise InvalidTokenError, change nothing.
   Otherwise it is revoked (revoked_at = now, replaced_by = new row id) and a successor in the
   SAME family is issued (use issue_refresh_token and pass family_id AND the row's
   family_expires_at, so the 90-day cap is inherited); return (user_id, new_raw_token).
   (Do not commit on the success path: the route does.)
5. consume_verification(db, token, prefix, *, now): find the Verification with this token's
   hash AND an identifier starting with `prefix`. Return the identifier without the prefix and
   DELETE the row (single use). Return None (and change nothing) if unknown, wrong prefix or
   expired. Do not commit.
6. link_oauth_account(db, profile, *, now) -> User. Rules, in order:
   a. An Account with this (provider_id, account_id) exists -> update its tokens (only the ones
      that are not None: Google sends a refresh_token only on the first consent, a later login
      must not erase it), return its user.
   b. Otherwise, if profile.email_verified is False raise OAuthLinkError and create nothing. An
      unverified provider email may neither link to an existing user (account takeover) nor
      create a user (that row would claim the address with the attacker's identity attached).
   c. A User with the (lowercased) email exists -> link a new Account to it. Pre-hijacking
      defense: if that user's email was NOT verified yet, delete ALL their existing Account rows
      (password and any linked provider identity: whoever created the row attached them),
      revoke_all_for_user, and set email_verified = True.
   d. No such user -> create a new User (email_verified = True) and the Account.
   Store the provider tokens on the Account. Flush, do not commit.
   (m_20 goes one step further for verified users linked while signed out; read its comments.)

Run: uv run pytest t04_fastapi_backend -k ex_20
"""

import hashlib  # noqa: F401
import secrets
import threading
import uuid
from collections import OrderedDict, deque
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from pwdlib import PasswordHash
from pydantic import BaseModel
from sqlalchemy import (
    DateTime,
    Engine,
    ForeignKey,
    String,
    UniqueConstraint,
    create_engine,
    delete,
    event,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator

COOKIE_NAME = "session_token"
SESSION_TTL = timedelta(days=7)
ACCESS_TTL = timedelta(minutes=15)
REFRESH_TTL = timedelta(days=30)
REFRESH_FAMILY_TTL = timedelta(days=90)  # absolute cap on a whole rotation chain
ALLOWED_ORIGINS = {"https://app.example.com"}  # front-ends allowed to use cookie auth
VERIFY_TTL = timedelta(hours=1)
RESET_TTL = timedelta(minutes=15)
JWT_SECRET = "exercise-jwt-secret-not-for-production-0123456789"


class UTCDateTime(TypeDecorator[datetime]):
    """SQLite drops tzinfo: refuse naive values going in, re-attach UTC coming out."""

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
    return str(uuid.uuid7())


class Base(DeclarativeBase):
    type_annotation_map = {datetime: UTCDateTime}


class User(Base):
    __tablename__ = "user"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
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
    provider_id: Mapped[str] = mapped_column(String(50))
    account_id: Mapped[str] = mapped_column(String(255))
    access_token: Mapped[str | None]
    refresh_token: Mapped[str | None]
    id_token: Mapped[str | None]
    access_token_expires_at: Mapped[datetime | None]
    scope: Mapped[str | None] = mapped_column(String(500))
    password: Mapped[str | None]
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
    family_id: Mapped[str] = mapped_column(String(36), index=True)
    expires_at: Mapped[datetime]
    family_expires_at: Mapped[datetime]  # absolute cap, set on the first token, inherited
    revoked_at: Mapped[datetime | None]
    replaced_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


def make_engine() -> Engine:
    # Demo/test only: StaticPool shares ONE SQLite connection (and transaction) between requests.
    # Real deployments use Postgres with a connection per session. See m_20.
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(eng, "connect")
    def _enforce_foreign_keys(dbapi_conn: Any, _record: Any) -> None:
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return eng


engine = make_engine()
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db


def get_now() -> datetime:
    return datetime.now(UTC)


DB = Annotated[Session, Depends(get_db)]
Now = Annotated[datetime, Depends(get_now)]

password_hasher = PasswordHash.recommended()  # Argon2id v=19 m=65536 KiB t=3 p=4
DUMMY_HASH = password_hasher.hash("not-a-real-password")
OUTBOX: list[dict[str, str]] = []  # fake mail server


class InvalidTokenError(Exception):
    """A refresh/verification token is unknown, expired, or was reused."""


class OAuthLinkError(Exception):
    """Provider email matches an existing user but is not verified."""


@dataclass(frozen=True)
class OAuthProfile:
    provider_id: str
    account_id: str
    email: str
    email_verified: bool
    name: str = ""
    access_token: str | None = None
    refresh_token: str | None = None
    id_token: str | None = None
    scope: str | None = None


def normalize_email(email: str) -> str:
    return email.strip().lower()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    raise NotImplementedError


def create_session(
    db: Session,
    user_id: str,
    *,
    now: datetime,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> str:
    raise NotImplementedError


def get_valid_session(db: Session, token: str, *, now: datetime) -> UserSession | None:
    raise NotImplementedError


def issue_refresh_token(
    db: Session,
    user_id: str,
    *,
    now: datetime,
    family_id: str | None = None,
    family_expires_at: datetime | None = None,
) -> tuple[str, RefreshToken]:
    family_expires_at = family_expires_at or now + REFRESH_FAMILY_TTL  # successors inherit it
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


def revoke_family(db: Session, family_id: str, *, now: datetime) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


def rotate_refresh_token(db: Session, raw_token: str, *, now: datetime) -> tuple[str, str]:
    raise NotImplementedError


def revoke_all_for_user(db: Session, user_id: str, *, now: datetime) -> None:
    db.execute(delete(UserSession).where(UserSession.user_id == user_id))
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


def issue_verification(db: Session, identifier: str, ttl: timedelta, *, now: datetime) -> str:
    token = new_token()
    db.execute(delete(Verification).where(Verification.identifier == identifier))
    db.add(
        Verification(
            identifier=identifier,
            value_hash=hash_token(token),
            expires_at=now + ttl,
            created_at=now,
        )
    )
    return token


def consume_verification(db: Session, token: str, prefix: str, *, now: datetime) -> str | None:
    raise NotImplementedError


def link_oauth_account(db: Session, profile: OAuthProfile, *, now: datetime) -> User:
    raise NotImplementedError


# ---- pre-wired app ----------------------------------------------------------------------
def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


def create_access_token(user_id: str, *, now: datetime) -> str:
    claims = {"sub": user_id, "iat": now, "exp": now + ACCESS_TTL, "jti": uuid.uuid4().hex}
    return jwt.encode(claims, JWT_SECRET, algorithm="HS256")


# ---- sign-in throttling (same limiter as m_20: DEMO, in-process) --------------------------
MAX_FAILURES, FAILURE_WINDOW = 5, timedelta(minutes=15)
MAX_TRACKED_EMAILS = 10_000
_attempts: OrderedDict[str, deque[datetime]] = OrderedDict()
_attempts_lock = threading.Lock()


def check_rate_limit(email: str, now: datetime) -> None:
    """Atomically count one attempt for `email` or raise 429 (read-check-append under one lock).

    The attempt is recorded BEFORE the slow password verification, otherwise a burst of parallel
    guesses all read "0 failures". Per-process demo only: production uses a shared Redis counter
    (INCR + EXPIRE, keyed by email and IP), see m_20.
    """
    with _attempts_lock:
        recent = _attempts.pop(email, None) or deque()
        while recent and now - recent[0] >= FAILURE_WINDOW:
            recent.popleft()
        if len(recent) >= MAX_FAILURES:
            _attempts[email] = recent
            raise HTTPException(429, "Too many attempts, try again later")
        recent.append(now)
        _attempts[email] = recent
        while len(_attempts) > MAX_TRACKED_EMAILS:
            _attempts.popitem(last=False)  # bounded memory: evict the least recently used


def clear_rate_limit(email: str) -> None:
    with _attempts_lock:
        _attempts.pop(email, None)


def reset_rate_limits() -> None:  # for tests
    with _attempts_lock:
        _attempts.clear()


def check_origin(request: Request) -> None:
    """CSRF defense in depth: state-changing cookie routes need a trusted Origin header."""
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if request.headers.get("origin") not in ALLOWED_ORIGINS:
            raise HTTPException(403, "Untrusted origin")


def authenticate(db: Session, email: str, password: str, now: datetime) -> User | None:
    email = normalize_email(email)
    check_rate_limit(email, now)  # counts this attempt; raises 429 when over the limit
    user = db.scalar(select(User).where(User.email == email))
    account = user and db.scalar(
        select(Account).where(Account.user_id == user.id, Account.provider_id == "credential")
    )
    stored = (account.password if account else None) or DUMMY_HASH  # timing: always verify
    ok, upgraded = password_hasher.verify_and_update(password, stored)
    if user is None or account is None or not ok:
        return None
    if upgraded:
        account.password = upgraded
    clear_rate_limit(email)
    return user


class SignUpIn(BaseModel):
    name: str
    email: str
    password: str


class SignInIn(BaseModel):
    email: str
    password: str


class TokenIn(BaseModel):
    token: str


class RefreshIn(BaseModel):
    refresh_token: str


class ForgotIn(BaseModel):
    email: str


class ResetIn(BaseModel):
    token: str
    new_password: str


class OAuthCallbackIn(BaseModel):
    code: str


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(engine)  # (m_20 uses an Alembic migration instead)
    yield


app = FastAPI(title="Exercise 20", lifespan=lifespan)


def invalid_credentials() -> HTTPException:
    return HTTPException(401, "Invalid email or password")


@app.post("/auth/sign-up", status_code=201, dependencies=[Depends(check_origin)])
def sign_up(body: SignUpIn, db: DB, now: Now) -> dict[str, str]:
    email = normalize_email(body.email)
    if len(body.password) < 8:
        raise HTTPException(422, "Password too short")
    user = User(name=body.name, email=email, created_at=now, updated_at=now)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:  # unique email; also covers the race between two sign-ups (no 500)
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
    token = issue_verification(db, f"email-verify:{email}", VERIFY_TTL, now=now)
    db.commit()
    OUTBOX.append({"to": email, "kind": "verify-email", "token": token})
    return {"id": user.id, "email": email}


@app.post("/auth/verify-email")
def verify_email(body: TokenIn, db: DB, now: Now) -> dict[str, bool]:
    email = consume_verification(db, body.token, "email-verify:", now=now)
    if email is None:
        raise HTTPException(400, "Invalid or expired token")
    db.execute(update(User).where(User.email == email).values(email_verified=True))
    db.commit()
    return {"verified": True}


@app.post("/auth/sign-in", dependencies=[Depends(check_origin)])
def sign_in(
    body: SignInIn,
    request: Request,
    response: Response,
    db: DB,
    now: Now,
    session_token: Annotated[str | None, Cookie()] = None,
) -> dict[str, str]:
    user = authenticate(db, body.email, body.password, now)
    if user is None:
        raise invalid_credentials()
    if session_token:  # rotate: drop the session the request arrived with
        db.execute(delete(UserSession).where(UserSession.token_hash == hash_token(session_token)))
    ip = request.client.host if request.client else None
    token = create_session(db, user.id, now=now, ip_address=ip)
    db.commit()
    set_session_cookie(response, token)
    return {"id": user.id, "email": user.email}


@app.post("/auth/sign-out", dependencies=[Depends(check_origin)])
def sign_out(
    response: Response, db: DB, session_token: Annotated[str | None, Cookie()] = None
) -> dict[str, bool]:
    if session_token:
        db.execute(delete(UserSession).where(UserSession.token_hash == hash_token(session_token)))
        db.commit()
    response.delete_cookie(COOKIE_NAME, path="/", secure=True, httponly=True, samesite="lax")
    return {"signed_out": True}


@app.get("/auth/me")
def me(db: DB, now: Now, session_token: Annotated[str | None, Cookie()] = None) -> dict[str, str]:
    row = get_valid_session(db, session_token, now=now) if session_token else None
    user = db.get(User, row.user_id) if row else None
    if user is None:
        raise HTTPException(401, "Not authenticated")
    return {"id": user.id, "email": user.email}


@app.post("/auth/token")
def token_login(body: SignInIn, db: DB, now: Now) -> dict[str, str]:
    user = authenticate(db, body.email, body.password, now)
    if user is None:
        raise invalid_credentials()
    refresh, _ = issue_refresh_token(db, user.id, now=now)
    db.commit()
    return {"access_token": create_access_token(user.id, now=now), "refresh_token": refresh}


@app.post("/auth/token/refresh")
def token_refresh(body: RefreshIn, db: DB, now: Now) -> dict[str, str]:
    try:
        user_id, refresh = rotate_refresh_token(db, body.refresh_token, now=now)
    except InvalidTokenError:
        raise HTTPException(401, "Invalid refresh token") from None
    db.commit()
    return {"access_token": create_access_token(user_id, now=now), "refresh_token": refresh}


@app.post("/auth/forgot-password", status_code=202)
def forgot_password(body: ForgotIn, db: DB, now: Now) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == normalize_email(body.email)))
    if user is not None:
        token = issue_verification(db, f"password-reset:{user.id}", RESET_TTL, now=now)
        db.commit()
        OUTBOX.append({"to": user.email, "kind": "reset-password", "token": token})
    return {"detail": "If that email is registered, a reset link has been sent."}


@app.post("/auth/reset-password")
def reset_password(body: ResetIn, db: DB, now: Now) -> dict[str, bool]:
    user_id = consume_verification(db, body.token, "password-reset:", now=now)
    account = user_id and db.scalar(
        select(Account).where(Account.user_id == user_id, Account.provider_id == "credential")
    )
    if not account or len(body.new_password) < 8:
        raise HTTPException(400, "Invalid or expired token")
    account.password, account.updated_at = password_hasher.hash(body.new_password), now
    revoke_all_for_user(db, account.user_id, now=now)  # sessions AND refresh tokens
    db.commit()
    return {"reset": True}


# Fake provider: authorization code -> profile (a real callback exchanges the code over HTTPS).
FAKE_PROVIDER: dict[tuple[str, str], OAuthProfile] = {
    ("github", "code-grace"): OAuthProfile("github", "gh-1001", "grace@example.com", True, "Grace"),
    ("github", "code-evil"): OAuthProfile("github", "gh-6666", "ada@example.com", False, "Evil"),
    ("google", "code-ada"): OAuthProfile("google", "g-42", "Ada@Example.com", True, "Ada", "at-1"),
}


@app.post("/auth/oauth/{provider}/callback")
def oauth_callback(
    provider: str, body: OAuthCallbackIn, response: Response, db: DB, now: Now
) -> dict[str, str]:
    profile = FAKE_PROVIDER.get((provider, body.code))
    if profile is None:
        raise HTTPException(400, "Invalid authorization code")
    try:
        user = link_oauth_account(db, profile, now=now)
    except OAuthLinkError:
        db.rollback()
        raise HTTPException(409, "account_not_linked") from None
    token = create_session(db, user.id, now=now)
    db.commit()
    set_session_cookie(response, token)
    return {"id": user.id, "email": user.email}
