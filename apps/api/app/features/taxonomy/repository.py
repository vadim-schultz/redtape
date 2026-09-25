from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import cast
from uuid import UUID

from sqlalchemy import Column, Select, func, select
from sqlalchemy.orm import Session

from app.models.taxonomy import Domain, LifeSituation, document_domain, document_life_situation

TermModel = type[Domain] | type[LifeSituation]


class TaxonomyRepository:
    """Persistence for both matrix axes; the two term tables share one access path."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_terms(self, model: TermModel) -> Sequence[Domain | LifeSituation]:
        stmt = select(model).order_by(model.sort_order.asc(), model.code.asc())
        return cast("Sequence[Domain | LifeSituation]", self._session.scalars(stmt).all())

    def ids_for_codes(self, model: TermModel, codes: Iterable[str]) -> dict[str, UUID]:
        stmt = select(model.code, model.id).where(model.code.in_(set(codes)))
        return {code: term_id for code, term_id in self._session.execute(stmt).all()}

    def matrix_counts(self, document_ids: Sequence[UUID]) -> list[tuple[str, str, int]]:
        """Non-empty (domain code, situation code, distinct documents) rows in taxonomy order."""
        stmt = self._scoped(self._cell_select(), document_ids)
        return [(d, s, n) for d, s, n in self._session.execute(stmt).all()]

    def domain_counts(self, document_ids: Sequence[UUID]) -> list[tuple[str, int]]:
        return self._axis_counts(Domain, document_domain.c.domain_id, document_ids)

    def situation_counts(self, document_ids: Sequence[UUID]) -> list[tuple[str, int]]:
        return self._axis_counts(LifeSituation, document_life_situation.c.life_situation_id, document_ids)

    def _axis_counts(
        self, model: TermModel, term_column: Column, document_ids: Sequence[UUID]
    ) -> list[tuple[str, int]]:
        link = term_column.table
        stmt = (
            select(model.code, func.count(link.c.document_id.distinct()))
            .join(link, term_column == model.id)
            .group_by(model.id)
            .order_by(model.sort_order.asc(), model.code.asc())
        )
        return [(code, n) for code, n in self._session.execute(self._scoped(stmt, document_ids, link)).all()]

    def _cell_select(self) -> Select:
        dd, ls = document_domain, document_life_situation
        return (
            select(Domain.code, LifeSituation.code, func.count(dd.c.document_id.distinct()))
            .select_from(dd)
            .join(ls, ls.c.document_id == dd.c.document_id)
            .join(Domain, Domain.id == dd.c.domain_id)
            .join(LifeSituation, LifeSituation.id == ls.c.life_situation_id)
            .group_by(Domain.id, LifeSituation.id)
            .order_by(Domain.sort_order, Domain.code, LifeSituation.sort_order, LifeSituation.code)
        )

    @staticmethod
    def _scoped(stmt: Select, document_ids: Sequence[UUID], link=document_domain) -> Select:
        return stmt.where(link.c.document_id.in_(document_ids))
