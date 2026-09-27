from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import jwt
import pytest
from app.features.auth.jwt import AuthError, JwtVerifier, TokenClaims, jwks_key_resolver
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "https://example.supabase.co/auth/v1"
AUDIENCE = "authenticated"
SUBJECT = "11111111-1111-1111-1111-111111111111"


def _rsa_keypair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


PRIVATE_KEY, PUBLIC_KEY = _rsa_keypair()
OTHER_PRIVATE_KEY, _OTHER_PUBLIC_KEY = _rsa_keypair()


def _claims(**overrides: object) -> dict[str, object]:
    now = int(time.time())
    payload: dict[str, object] = {
        "sub": SUBJECT,
        "email": "ada@example.com",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 3600,
        "user_metadata": {"full_name": "Ada Lovelace"},
    }
    payload.update(overrides)
    return payload


def _token(payload: dict[str, object], key: str = PRIVATE_KEY, algorithm: str = "RS256") -> str:
    return jwt.encode(payload, key, algorithm=algorithm)


def _b64url(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def _forged_hs256_token(payload: dict[str, object], secret: str) -> str:
    """Build an HS256 JWT by hand: PyJWT itself refuses to `encode` with a PEM-shaped
    HMAC secret, but an attacker isn't bound by that guard, so the verifier must be."""
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = _b64url(json.dumps(header).encode()) + b"." + _b64url(json.dumps(payload).encode())
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return (signing_input + b"." + _b64url(signature)).decode()


def _verifier(key: str = PUBLIC_KEY) -> JwtVerifier:
    return JwtVerifier(key_resolver=lambda token: key, issuer=ISSUER, audience=AUDIENCE)


def test_accepts_a_valid_token_and_returns_sub_and_email() -> None:
    token = _token(_claims())

    claims = _verifier().verify(token)

    assert claims == TokenClaims(sub=SUBJECT, email="ada@example.com", display_name="Ada Lovelace")


def test_rejects_an_expired_token() -> None:
    token = _token(_claims(exp=int(time.time()) - 3600))

    with pytest.raises(AuthError) as exc_info:
        _verifier().verify(token)

    assert exc_info.value.reason == "expired"


def test_rejects_a_token_signed_by_another_key() -> None:
    token = _token(_claims(), key=OTHER_PRIVATE_KEY)

    with pytest.raises(AuthError) as exc_info:
        _verifier().verify(token)

    assert exc_info.value.reason == "bad_signature"


def test_rejects_a_wrong_audience() -> None:
    token = _token(_claims(aud="some-other-audience"))

    with pytest.raises(AuthError) as exc_info:
        _verifier().verify(token)

    assert exc_info.value.reason == "bad_audience"


def test_rejects_a_wrong_issuer() -> None:
    token = _token(_claims(iss="https://evil.example.com/auth/v1"))

    with pytest.raises(AuthError) as exc_info:
        _verifier().verify(token)

    assert exc_info.value.reason == "bad_issuer"


def test_rejects_alg_none() -> None:
    token = jwt.encode(_claims(), key=None, algorithm="none")

    with pytest.raises(AuthError) as exc_info:
        _verifier().verify(token)

    assert exc_info.value.reason == "unsupported_alg"


def test_rejects_an_hs256_token_signed_with_the_public_key_text() -> None:
    token = _forged_hs256_token(_claims(), secret=PUBLIC_KEY)

    with pytest.raises(AuthError) as exc_info:
        _verifier().verify(token)

    assert exc_info.value.reason == "unsupported_alg"


def test_rejects_a_token_without_sub() -> None:
    payload = _claims()
    del payload["sub"]
    token = _token(payload)

    with pytest.raises(AuthError) as exc_info:
        _verifier().verify(token)

    assert exc_info.value.reason == "missing_claim"


def test_rejects_a_token_without_email() -> None:
    payload = _claims()
    del payload["email"]
    token = _token(payload)

    with pytest.raises(AuthError) as exc_info:
        _verifier().verify(token)

    assert exc_info.value.reason == "missing_claim"


def test_rejects_a_non_jwt_string() -> None:
    with pytest.raises(AuthError) as exc_info:
        _verifier().verify("not-a-jwt")

    assert exc_info.value.reason == "malformed"


def test_accepts_a_token_within_clock_leeway_of_expiry() -> None:
    token = _token(_claims(exp=int(time.time()) - 5))

    claims = _verifier().verify(token)

    assert claims.sub == SUBJECT


def test_jwks_key_resolver_returns_a_callable_without_hitting_the_network() -> None:
    resolver = jwks_key_resolver("https://example.supabase.co/auth/v1/.well-known/jwks.json")

    assert callable(resolver)
