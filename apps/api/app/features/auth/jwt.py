from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import jwt
from jwt import PyJWKClient
from jwt.algorithms import AllowedPublicKeys
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError, field_validator

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


def _string_or_none(value: object) -> object:
    """Treat any non-string value as absent: a display name is optional and never trusted by type."""
    return value if isinstance(value, str) else None


class UserMetadata(BaseModel):
    """The `user_metadata` object of a Supabase access token; only the display name is read."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    full_name: Annotated[str | None, BeforeValidator(_string_or_none)] = None


class JwtClaims(BaseModel):
    """The verified claims the application reads from a Supabase access token."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    sub: str
    email: str = Field(min_length=1)
    user_metadata: UserMetadata | None = None

    @field_validator("email")
    @classmethod
    def _email_has_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("email must not be blank")
        return value

    @property
    def display_name(self) -> str | None:
        """Return the token's full name, or ``None`` when the token carries none."""
        return self.user_metadata.full_name if self.user_metadata is not None else None


class AuthError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _translate(exc: Exception) -> AuthError:
    return AuthError(_REASON_BY_EXCEPTION.get(type(exc), "malformed"))


def _claims_from(payload: dict[str, object]) -> JwtClaims:
    """Validate the decoded payload once; a missing or blank email is `missing_claim`, any other defect `malformed`."""
    email = payload.get("email")
    if email is None or (isinstance(email, str) and not email.strip()):
        raise AuthError("missing_claim")
    try:
        return JwtClaims.model_validate(payload)
    except ValidationError as exc:
        raise AuthError("malformed") from exc


class JwtVerifier:
    """Database-free verification of a Supabase access token against its JWKS."""

    def __init__(self, key_resolver: KeyResolver, issuer: str, audience: str) -> None:
        self._key_resolver = key_resolver
        self._issuer = issuer
        self._audience = audience

    def verify(self, token: str) -> JwtClaims:
        """Return the claims of a valid token, or raise `AuthError` with the reason it was refused."""
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
        return _claims_from(payload)


def jwks_key_resolver(url: str) -> KeyResolver:
    """Production key resolver: fetches and caches the project's JWKS over HTTP."""
    client = PyJWKClient(url, cache_keys=True)
    return lambda token: client.get_signing_key_from_jwt(token).key
