"""Persistence for suggestions."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.api_key import ApiKey
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.models.user import AppUser


def _apply(
    stmt: Select,
    *,
    status: Sequence[SuggestionStatus],
    kind: SuggestionKind | None,
    source_type: SuggestionSource | None,
    jurisdiction_id: UUID | None,
) -> Select:
    """Narrow `stmt` by each non-empty filter; a list of `(values, column)` pairs, not an if-chain."""
    for values, column in (
        (status, Suggestion.status),
        ((kind,) if kind else (), Suggestion.kind),
        ((source_type,) if source_type else (), Suggestion.source_type),
        ((jurisdiction_id,) if jurisdiction_id else (), Suggestion.jurisdiction_id),
    ):
        if values:
            stmt = stmt.where(column.in_(values))
    return stmt


class SuggestionRepository:
    """Persistence for suggestions; the session only."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, suggestion: Suggestion) -> Suggestion:
        self._session.add(suggestion)
        self._session.flush()
        return suggestion

    def get(self, suggestion_id: UUID) -> Suggestion | None:
        return self._session.get(Suggestion, suggestion_id)

    def save(self, suggestion: Suggestion) -> Suggestion:
        self._session.flush()
        return suggestion

    def count(
        self,
        *,
        status: Sequence[SuggestionStatus] = (),
        kind: SuggestionKind | None = None,
        source_type: SuggestionSource | None = None,
        jurisdiction_id: UUID | None = None,
    ) -> int:
        stmt = _apply(
            select(func.count()).select_from(Suggestion),
            status=status,
            kind=kind,
            source_type=source_type,
            jurisdiction_id=jurisdiction_id,
        )
        return int(self._session.scalar(stmt) or 0)

    def list_page(
        self,
        *,
        offset: int,
        limit: int,
        status: Sequence[SuggestionStatus] = (),
        kind: SuggestionKind | None = None,
        source_type: SuggestionSource | None = None,
        jurisdiction_id: UUID | None = None,
    ) -> list[tuple[Suggestion, str | None]]:
        stmt = _apply(
            self._with_submitter(), status=status, kind=kind, source_type=source_type, jurisdiction_id=jurisdiction_id
        )
        stmt = stmt.order_by(Suggestion.created_at.desc(), Suggestion.id.desc()).offset(offset).limit(limit)
        return list(self._session.execute(stmt).tuples().all())

    def get_with_submitter(self, suggestion_id: UUID) -> tuple[Suggestion, str | None] | None:
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
        stmt = select(Suggestion).where(
            Suggestion.submitted_by_api_key_id == api_key_id,
            Suggestion.idempotency_key == idempotency_key,
        )
        return self._session.scalar(stmt)

    def rollback(self) -> None:
        """Discard a failed insert so the session is usable again (D8 race path)."""
        self._session.rollback()
