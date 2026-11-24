# Auth Flows: OAuth and API Keys
"""
Every customer integration starts with "how do we authenticate?". Pick the simplest flow that
matches WHO is acting.

1. API KEYS (service-to-service, simplest)
   - Sent as `Authorization: Bearer <key>` or a vendor header. Treat like a password.
   - Store only a HASH on the server side of your own services (sha256 is fine for random,
     high-entropy keys); compare with `hmac.compare_digest` (constant time, no timing leaks).
   - Support TWO active keys per client so rotation has zero downtime. Scope keys (read-only).
2. OAUTH2 CLIENT CREDENTIALS (machine-to-machine, no user)
   - POST `grant_type=client_credentials` with client id/secret -> short-lived access token.
   - CACHE the token until shortly before `expires_in`; do not fetch one per request.
3. OAUTH2 AUTHORIZATION CODE + PKCE (a USER grants your app access to their data)
   - Redirect the user to `/authorize` with `code_challenge = BASE64URL(SHA256(verifier))`
     and a random `state`; they log in at THEIR identity provider; it redirects back with
     `code` + `state`. You verify `state` (CSRF defense), then POST the `code` plus the original
     `code_verifier` to `/token`. An attacker who steals the code cannot use it without the
     verifier. PKCE is now recommended even for confidential clients.
4. REFRESH TOKENS: long-lived, exchanged for new access tokens. Many providers ROTATE them (each
   refresh returns a new one and invalidates the old): always persist the newest, encrypted.
5. JWT VALIDATION (when the customer's IdP issues JWT access tokens to YOUR API)
   - Verify the SIGNATURE with the issuer's public key (JWKS), pin the ALGORITHMS you accept
     (never trust the token's own `alg` header: "none" and HS256-with-public-key attacks),
     and check `exp`, `iss`, `aud` (and `nbf`). Require the claims to exist.

Libraries: `httpx` for calls, `authlib` for OAuth flows and PKCE helpers, `pyjwt` for JWTs.
authlib's httpx client may sit on `httpx2` (a fork); the lesson imports whichever it uses.
Everything here is mocked (respx / MockTransport); no secrets are real and none are printed.
Run: uv run python -m t08_forward_deployed.m_04_auth_flows_oauth_api_keys
"""

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import respx
from authlib.integrations.httpx_client import OAuth2Client
from cryptography.hazmat.primitives.asymmetric import rsa

try:  # authlib >= 1.7 builds on httpx2; older releases use httpx
    import httpx2 as authlib_httpx
except ImportError:  # pragma: no cover
    authlib_httpx = httpx

TOKEN_URL = "https://idp.customer.test/oauth/token"


class AuthError(Exception):
    """Authentication failed. Messages must never contain secrets."""


# Example 1: API keys: store hashes, compare in constant time, check ALL candidates
def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def verify_key(presented: str, stored: dict[str, str]) -> str | None:
    """stored maps key-id -> sha256 hex. Returns the matching key id (or None)."""
    digest, match = hash_key(presented), None
    for key_id, expected in stored.items():  # no early exit: same work whether or not it matches
        if hmac.compare_digest(digest, expected):
            match = key_id
    return match


# Example 2: client credentials + an expiry-aware cache
@dataclass
class Token:
    access_token: str
    expires_at: float  # monotonic seconds
    refresh_token: str | None = None

    def __repr__(self) -> str:  # keep secrets out of logs and tracebacks
        return f"Token(expires_at={self.expires_at:.0f}, access_token=***)"


def fetch_client_credentials(
    http: httpx.Client, client_id: str, client_secret: str, scope: str, clock=time.monotonic
) -> Token:
    resp = http.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials", "scope": scope},
        auth=(client_id, client_secret),  # HTTP Basic, the most widely supported method
    )
    if resp.status_code != 200 or "access_token" not in resp.json():
        raise AuthError(
            f"token endpoint returned HTTP {resp.status_code}"
        )  # no body: may echo input
    body = resp.json()
    return Token(body["access_token"], clock() + float(body.get("expires_in", 300)))


class TokenCache:
    """Hands out a valid token; refreshes `skew` seconds before expiry; thread-safe."""

    def __init__(
        self, fetch: Callable[[], Token], clock=time.monotonic, skew: float = 30.0
    ) -> None:
        self._fetch, self._clock, self._skew = fetch, clock, skew
        self._token: Token | None = None
        self._lock = threading.Lock()

    def get(self) -> str:
        with self._lock:  # one thread refreshes; the others reuse the result
            if self._token is None or self._clock() >= self._token.expires_at - self._skew:
                self._token = self._fetch()
            return self._token.access_token

    def invalidate(self) -> None:  # call after a 401: the token may have been revoked
        with self._lock:
            self._token = None


# Example 3: PKCE by hand (what authlib does for you)
def make_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)  # 86 URL-safe chars (RFC 7636 allows 43..128)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def check_state(expected: str, returned: str) -> None:
    if not hmac.compare_digest(expected, returned):
        raise AuthError("state mismatch: possible CSRF, abort the login")


# Example 4: JWT validation against a JWKS (local keypair stands in for the customer's IdP)
def make_idp() -> tuple[object, dict]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update(kid="key-1", alg="RS256", use="sig")
    return key, {"keys": [jwk]}


