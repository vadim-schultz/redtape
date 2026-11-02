"""One-time repair for a leaked pytest fixture that displaced Saxony's real data.

Pytest fixtures shaped like `country:DE`/`state:SN`/`district:SN-146` leaked into
production (see 20260928d_fix_jurisdiction_kind_code_dupes.py's docstring) and,
combined with seed_documents.py (now seed_jurisdictions.py) flattening its own Dresden row directly under the
region, ended up as the surviving rows once that migration deduped on (kind, code)
by oldest `last_updated` -- picking the stale leaked/seeded rows over the actively
reimported real ones and deleting Saxony's real district/municipality subtree.

Re-imports Saxony from OpenPLZ and repoints anything that referenced the fake
Dresden row onto the real one. Idempotent: no-ops once the fake row is gone, so
it's safe to run on every boot (see scripts/start.sh).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from app.db import SessionLocal
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locality import Locality
from app.models.suggestion import Suggestion
from sqlalchemy import select
from sqlalchemy.orm import Session

from scripts.import_openplz_locations import import_locations

FAKE_DRESDEN_ID = uuid.UUID("11111111-1111-1111-1111-111111111103")
LEAKED_DISTRICT_ID = uuid.UUID("c3d315b5-83da-5412-9119-4d9680d87fdb")
LEAKED_MUNICIPALITY_ID = uuid.UUID("732ab821-227b-5e04-a94e-329b1849a9a9")
SAXONY_STATE_CODE = "14"
DRESDEN_MUNICIPALITY_CODE = "14612000"

# Every table with a FK that could point at a leaked jurisdiction row.
_JURISDICTION_REFERENCES = (
    (Document, Document.jurisdiction_id),
    (DocumentRequirement, DocumentRequirement.jurisdiction_id),
    (Suggestion, Suggestion.jurisdiction_id),
    (Locality, Locality.municipality_id),
)


def _default_reimport() -> None:
    import_locations("de", state_codes={SAXONY_STATE_CODE})


def _needs_repair(session: Session) -> bool:
    fake_dresden = session.get(Jurisdiction, FAKE_DRESDEN_ID)
    found_code = fake_dresden.code if fake_dresden else None
    print(f"fix_saxony_jurisdiction_leak: fake Dresden lookup -> found={fake_dresden is not None} code={found_code!r}")
    return fake_dresden is not None and found_code == DRESDEN_MUNICIPALITY_CODE


def _exempt_fake_dresden_from_unique_index(session: Session) -> None:
    # uq_jurisdiction_kind_code only applies WHERE code IS NOT NULL, so this lets
    # the reimport recreate the real (kind, code) row without colliding.
    session.execute(Jurisdiction.__table__.update().where(Jurisdiction.id == FAKE_DRESDEN_ID).values(code=None))
    session.commit()


def _restore_fake_dresden_code(session: Session) -> None:
    session.execute(
        Jurisdiction.__table__.update().where(Jurisdiction.id == FAKE_DRESDEN_ID).values(code=DRESDEN_MUNICIPALITY_CODE)
    )
    session.commit()


def _real_dresden_id(session: Session) -> uuid.UUID:
    return session.execute(
        select(Jurisdiction.id).where(
            Jurisdiction.kind == JurisdictionKind.MUNICIPALITY,
            Jurisdiction.code == DRESDEN_MUNICIPALITY_CODE,
        )
    ).scalar_one()


def _repoint_fake_dresden_references(session: Session, real_dresden_id: uuid.UUID) -> None:
    for model, column in _JURISDICTION_REFERENCES:
        session.execute(model.__table__.update().where(column == FAKE_DRESDEN_ID).values({column.key: real_dresden_id}))


def _delete_rows_referencing(session: Session, jurisdiction_id: uuid.UUID) -> None:
    # LEAKED_DISTRICT_ID/LEAKED_MUNICIPALITY_ID are wholly fake rows (unlike
    # FAKE_DRESDEN_ID, which stands in for a real place), so anything
    # referencing them is leaked garbage too -- delete it, don't repoint it.
    for model, column in _JURISDICTION_REFERENCES:
        session.execute(model.__table__.delete().where(column == jurisdiction_id))


def _delete_leaked_jurisdictions(session: Session) -> None:
    session.execute(Jurisdiction.__table__.delete().where(Jurisdiction.id == FAKE_DRESDEN_ID))
    for leaked_id in (LEAKED_MUNICIPALITY_ID, LEAKED_DISTRICT_ID):
        _delete_rows_referencing(session, leaked_id)
        session.execute(Jurisdiction.__table__.delete().where(Jurisdiction.id == leaked_id))


def repair_saxony_jurisdictions(session: Session, *, reimport: Callable[[], None] = _default_reimport) -> bool:
    if not _needs_repair(session):
        return False

    _exempt_fake_dresden_from_unique_index(session)
    try:
        reimport()
    except Exception as exc:
        _restore_fake_dresden_code(session)
        print(f"fix_saxony_jurisdiction_leak: reimport failed ({exc!r}); reverted, will retry next boot")
        raise

    real_dresden_id = _real_dresden_id(session)
    _repoint_fake_dresden_references(session, real_dresden_id)
    _delete_leaked_jurisdictions(session)
    session.commit()
    print(f"fix_saxony_jurisdiction_leak: repaired, real Dresden id={real_dresden_id}")
    return True


def main() -> None:
    with SessionLocal() as session:
        repaired = repair_saxony_jurisdictions(session)
    print(f"fix_saxony_jurisdiction_leak: {'repaired' if repaired else 'no-op, nothing to repair'}")


if __name__ == "__main__":
    main()
