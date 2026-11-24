"""Reference solution for Exercise 20: Auth schema, sessions, refresh rotation, OAuth linking."""

import hashlib
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
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(
    db: Session,
    user_id: str,
    *,
    now: datetime,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> str:
    token = new_token()
    db.add(
        UserSession(
            user_id=user_id,
            token_hash=hash_token(token),
            expires_at=now + SESSION_TTL,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            updated_at=now,
        )
    )
    db.flush()
    return token


def get_valid_session(db: Session, token: str, *, now: datetime) -> UserSession | None:
    row = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    return row if row is not None and row.expires_at > now else None


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
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token)))
    if row is None:
        raise InvalidTokenError("unknown refresh token")
    user_id, family_id = row.user_id, row.family_id
    if row.revoked_at is None:
        # Expiry only matters for a token that was never used. Checking it BEFORE the reuse
        # test would let a stolen, already-rotated token be replayed after it expired without
        # triggering family revocation.
        if row.expires_at <= now or row.family_expires_at <= now:
            raise InvalidTokenError("expired refresh token")
        new_raw, new_row = issue_refresh_token(
            db, user_id, now=now, family_id=family_id, family_expires_at=row.family_expires_at
        )
        claimed = db.execute(
            update(RefreshToken)
            .where(RefreshToken.id == row.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now, replaced_by=new_row.id)
        )
        if claimed.rowcount == 1:
            return user_id, new_raw
        db.rollback()  # lost a race against a concurrent refresh: treat as reuse
    revoke_family(db, family_id, now=now)
    db.commit()  # must persist even though we raise
    raise InvalidTokenError("refresh token reuse detected: family revoked")


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
    digest = hash_token(token)
    row = db.scalar(
        select(Verification).where(
            Verification.value_hash == digest, Verification.identifier.startswith(prefix)
        )
    )
    # No compare_digest: the row was found BY HASH, so there is nothing left to compare. Constant
    # time matters when Python compares an attacker-supplied value with a secret it holds
    # (webhook HMAC signatures, the OAuth state cookie), not after a database lookup by hash.
    if row is None or row.expires_at <= now:
        return None
    if db.execute(delete(Verification).where(Verification.id == row.id)).rowcount != 1:
        return None
    return row.identifier.removeprefix(prefix)


def link_oauth_account(db: Session, profile: OAuthProfile, *, now: datetime) -> User:
    tokens = {
        k: getattr(profile, k) for k in ("access_token", "refresh_token", "id_token", "scope")
    }
    account = db.scalar(
        select(Account).where(
            Account.provider_id == profile.provider_id, Account.account_id == profile.account_id
        )
    )
    if account is not None:
        for key, value in tokens.items():
            if value is not None:  # Google sends a refresh_token only on the first consent:
                setattr(account, key, value)  # a later login must not wipe the stored one
        account.updated_at = now
        return db.get_one(User, account.user_id)
    if not profile.email_verified:
        # Unverified provider email: it may neither link to an existing user (takeover) nor
        # create one (the new row would claim the address with the attacker's identity attached,
        # and stay usable by them after the real owner later verifies the email).
        raise OAuthLinkError("provider email is not verified")
    email = normalize_email(profile.email)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
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
        # Pre-hijacking defense: nothing attached to an unverified row can be trusted. Evict
        # EVERY existing login method (password AND any linked identity), all sessions/tokens.
        db.execute(delete(Account).where(Account.user_id == user.id))
        revoke_all_for_user(db, user.id, now=now)
        user.email_verified, user.updated_at = True, now
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
