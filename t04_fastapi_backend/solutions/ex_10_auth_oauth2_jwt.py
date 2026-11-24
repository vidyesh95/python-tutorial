"""Reference solution for Exercise 10: Password hashing, JWTs and a protected route."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash

SECRET_KEY = "exercise-secret-key-not-for-production-0123456789"
ALGORITHM = "HS256"

_hasher = PasswordHash.recommended()


class AuthError(Exception):
    """Raised by decode_token for any invalid token."""


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _hasher.verify(password, hashed)


def create_access_token(
    subject: str,
    secret: str,
    expires_delta: timedelta = timedelta(minutes=30),
    now: datetime | None = None,
) -> str:
    now = now or datetime.now(UTC)
    payload = {"sub": subject, "iat": now, "exp": now + expires_delta}
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_token(token: str, secret: str) -> str:
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError as exc:
        raise AuthError(str(exc)) from exc
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise AuthError("token has no subject")
    return subject


def authenticate(users: dict[str, dict], username: str, password: str) -> dict | None:
    user = users.get(username)
    if user is None or not verify_password(password, user["password_hash"]):
        return None
    return user


USERS: dict[str, dict] = {}


def seed_users() -> None:
    USERS.clear()
    USERS["ada"] = {"username": "ada", "password_hash": hash_password("analytical-engine")}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        username = decode_token(token, SECRET_KEY)
    except AuthError:
        raise unauthorized from None
    user = USERS.get(username)
    if user is None:
        raise unauthorized
    return user


app = FastAPI(title="Exercise 10")


@app.post("/token")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> dict[str, str]:
    user = authenticate(USERS, form.username, form.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password")
    return {
        "access_token": create_access_token(user["username"], SECRET_KEY),
        "token_type": "bearer",
    }


@app.get("/users/me")
def read_me(user: Annotated[dict, Depends(get_current_user)]) -> dict[str, str]:
    return {"username": user["username"]}
