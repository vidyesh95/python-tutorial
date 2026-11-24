"""Reference solution for exercise 04."""

import base64
import hashlib
import hmac
import secrets
from collections.abc import Callable
from typing import Any

import httpx
import jwt


class AuthError(Exception):
    """Authentication failed. Messages must NEVER contain secrets."""


def generate_verifier() -> str:
    return secrets.token_urlsafe(48)  # 64 chars of [A-Za-z0-9_-]


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class TokenCache:
    def __init__(
        self,
        fetch: Callable[[], tuple[str, float]],
        clock: Callable[[], float],
        skew: float = 30.0,
    ) -> None:
        self._fetch, self._clock, self._skew = fetch, clock, skew
        self._token: str | None = None
        self._refresh_at = 0.0

    def get(self) -> str:
        if self._token is None or self._clock() >= self._refresh_at:
            token, expires_in = self._fetch()
            self._token = token
            self._refresh_at = self._clock() + expires_in - self._skew
        return self._token

    def invalidate(self) -> None:
        self._token = None


def fetch_client_credentials(
    http: httpx.Client, token_url: str, client_id: str, client_secret: str, scope: str
) -> tuple[str, float]:
    resp = http.post(
        token_url,
        data={"grant_type": "client_credentials", "scope": scope},
        auth=(client_id, client_secret),
    )
    if resp.status_code != 200:
        raise AuthError(f"token endpoint returned HTTP {resp.status_code}")
    try:
        body = resp.json()
        return body["access_token"], float(body.get("expires_in", 300))
    except (ValueError, KeyError, TypeError) as exc:
        raise AuthError("token endpoint returned an unexpected body") from exc


def validate_jwt(
    token: str, key: Any, *, issuer: str, audience: str, algorithms: list[str]
) -> dict:
    try:
        return jwt.decode(
            token,
            key,
            algorithms=algorithms,
            issuer=issuer,
            audience=audience,
            leeway=5,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthError(f"invalid token: {type(exc).__name__}") from exc


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(presented: str, stored: dict[str, str]) -> str | None:
    digest = hash_api_key(presented)
    match: str | None = None
    for key_id, expected in stored.items():
        if hmac.compare_digest(digest, expected):
            match = key_id
    return match
