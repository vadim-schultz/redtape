"""Persistence for the taxonomy axes: term listing, code lookup and the matrix and axis counts."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import cast
from uuid import UUID

from sqlalchemy import Column, Select, func, select
from sqlalchemy.orm import Session

from app.models.taxonomy import Domain, LifeSituation, LifeSituationGroup, document_domain, document_life_situation

TermModel = type[Domain] | type[LifeSituation] | type[LifeSituationGroup]


class TaxonomyRepository:
    """Persistence for both matrix axes; the two term tables share one access path."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to the session it queries through."""
        self._session = session

    def list_terms(self, model: TermModel) -> Sequence[Domain | LifeSituation | LifeSituationGroup]:
        """List the terms of one axis model in its sort order, then by code."""
        stmt = select(model).order_by(model.sort_order.asc(), model.code.asc())
        return cast("Sequence[Domain | LifeSituation | LifeSituationGroup]", self._session.scalars(stmt).all())

    def list_situations_with_group(self) -> Sequence[tuple[LifeSituation, str]]:
        """Every situation alongside its group's ``code``, in the axis's own sort order."""
        stmt = (
            select(LifeSituation, LifeSituationGroup.code)
            .join(LifeSituationGroup, LifeSituation.group_id == LifeSituationGroup.id)
            .order_by(LifeSituation.sort_order.asc(), LifeSituation.code.asc())
        )
        return [(situation, group_code) for situation, group_code in self._session.execute(stmt).all()]

    def ids_for_codes(self, model: TermModel, codes: Iterable[str]) -> dict[str, UUID]:
        """Map known term codes to their ids; unknown codes are simply absent from the result."""
        stmt = select(model.code, model.id).where(model.code.in_(set(codes)))
        return {code: term_id for code, term_id in self._session.execute(stmt).all()}

    def matrix_counts(self, document_ids: Sequence[UUID]) -> list[tuple[str, str, int]]:
        """Non-empty (domain code, situation code, distinct documents) rows in taxonomy order."""
        stmt = self._scoped(self._cell_select(), document_ids)
        return [(d, s, n) for d, s, n in self._session.execute(stmt).all()]

    def domain_counts(self, document_ids: Sequence[UUID]) -> list[tuple[str, int]]:
        """Count the distinct in-scope documents per domain, in axis order."""
        return self._axis_counts(Domain, document_domain.c.domain_id, document_ids)

    def situation_counts(self, document_ids: Sequence[UUID]) -> list[tuple[str, int]]:
        """Count the distinct in-scope documents per life situation, in axis order."""
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
