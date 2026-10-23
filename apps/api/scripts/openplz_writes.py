"""Row writers for the OpenPLZ import: insert a new row, or update one that differs.

Updates are plain `UPDATE ... WHERE id` statements. They bypass the ORM unit of
work on purpose: a row that is already in the database is never loaded, and an
unchanged row costs no statement at all.
"""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime

from app.models.jurisdiction import Jurisdiction
from app.models.locality import Locality
from sqlalchemy import update
from sqlalchemy.orm import Session

from scripts.openplz_rows import JurisdictionRow, LocalityRow


def _naive(moment: datetime) -> datetime:
    return moment.replace(tzinfo=None)


def insert_jurisdiction(session: Session, row: JurisdictionRow, touched_at: datetime) -> JurisdictionRow:
    """Queue an INSERT for a jurisdiction that does not exist yet."""
    session.add(Jurisdiction(**asdict(row), last_updated=_naive(touched_at)))
    return row


def sync_jurisdiction(
    session: Session, existing: JurisdictionRow, wanted: JurisdictionRow, touched_at: datetime
) -> JurisdictionRow:
    """Update `existing` to match `wanted` and return the resulting row; a no-op when equal."""
    # The existing row keeps its id. Reassigning geographic_parent_id lets a
    # stale/misparented row self-heal onto the authoritative parent instead of
    # the import raising on the next INSERT attempt.
    desired = replace(wanted, id=existing.id)
    if desired == existing:
        return existing
    # Parents inserted earlier in this run may still be pending; the UPDATE must see them.
    session.flush()
    values = {
        "geographic_parent_id": desired.geographic_parent_id,
        "openplz_type": desired.openplz_type,
        "postal_code": desired.postal_code,
        "multiple_postal_codes": desired.multiple_postal_codes,
        "administrative_roles": desired.administrative_roles,
        "name_i18n": desired.name_i18n,
        "last_updated": _naive(touched_at),
    }
    stmt = update(Jurisdiction).where(Jurisdiction.id == existing.id).values(**values)
    session.execute(stmt, execution_options={"synchronize_session": False})
    return desired


def insert_locality(
    session: Session, row: LocalityRow, *, postal_code: str, name: str, touched_at: datetime
) -> LocalityRow:
    """Queue an INSERT for a locality that does not exist yet."""
    session.add(Locality(**asdict(row), postal_code=postal_code, name=name, last_updated=_naive(touched_at)))
    return row


def sync_locality(session: Session, existing: LocalityRow, wanted: LocalityRow, touched_at: datetime) -> LocalityRow:
    """Update `existing` to match `wanted`; a no-op when equal."""
    if wanted == existing:
        return existing
    # A pending municipality (inserted earlier in this run) must exist before the UPDATE.
    session.flush()
    values = {"municipality_id": wanted.municipality_id, "name_i18n": wanted.name_i18n}
    stmt = update(Locality).where(Locality.id == existing.id).values(**values, last_updated=_naive(touched_at))
    session.execute(stmt, execution_options={"synchronize_session": False})
    return wanted