def validate_jwt(token: str, jwks: dict, issuer: str, audience: str) -> dict:
    try:
        kid = jwt.get_unverified_header(token).get("kid")  # only to PICK the key, nothing else
        signing_key = jwt.PyJWKSet.from_dict(jwks)[kid].key
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],  # pinned: ignore whatever the token claims
            issuer=issuer,
            audience=audience,
            leeway=10,  # tolerate small clock skew
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except (jwt.PyJWTError, KeyError) as exc:
        raise AuthError(f"invalid token: {type(exc).__name__}") from exc


def run_demo() -> None:
    # API keys
    key = "sk_live_" + secrets.token_hex(16)  # shown only as a length: never print keys
    stored = {"primary": hash_key(key), "previous": hash_key("sk_live_old")}
    print("api key ok:", verify_key(key, stored), "| wrong key:", verify_key("nope", stored))

    # Client credentials + cache
    issued = {"n": 0}

    def token_endpoint(request: httpx.Request) -> httpx.Response:
        issued["n"] += 1
        return httpx.Response(200, json={"access_token": f"AT-{issued['n']}", "expires_in": 60})

    now = {"t": 1000.0}
    with respx.mock() as router:
        router.post(TOKEN_URL).mock(side_effect=token_endpoint)
        http = httpx.Client()
        cache = TokenCache(
            lambda: fetch_client_credentials(http, "cid", "csecret", "read", lambda: now["t"]),
            clock=lambda: now["t"],
        )
        first, again = cache.get(), cache.get()
        now["t"] += 40  # inside the 30s skew window of a 60s token -> refresh
        refreshed = cache.get()
        print("cache:", first, again, refreshed, "| token calls:", issued["n"])
        print("repr is safe:", Token("secret-value", 5.0))

    # PKCE pair (verifier stays secret on the client; only the challenge is sent)
    _, challenge = make_pkce()
    print("pkce challenge length:", len(challenge))

    # Authorization code + PKCE + refresh with authlib (token endpoint mocked in-process)
    def idp(request: authlib_httpx.Request) -> authlib_httpx.Response:
        form = parse_qs(request.content.decode())
        n = 2 if form["grant_type"] == ["refresh_token"] else 1
        return authlib_httpx.Response(
            200,
            json={
                "access_token": f"AT-{n}",
                "refresh_token": f"RT-{n}",
                "token_type": "Bearer",
                "expires_in": 3600,
            },
        )

    client = OAuth2Client(
        "public-client-id",
        redirect_uri="https://app.test/callback",
        scope="read",
        code_challenge_method="S256",
        token_endpoint_auth_method="none",  # public client: PKCE replaces the secret
        transport=authlib_httpx.MockTransport(idp),
    )
    verifier, _ = make_pkce()
    url, state = client.create_authorization_url(
        "https://idp.customer.test/authorize", code_verifier=verifier
    )
    query = parse_qs(urlparse(url).query)
    print("authorize params:", sorted(query))
    check_state(state, query["state"][0])  # what you do when the redirect comes back
    token = client.fetch_token(
        TOKEN_URL, code="one-time-code", code_verifier=verifier, grant_type="authorization_code"
    )
    rotated = client.refresh_token(TOKEN_URL, refresh_token=token["refresh_token"])
    print("refresh rotated:", token["refresh_token"], "->", rotated["refresh_token"])

    # JWT validation
    private, jwks = make_idp()
    claims = {
        "iss": "https://idp.customer.test",
        "aud": "orders-api",
        "sub": "svc-1",
        "exp": int(time.time()) + 300,
    }
    good = jwt.encode(claims, private, algorithm="RS256", headers={"kid": "key-1"})
    print("jwt ok:", validate_jwt(good, jwks, claims["iss"], "orders-api")["sub"])
    attacks = {
        "expired": jwt.encode(
            claims | {"exp": int(time.time()) - 60},
            private,
            algorithm="RS256",
            headers={"kid": "key-1"},
        ),
        "wrong audience": good,
        "alg=none": jwt.encode(claims, None, algorithm="none", headers={"kid": "key-1"}),
        "HS256 forged": jwt.encode(claims, "x" * 64, algorithm="HS256", headers={"kid": "key-1"}),
    }
    for name, bad in attacks.items():
        audience = "someone-else" if name == "wrong audience" else "orders-api"
        try:
            validate_jwt(bad, jwks, claims["iss"], audience)
        except AuthError as exc:
            print(f"  rejected {name}: {exc}")


"""
Common mistakes:
- Hardcoding secrets, committing `.env`, pasting tokens into tickets or logs. Rotate if it happens.
- Comparing secrets with `==` (timing side channel): use `hmac.compare_digest`.
- `jwt.decode(..., options={"verify_signature": False})` "just to read the claims" in prod code,
  or omitting `algorithms=` so the token chooses its own algorithm.
- Skipping `aud`/`iss` checks: a token minted for another API then works on yours.
- Fetching a new OAuth token on every request (rate limited, slow); or never refreshing and
  failing at the one-hour mark.
- Losing a rotated refresh token (you must save the new one) or storing it in plain text.
- Skipping `state` on redirects, or using the implicit flow (tokens in URLs).

Production notes:
- Secrets come from env vars locally and a secret manager in the cloud (t05 m_13), injected at
  runtime; give each integration its own least-privilege credential and its own scopes.
- Log the token's `sub`, scopes and expiry, NEVER the token. Redact `Authorization` headers.
- Ask the customer's IT for: token endpoint, scopes, token lifetime, rotation policy, who owns
  the client registration, and how to revoke it in an incident.
- Cache JWKS with a TTL and refetch once on an unknown `kid` (key rotation).
- For a browser or mobile app use authorization code + PKCE; never embed a client secret there.
"""

if __name__ == "__main__":
    run_demo()
