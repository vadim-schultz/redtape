"""Interpret database integrity errors raised by discovery persistence."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

_FOREIGN_KEY_PGCODE = "23503"


def is_jurisdiction_foreign_key_violation(exc: IntegrityError) -> bool:
    """Return whether ``exc`` is a failed ``catalogue_service.jurisdiction_id`` FK."""
    orig = exc.orig
    if orig is not None and getattr(orig, "pgcode", None) == _FOREIGN_KEY_PGCODE and _mentions_jurisdiction(orig):
        return True
    message = str(exc).lower()
    return "jurisdiction" in message and "foreign key" in message


def _mentions_jurisdiction(orig: BaseException) -> bool:
    diag = getattr(orig, "diag", None)
    constraint = getattr(diag, "constraint_name", None) if diag is not None else None
    if constraint is not None and "jurisdiction" in constraint.lower():
        return True
    return "jurisdiction" in str(orig).lower()
