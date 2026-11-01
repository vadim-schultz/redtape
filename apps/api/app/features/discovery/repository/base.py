"""Shared session handling for the discovery repositories."""

from __future__ import annotations

from sqlalchemy.orm import Session


class SessionRepository:
    """Hold the SQLAlchemy session and expose the unit-of-work calls services need."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to ``session``."""
        self._session = session

    @property
    def session(self) -> Session:
        """Expose the bound session to feature code that needs to run a query of its own."""
        return self._session

    def flush(self) -> None:
        """Flush pending changes to the database."""
        self._session.flush()

    def rollback(self) -> None:
        """Roll back the current transaction (called by services that own the policy)."""
        self._session.rollback()
