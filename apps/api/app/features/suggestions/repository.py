"""Persistence for suggestions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.features.suggestions.filters import SuggestionFilters
from app.models.api_key import ApiKey
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionStatus
from app.models.user import AppUser


def _apply(stmt: Select, filters: SuggestionFilters) -> Select:
    """Narrow `stmt` by each filter that is set; an unset axis adds no condition."""
    if filters.status:
        stmt = stmt.where(Suggestion.status.in_(filters.status))
    if filters.kind is not None:
        stmt = stmt.where(Suggestion.kind == filters.kind)
    if filters.source_type is not None:
        stmt = stmt.where(Suggestion.source_type == filters.source_type)
    if filters.jurisdiction_id is not None:
        stmt = stmt.where(Suggestion.jurisdiction_id == filters.jurisdiction_id)
    return stmt


class SuggestionRepository:
    """Persistence for suggestions; the session only."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to the request session; committing stays with the request."""
        self._session = session

    def add(self, suggestion: Suggestion) -> Suggestion:
        """Stage a new suggestion and flush so its generated columns are populated."""
        self._session.add(suggestion)
        self._session.flush()
        return suggestion

    def get(self, suggestion_id: UUID) -> Suggestion | None:
        """Return the suggestion with this id, or None."""
        return self._session.get(Suggestion, suggestion_id)

    def get_for_update(self, suggestion_id: UUID) -> Suggestion | None:
        """
        Read and lock the row for the caller's transaction.

        The caller must already be inside a transaction. Refreshes an already-loaded instance
        held in the session's identity map, so a status changed by another transaction since it
        was first loaded is not missed.
        """
        stmt = (
            select(Suggestion)
            .where(Suggestion.id == suggestion_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self._session.scalar(stmt)

    def save(self, suggestion: Suggestion) -> Suggestion:
        """Flush changes made to a suggestion that is already in the session."""
        self._session.flush()
        return suggestion

    def count(self, filters: SuggestionFilters) -> int:
        """Count the suggestions matching `filters`."""
        stmt = _apply(select(func.count()).select_from(Suggestion), filters)
        return int(self._session.scalar(stmt) or 0)

    def list_page(self, filters: SuggestionFilters, *, offset: int, limit: int) -> list[tuple[Suggestion, str | None]]:
        """One page of suggestions matching `filters`, newest first, each with its submitter's display name."""
        stmt = _apply(self._with_submitter(), filters)
        stmt = stmt.order_by(Suggestion.created_at.desc(), Suggestion.id.desc()).offset(offset).limit(limit)
        return list(self._session.execute(stmt).tuples().all())

    def get_with_submitter(self, suggestion_id: UUID) -> tuple[Suggestion, str | None] | None:
        """Return one suggestion with its submitter's display name, or None."""
        stmt = self._with_submitter().where(Suggestion.id == suggestion_id)
        row = self._session.execute(stmt).tuples().first()
        return row if row is None else (row[0], row[1])

    def _with_submitter(self) -> Select:
        """`Suggestion` joined to its submitter's display name; one query, never the email or key hash (D7)."""
        return (
            select(Suggestion, func.coalesce(AppUser.display_name, ApiKey.name))
            .outerjoin(AppUser, Suggestion.submitted_by_user_id == AppUser.id)
            .outerjoin(ApiKey, Suggestion.submitted_by_api_key_id == ApiKey.id)
        )

    def find_pending_by_url(self, *, jurisdiction_id: UUID, normalized_url: str) -> list[UUID]:
        """Ids of pending `new_document` suggestions in `jurisdiction_id` with this normalized URL."""
        stmt = select(Suggestion.id).where(
            Suggestion.jurisdiction_id == jurisdiction_id,
            Suggestion.normalized_url == normalized_url,
            Suggestion.status == SuggestionStatus.PENDING,
            Suggestion.kind == SuggestionKind.NEW_DOCUMENT,
        )
        return list(self._session.scalars(stmt).all())

    def find_pending_edge(
        self, *, jurisdiction_id: UUID, parent_document_id: UUID, required_document_id: UUID
    ) -> list[UUID]:
        """Ids of pending `new_requirement` suggestions in `jurisdiction_id` proposing this exact edge."""
        stmt = select(Suggestion.id).where(
            Suggestion.jurisdiction_id == jurisdiction_id,
            Suggestion.status == SuggestionStatus.PENDING,
            Suggestion.kind == SuggestionKind.NEW_REQUIREMENT,
            Suggestion.payload["parent_document_id"].astext == str(parent_document_id),
            Suggestion.payload["required_document_id"].astext == str(required_document_id),
        )
        return list(self._session.scalars(stmt).all())

    def get_by_idempotency_key(self, *, api_key_id: UUID, idempotency_key: str) -> Suggestion | None:
        """Return the suggestion this API key stored under the idempotency key, or None."""
        stmt = select(Suggestion).where(
            Suggestion.submitted_by_api_key_id == api_key_id,
            Suggestion.idempotency_key == idempotency_key,
        )
        return self._session.scalar(stmt)

    def rollback(self) -> None:
        """Discard a failed insert so the session is usable again (D8 race path)."""
        self._session.rollback()
