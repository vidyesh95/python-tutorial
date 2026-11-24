# Authentication with OAuth2 Password Flow and JWT
"""
Authentication = "who are you?". The standard FastAPI recipe:

1. Register: store a password HASH (never the password). `pwdlib` + Argon2 is the modern
   choice: slow on purpose, salted, parameters embedded in the hash string.
2. Login: client POSTs `username` + `password` (form fields) to `/token`. We verify the hash
   and return a signed JWT: {"access_token": "...", "token_type": "bearer"}.
3. Calls: client sends `Authorization: Bearer <jwt>`. A dependency (`get_current_user`)
   verifies the signature + expiry, loads the user, or answers 401.

JWT = three base64 parts `header.payload.signature`. The payload is SIGNED, not encrypted:
anyone can read it, nobody can alter it without the secret. Standard claims used here:
`sub` (subject = user id/name), `iat` (issued at), `exp` (expiry, enforced by PyJWT).

FastAPI pieces:
- `OAuth2PasswordBearer(tokenUrl="token")`: dependency that extracts the bearer token and
  makes the "Authorize" button appear in /docs.
- `OAuth2PasswordRequestForm`: parses the login form (needs `python-multipart`, included in
  fastapi[standard]).
- 401 responses should carry `WWW-Authenticate: Bearer`.

Secret handling: `SECRET_KEY` comes from the environment. A dev default exists so the lesson
runs, but it triggers a warning - never ship the default.
Generate a real one:  python -c "import secrets; print(secrets.token_urlsafe(48))"

Serve it live:  uv run fastapi dev t04_fastapi_backend/m_10_auth_oauth2_jwt.py
                (open /docs, click Authorize, log in as ada / correct-horse-battery)
Run the offline demo: uv run python -m t04_fastapi_backend.m_10_auth_oauth2_jwt
"""

import os
import warnings
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from pydantic import BaseModel

# Example: configuration from the environment (with a loud dev default)
DEV_SECRET = "dev-only-secret-change-me-0123456789abcdef"
SECRET_KEY = os.environ.get("SECRET_KEY", DEV_SECRET)
if SECRET_KEY == DEV_SECRET:
    warnings.warn("SECRET_KEY not set: using the insecure development default!", stacklevel=1)
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30

# Example: password hashing (Argon2 by default)
password_hash = PasswordHash.recommended()
DB: dict[str, dict[str, str]] = {
    "ada": {
        "username": "ada",
        "full_name": "Ada Lovelace",
        "password_hash": password_hash.hash("correct-horse-battery"),
    },
}
# Hash verified for unknown users too, so response time doesn't reveal which names exist
DUMMY_HASH = password_hash.hash("not-a-real-password")


# Example: create / verify JWTs
def create_access_token(subject: str, expires: timedelta | None = None) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + (expires or timedelta(minutes=ACCESS_TOKEN_MINUTES)),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str:
    """Return the subject or raise jwt.InvalidTokenError (expired, tampered, malformed...)."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # pin the algorithm!
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise jwt.InvalidTokenError("missing sub")
    return subject


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    username: str
    full_name: str


# Example: the dependency chain
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict[str, str]:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        username = decode_token(token)
    except jwt.InvalidTokenError:
        raise unauthorized from None
    user = DB.get(username)
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[dict[str, str], Depends(get_current_user)]

app = FastAPI(title="Auth Demo")


@app.post("/token")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = DB.get(form.username)
    stored = user["password_hash"] if user else DUMMY_HASH
    valid = password_hash.verify(form.password, stored)
    if user is None or not valid:  # same message for both: don't reveal which part was wrong
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user["username"]))


@app.get("/users/me")
def read_me(user: CurrentUser) -> UserOut:
    return UserOut(**{k: user[k] for k in ("username", "full_name")})  # never the hash


"""
Common mistakes:
- Storing plain or fast-hashed (MD5/SHA256) passwords. Use Argon2/bcrypt via pwdlib.
- `jwt.decode(token, key)` without `algorithms=[...]` - lets attackers pick the algorithm.
- Putting secrets/PII in the JWT payload: it is only base64, not encrypted.
- Forgetting `exp`: a leaked token then works forever.
- Different error messages for "no such user" vs "wrong password" (user enumeration).
- Committing SECRET_KEY, or using one default key across environments.
- Sending credentials over plain HTTP.

Production notes:
- Serve over HTTPS only; set short access-token lifetimes (5-30 min) plus refresh tokens
  stored server-side so they can be revoked.
- Rotate SECRET_KEY on a schedule (support old+new keys during the switch, or use `kid`).
- For multiple services use asymmetric signing (RS256/EdDSA): services verify with a public
  key and never hold the signing secret.
- Rate limit `/token` and lock/slow down repeated failures (brute force protection).
- Authentication (who) is not authorization (may they?): check ownership/roles/scopes in
  your handlers or dependencies.
- Consider an identity provider (Auth0, Cognito, Keycloak) instead of rolling your own.
"""

if __name__ == "__main__":
    client = TestClient(app)
    print(client.get("/users/me").status_code)  # 401: no token
    bad = client.post("/token", data={"username": "ada", "password": "nope"})
    print(bad.status_code, bad.json())
    ok = client.post("/token", data={"username": "ada", "password": "correct-horse-battery"})
    token = ok.json()["access_token"]
    print(ok.status_code, token[:20] + "...", "-> parts:", len(token.split(".")))
    print(jwt.decode(token, options={"verify_signature": False}))  # payload is readable!
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    print(me.status_code, me.json())
    expired = create_access_token("ada", expires=timedelta(seconds=-5))
    print(client.get("/users/me", headers={"Authorization": f"Bearer {expired}"}).json())
    forged = token[:-3] + ("AAA" if not token.endswith("AAA") else "BBB")
    print(client.get("/users/me", headers={"Authorization": f"Bearer {forged}"}).status_code)
