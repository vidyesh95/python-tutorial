import re
import time

import pytest

httpx = pytest.importorskip("httpx")
respx = pytest.importorskip("respx")
jwt = pytest.importorskip("jwt")

from _loader import load  # noqa: E402

ex = load("t08_forward_deployed", "ex_04_auth_flows_oauth_api_keys")
TOKEN_URL = "https://idp.test/token"
KEY = "k" * 64  # >= 64 bytes avoids pyjwt weak-key warnings


def test_pkce_rfc7636_vector():
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert ex.pkce_challenge(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_generate_verifier_is_valid_and_random():
    values = {ex.generate_verifier() for _ in range(20)}
    assert len(values) == 20
    for v in values:
        assert 43 <= len(v) <= 128
        assert re.fullmatch(r"[A-Za-z0-9\-._~]+", v)


def test_token_cache_reuses_then_refreshes_before_expiry():
    now = {"t": 100.0}
    calls: list[int] = []

    def fetch():
        calls.append(1)
        return f"tok-{len(calls)}", 60.0

    cache = ex.TokenCache(fetch, clock=lambda: now["t"], skew=10.0)
    assert cache.get() == "tok-1"
    now["t"] += 49  # 149 < 100 + 60 - 10 = 150
    assert cache.get() == "tok-1" and len(calls) == 1
    now["t"] += 1  # exactly at the refresh point
    assert cache.get() == "tok-2" and len(calls) == 2


def test_token_cache_invalidate():
    n = {"i": 0}

    def fetch():
        n["i"] += 1
        return f"t{n['i']}", 3600.0

    cache = ex.TokenCache(fetch, clock=lambda: 0.0)
    assert cache.get() == "t1"
    cache.invalidate()
    assert cache.get() == "t2"


def test_fetch_client_credentials_success_uses_basic_auth():
    with respx.mock() as router:
        route = router.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "AT", "expires_in": 120})
        )
        token, ttl = ex.fetch_client_credentials(httpx.Client(), TOKEN_URL, "cid", "s3cr3t", "read")
    request = route.calls.last.request
    assert (token, ttl) == ("AT", 120.0)
    assert request.headers["authorization"].startswith("Basic ")
    assert b"grant_type=client_credentials" in request.content and b"scope=read" in request.content
    assert b"s3cr3t" not in request.content  # the secret travels in the header only


def test_fetch_client_credentials_default_ttl():
    with respx.mock() as router:
        router.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "AT"}))
        assert ex.fetch_client_credentials(httpx.Client(), TOKEN_URL, "c", "s", "r") == (
            "AT",
            300.0,
        )


def test_fetch_client_credentials_error_never_leaks_secret():
    with respx.mock() as router:
        router.post(TOKEN_URL).mock(
            return_value=httpx.Response(401, json={"error": "bad client s3cr3t-value"})
        )
        with pytest.raises(ex.AuthError) as err:
            ex.fetch_client_credentials(httpx.Client(), TOKEN_URL, "cid", "s3cr3t-value", "read")
    assert "s3cr3t-value" not in str(err.value)


def _claims(**over):
    return {"iss": "https://idp", "aud": "api", "sub": "u1", "exp": int(time.time()) + 60} | over


def _validate(token, **over):
    kwargs = {"issuer": "https://idp", "audience": "api", "algorithms": ["HS256"]}
    return ex.validate_jwt(token, KEY, **(kwargs | over))


def test_validate_jwt_accepts_good_token():
    token = jwt.encode(_claims(), KEY, algorithm="HS256")
    assert _validate(token)["sub"] == "u1"


@pytest.mark.parametrize(
    "claims",
    [
        _claims(exp=int(time.time()) - 600),
        _claims(aud="other-api"),
        _claims(iss="https://evil"),
    ],
    ids=["expired", "wrong-aud", "wrong-iss"],
)
def test_validate_jwt_rejects_bad_claims(claims):
    with pytest.raises(ex.AuthError):
        _validate(jwt.encode(claims, KEY, algorithm="HS256"))


def test_validate_jwt_requires_exp_and_sub():
    no_exp = {k: v for k, v in _claims().items() if k != "exp"}
    no_sub = {k: v for k, v in _claims().items() if k != "sub"}
    for claims in (no_exp, no_sub):
        with pytest.raises(ex.AuthError):
            _validate(jwt.encode(claims, KEY, algorithm="HS256"))


def test_validate_jwt_rejects_wrong_signature_and_algorithms():
    with pytest.raises(ex.AuthError):
        _validate(jwt.encode(_claims(), "z" * 64, algorithm="HS256"))
    with pytest.raises(ex.AuthError):
        _validate(jwt.encode(_claims(), None, algorithm="none"))
    with pytest.raises(ex.AuthError):  # HS512 is not in the accepted list
        _validate(jwt.encode(_claims(), KEY, algorithm="HS512"))


def test_api_key_hash_and_verify():
    stored = {"primary": ex.hash_api_key("key-one"), "old": ex.hash_api_key("key-zero")}
    assert re.fullmatch(r"[0-9a-f]{64}", ex.hash_api_key("x"))
    assert ex.verify_api_key("key-one", stored) == "primary"
    assert ex.verify_api_key("key-zero", stored) == "old"
    assert ex.verify_api_key("key-two", stored) is None
    assert ex.verify_api_key("", stored) is None
