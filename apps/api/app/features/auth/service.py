"""Application services for users and API keys: resolve token claims to users and issue or verify keys."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from app.features.auth.jwt import JwtClaims
from app.features.auth.repository import ApiKeyRepository, UserRepository
from app.models import AppUser
from app.models.api_key import ApiKey
from app.models.user import UserRole

KEY_PREFIX = "rt_"
LAST_USED_THROTTLE = timedelta(minutes=1)


class UnknownRoleError(ValueError):
    """Raised when a role name is not one of the defined user roles."""

    def __init__(self, role: str) -> None:
        """Build the message from the rejected role and the list of valid roles."""
        valid = ", ".join(member.value for member in UserRole)
        super().__init__(f"unknown role {role!r}; valid roles: {valid}")


class UnknownUserError(ValueError):
    """Raised when no user has the given email."""

    def __init__(self, email: str) -> None:
        """Build the message from the email that matched no user."""
        super().__init__(f"no user with email {email!r}")


class UserService:
    """Resolve verified claims to users and manage user roles."""

    def __init__(self, repository: UserRepository) -> None:
        """Bind the service to its user repository."""
        self._repo = repository

    def resolve(self, claims: JwtClaims) -> AppUser:
        """Create or refresh the user named by verified token claims; the email is stored lowercase."""
        return self._repo.upsert(
            id=uuid.UUID(claims.sub),
            email=claims.email.lower(),
            display_name=claims.display_name,
        )

    def get(self, user_id: uuid.UUID) -> AppUser | None:
        """Return the user with this id, or `None` when none exists."""
        return self._repo.get(user_id)

    def set_role(self, email: str, role: str) -> AppUser:
        """Assign a role to the user with this email; raise if the role or the user is unknown."""
        try:
            parsed_role = UserRole(role)
        except ValueError:
            raise UnknownRoleError(role) from None
        user = self._repo.get_by_email(email)
        if user is None:
            raise UnknownUserError(email)
        user.role = parsed_role
        return user


class ApiKeyError(Exception):
    """Raised for an unknown or revoked API key; both cases look identical to the caller."""


class ApiKeyService:
    """Issue, verify and revoke machine API keys; only a hash of each key is stored."""

    def __init__(self, repository: ApiKeyRepository) -> None:
        """Bind the service to its API-key repository."""
        self._repo = repository

    def issue(self, name: str) -> str:
        """Create a key, store only its hash, and return the plaintext once."""
        key = self._generate()
        self._repo.create(name=name, key_hash=self._hash(key), key_prefix=key.removeprefix(KEY_PREFIX)[:8])
        return key

    def get(self, key_id: uuid.UUID) -> ApiKey | None:
        """Return the API key with this id, or `None` when none exists."""
        return self._repo.get(key_id)

    def verify(self, key: str) -> ApiKey:
        """Return the record for a presented key; refuse unknown or revoked keys with one shared error."""
        key_hash = self._hash(key)
        record = self._repo.get_by_hash(key_hash)
        if record is None or not hmac.compare_digest(record.key_hash, key_hash) or record.revoked_at is not None:
            raise ApiKeyError("unknown or revoked API key")
        self._touch_last_used(record)
        return record

    def revoke(self, key_prefix: str) -> ApiKey:
        """Mark the key with this prefix as revoked; raise if no key has that prefix."""
        record = self._repo.get_by_prefix(key_prefix)
        if record is None:
            raise ApiKeyError(f"no API key with prefix {key_prefix!r}")
        record.revoked_at = datetime.now(UTC)
        return record

    def _touch_last_used(self, record: ApiKey) -> None:
        now = datetime.now(UTC)
        if record.last_used_at is None or now - record.last_used_at >= LAST_USED_THROTTLE:
            self._repo.touch_last_used(record, now)

    @staticmethod
    def _generate() -> str:
        return KEY_PREFIX + secrets.token_urlsafe(32)

    @staticmethod
    def _hash(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()
