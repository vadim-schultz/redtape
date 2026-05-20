from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locality import Locality


class LocationsRepository:
    """DB persistence for OpenPLZ-backed jurisdiction hierarchy reads."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_jurisdiction_by_kind_and_code(
        self, *, kind: JurisdictionKind, code: str
    ) -> Jurisdiction | None:
        stmt = select(Jurisdiction).where(Jurisdiction.kind == kind, Jurisdiction.code == code)
        return self._session.scalar(stmt)

    def list_by_parent_and_kind(
        self,
        *,
        parent_id: UUID,
        kind: JurisdictionKind,
        administrative_role: str | None = None,
    ) -> list[Jurisdiction]:
        stmt = select(Jurisdiction).where(
            Jurisdiction.geographic_parent_id == parent_id,
            Jurisdiction.kind == kind,
        )
        if administrative_role is not None:
            stmt = stmt.where(Jurisdiction.administrative_roles.any(administrative_role))
        stmt = stmt.order_by(Jurisdiction.code.asc())
        return list(self._session.scalars(stmt).all())

    def list_countries(self) -> list[Jurisdiction]:
        stmt = (
            select(Jurisdiction)
            .where(Jurisdiction.kind == JurisdictionKind.COUNTRY)
            .order_by(Jurisdiction.code.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_localities_for_city(self, *, municipality_id: UUID) -> list[Locality]:
        stmt = (
            select(Locality)
            .where(Locality.municipality_id == municipality_id)
            .order_by(Locality.postal_code.asc(), Locality.name.asc())
        )
        return list(self._session.scalars(stmt).all())

