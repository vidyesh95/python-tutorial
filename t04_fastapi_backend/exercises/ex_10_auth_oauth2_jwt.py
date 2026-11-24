"""Exercise 10: Password hashing, JWTs and a protected route.

Tasks
1. hash_password / verify_password: use `pwdlib.PasswordHash.recommended()` (Argon2).
   The hash must differ from the password and differ between calls (random salt).
2. create_access_token(subject, secret, expires_delta=30 min, now=None): HS256 JWT with
   claims "sub", "iat" and "exp" (now + expires_delta). `now` defaults to datetime.now(UTC).
3. decode_token(token, secret): return the "sub" claim. Raise AuthError for ANY problem:
   expired, bad signature, malformed, or no string "sub". Pin the algorithm (HS256) when decoding.
4. authenticate(users, username, password): return the user dict if the username exists and the
   password matches its "password_hash"; otherwise None.
5. get_current_user: the FastAPI dependency behind GET /users/me. Decode the bearer token with
   SECRET_KEY, look the user up in USERS, and raise
   HTTPException(401, "Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
   when the token is invalid or the user is unknown. Return the user dict.
   (`/token` is already written using tasks 1, 2 and 4. `seed_users()` uses task 1.)

Run: uv run pytest t04_fastapi_backend -k ex_10
"""

from datetime import UTC, datetime, timedelta  # noqa: F401
from typing import Annotated

import jwt  # noqa: F401
from fastapi import Depends, FastAPI, HTTPException, status  # noqa: F401
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash  # noqa: F401

SECRET_KEY = "exercise-secret-key-not-for-production-0123456789"
ALGORITHM = "HS256"


class AuthError(Exception):
    """Raised by decode_token for any invalid token."""


def hash_password(password: str) -> str:
    raise NotImplementedError


def verify_password(password: str, hashed: str) -> bool:
    raise NotImplementedError


def create_access_token(
    subject: str,
    secret: str,
    expires_delta: timedelta = timedelta(minutes=30),
    now: datetime | None = None,
) -> str:
    raise NotImplementedError


def decode_token(token: str, secret: str) -> str:
    raise NotImplementedError


def authenticate(users: dict[str, dict], username: str, password: str) -> dict | None:
    raise NotImplementedError


USERS: dict[str, dict] = {}


def seed_users() -> None:
    USERS.clear()
    USERS["ada"] = {"username": "ada", "password_hash": hash_password("analytical-engine")}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    raise NotImplementedError


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
