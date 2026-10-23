"""Plain-value snapshots of the rows the OpenPLZ import reconciles.

The import compares every OpenPLZ record with what the database already holds.
Holding that state as frozen dataclasses (not ORM entities) keeps the preloaded
maps valid across the importer's periodic ``commit()``, which would expire ORM
instances and turn every later attribute read into a fresh SELECT.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locality import Locality
from sqlalchemy import select
from sqlalchemy.orm import Session

JurisdictionKey = tuple[JurisdictionKind, str]


@dataclass(frozen=True)
class JurisdictionRow:
    """Every jurisdiction field the import owns; equality is the "changed?" test."""

    id: uuid.UUID
    kind: JurisdictionKind
    geographic_parent_id: uuid.UUID | None
    code: str
    openplz_type: str | None
    postal_code: str | None
    multiple_postal_codes: bool
    administrative_roles: list[str]
    name_i18n: dict[str, str]

    @property
    def key(self) -> JurisdictionKey:
        """The DB uniqueness key (`uq_jurisdiction_kind_code`)."""
        return (self.kind, self.code)


@dataclass(frozen=True)
class LocalityRow:
    """The locality fields that can change for a fixed deterministic id."""

    id: uuid.UUID
    municipality_id: uuid.UUID
    name_i18n: dict[str, str]


_JURISDICTION_COLUMNS = (
    Jurisdiction.id,
    Jurisdiction.kind,
    Jurisdiction.geographic_parent_id,
    Jurisdiction.code,
    Jurisdiction.openplz_type,
    Jurisdiction.postal_code,
    Jurisdiction.multiple_postal_codes,
    Jurisdiction.administrative_roles,
    Jurisdiction.name_i18n,
)
_LOCALITY_COLUMNS = (Locality.id, Locality.municipality_id, Locality.name_i18n)


@dataclass
class KnownRows:
    """Existing rows keyed the way the importer looks them up.

    A `complete` map came from `load()`, so a missing key means the row does not
    exist. An incomplete (empty) map falls back to one SELECT per lookup, which is
    what callers get when they upsert a single row without preloading.
    """

    jurisdictions: dict[JurisdictionKey, JurisdictionRow] = field(default_factory=dict)
    localities: dict[uuid.UUID, LocalityRow] = field(default_factory=dict)
    complete: bool = False

    @classmethod
    def load(cls, session: Session) -> KnownRows:
        """Read every jurisdiction and locality with one query each."""
        jurisdictions = [JurisdictionRow(**row._mapping) for row in session.execute(select(*_JURISDICTION_COLUMNS))]
        localities = [LocalityRow(**row._mapping) for row in session.execute(select(*_LOCALITY_COLUMNS))]
        return cls(
            jurisdictions={row.key: row for row in jurisdictions if row.code is not None},
            localities={row.id: row for row in localities},
            complete=True,
        )

    def jurisdiction(self, session: Session, kind: JurisdictionKind, code: str) -> JurisdictionRow | None:
        """Return the existing jurisdiction for `(kind, code)`, or None."""
        row = self.jurisdictions.get((kind, code))
        if row is None and not self.complete:
            row = find_jurisdiction(session, kind, code)
        return row

    def locality(self, session: Session, locality_id: uuid.UUID) -> LocalityRow | None:
        """Return the existing locality with this deterministic id, or None."""
        row = self.localities.get(locality_id)
        if row is None and not self.complete:
            row = find_locality(session, locality_id)
        return row


def find_jurisdiction(session: Session, kind: JurisdictionKind, code: str) -> JurisdictionRow | None:
    """Fetch one jurisdiction by `(kind, code)` when no preloaded map is available."""
    stmt = select(*_JURISDICTION_COLUMNS).where(Jurisdiction.kind == kind, Jurisdiction.code == code)
    row = session.execute(stmt).one_or_none()
    return None if row is None else JurisdictionRow(**row._mapping)


def find_locality(session: Session, locality_id: uuid.UUID) -> LocalityRow | None:
    """Fetch one locality by id when no preloaded map is available."""
    row = session.execute(select(*_LOCALITY_COLUMNS).where(Locality.id == locality_id)).one_or_none()
    return None if row is None else LocalityRow(**row._mapping)
