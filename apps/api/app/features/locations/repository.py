"""Persistence for the OpenPLZ jurisdiction hierarchy and its localities."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import any_, literal, select
from sqlalchemy.orm import Session

from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locality import Locality


class LocationsRepository:
    """DB persistence for OpenPLZ-backed jurisdiction hierarchy reads."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to the session it queries through."""
        self._session = session

    def _get_jurisdiction_by_kind_and_code(self, *, kind: JurisdictionKind, code: str) -> Jurisdiction | None:
        stmt = select(Jurisdiction).where(Jurisdiction.kind == kind, Jurisdiction.code == code)
        return self._session.scalar(stmt)

    def list_by_parent_and_kind(
        self,
        *,
        parent_id: UUID,
        kind: JurisdictionKind,
        administrative_role: str | None = None,
    ) -> list[Jurisdiction]:
        """List jurisdictions of one kind under a parent, optionally those holding an administrative role, sorted by code."""
        stmt = select(Jurisdiction).where(
            Jurisdiction.geographic_parent_id == parent_id,
            Jurisdiction.kind == kind,
        )
        if administrative_role is not None:
            stmt = stmt.where(literal(administrative_role) == any_(Jurisdiction.administrative_roles))
        stmt = stmt.order_by(Jurisdiction.code.asc())
        return list(self._session.scalars(stmt).all())

    def list_countries(self) -> list[Jurisdiction]:
        """List every country jurisdiction, sorted by code."""
        stmt = (
            select(Jurisdiction).where(Jurisdiction.kind == JurisdictionKind.COUNTRY).order_by(Jurisdiction.code.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_localities_for_city(self, *, municipality_id: UUID) -> list[Locality]:
        """List the localities of a municipality, ordered by postal code and name."""
        stmt = (
            select(Locality)
            .where(Locality.municipality_id == municipality_id)
            .order_by(Locality.postal_code.asc(), Locality.name.asc())
        )
        return list(self._session.scalars(stmt).all())
