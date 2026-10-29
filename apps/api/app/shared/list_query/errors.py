"""Collecting rejected query parameters into one framework validation error."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from litestar.exceptions import ValidationException

_Value = TypeVar("_Value")


class InvalidParam(ValueError):
    """One rejected query parameter."""

    def __init__(self, key: str, message: str) -> None:
        """Remember the offending ``key`` next to the client-facing ``message``."""
        super().__init__(message)
        self.key = key

    def as_extra(self) -> dict[str, str]:
        """Return the entry in the framework's validation ``extra`` shape."""
        return {"message": str(self), "key": self.key, "source": "query"}


def attempt(errors: list[InvalidParam], parse: Callable[..., _Value], *args: object) -> _Value | None:
    """Run ``parse``; record a rejection in ``errors`` and return ``None`` instead of raising."""
    try:
        return parse(*args)
    except InvalidParam as invalid:
        errors.append(invalid)
        return None


def raise_if_any(errors: list[InvalidParam]) -> None:
    """Raise one ``ValidationException`` that lists every recorded rejection."""
    if errors:
        raise ValidationException(detail="Invalid list query", extra=[error.as_extra() for error in errors])
