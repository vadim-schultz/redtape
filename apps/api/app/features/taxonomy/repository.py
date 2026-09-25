from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.taxonomy import Domain, LifeSituation

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
