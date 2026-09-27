from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.algorithms import AllowedPublicKeys

ALGORITHMS = ("RS256", "ES256")
REQUIRED_CLAIMS = ("exp", "iat", "sub", "iss", "aud")
CLOCK_LEEWAY_SECONDS = 10

KeyResolver = Callable[[str], AllowedPublicKeys | str | bytes]

_REASON_BY_EXCEPTION: dict[type[Exception], str] = {
    jwt.ExpiredSignatureError: "expired",
    jwt.InvalidSignatureError: "bad_signature",
    jwt.InvalidAudienceError: "bad_audience",
    jwt.InvalidIssuerError: "bad_issuer",
    jwt.InvalidAlgorithmError: "unsupported_alg",
    jwt.MissingRequiredClaimError: "missing_claim",
    jwt.DecodeError: "malformed",
}


@dataclass(frozen=True)
class TokenClaims:
    sub: str
    email: str
    display_name: str | None = None


class AuthError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _translate(exc: Exception) -> AuthError:
    return AuthError(_REASON_BY_EXCEPTION.get(type(exc), "malformed"))


def _build_claims(payload: dict[str, Any]) -> TokenClaims:
    email = payload.get("email")
    if not email:
        raise AuthError("missing_claim")
    display_name = payload.get("user_metadata", {}).get("full_name")
    return TokenClaims(sub=payload["sub"], email=email, display_name=display_name)


class JwtVerifier:
    """Database-free verification of a Supabase access token against its JWKS."""

    def __init__(self, key_resolver: KeyResolver, issuer: str, audience: str) -> None:
        self._key_resolver = key_resolver
        self._issuer = issuer
        self._audience = audience

    def verify(self, token: str) -> TokenClaims:
        try:
            key = self._key_resolver(token)
            payload = jwt.decode(
                token,
                key,
                algorithms=list(ALGORITHMS),
                audience=self._audience,
                issuer=self._issuer,
                leeway=CLOCK_LEEWAY_SECONDS,
                options={"require": list(REQUIRED_CLAIMS)},
            )
        except jwt.PyJWTError as exc:
            raise _translate(exc) from exc
        return _build_claims(payload)


def jwks_key_resolver(url: str) -> KeyResolver:
    """Production key resolver: fetches and caches the project's JWKS over HTTP."""

    client = PyJWKClient(url, cache_keys=True)
    return lambda token: client.get_signing_key_from_jwt(token).key
