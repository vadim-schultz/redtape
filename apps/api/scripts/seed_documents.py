"""Idempotent seed: DE + Saxony + Dresden, 4 documents, 3 requirements (MVP graph).

Run from `apps/api`:
  python -m scripts.seed_documents
"""

from __future__ import annotations

import uuid

from app.db import SessionLocal
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from sqlalchemy import select
from sqlalchemy.orm import Session

# Stable UUIDs (re-runs merge by primary key)
ID_DE = uuid.UUID("11111111-1111-1111-1111-111111111101")
ID_SN = uuid.UUID("11111111-1111-1111-1111-111111111102")
ID_DD = uuid.UUID("11111111-1111-1111-1111-111111111103")

ID_DOC_MELDE = uuid.UUID("22222222-2222-2222-2222-222222222201")
ID_DOC_AUSWEIS = uuid.UUID("22222222-2222-2222-2222-222222222202")
ID_DOC_GEBURT = uuid.UUID("22222222-2222-2222-2222-222222222203")
ID_DOC_WOHN = uuid.UUID("22222222-2222-2222-2222-222222222204")

ID_REQ_1 = uuid.UUID("33333333-3333-3333-3333-333333333301")
ID_REQ_2 = uuid.UUID("33333333-3333-3333-3333-333333333302")
ID_REQ_3 = uuid.UUID("33333333-3333-3333-3333-333333333303")


def _find_or_create_jurisdiction(session: Session, placeholder: Jurisdiction) -> uuid.UUID:
    """Reuse a jurisdiction already at this (parent, code) instead of merging our own.

    A real location import (see import_openplz_locations.py) may already own this
    (parent, code) under a different id — Postgres's composite unique constraint
    can't catch that collision itself since `geographic_parent_id` is nullable for
    the country row, so we look it up ourselves rather than merge() by primary key
    and create a duplicate.
    """
    existing_id = session.execute(
        select(Jurisdiction.id).where(
            Jurisdiction.geographic_parent_id == placeholder.geographic_parent_id,
            Jurisdiction.code == placeholder.code,
        )
    ).scalar_one_or_none()
    if existing_id is not None:
        return existing_id

    session.merge(placeholder)
    return placeholder.id


def _upsert_jurisdictions(session: Session) -> uuid.UUID:
    de_id = _find_or_create_jurisdiction(
        session,
        Jurisdiction(
            id=ID_DE,
            kind=JurisdictionKind.COUNTRY,
            geographic_parent_id=None,
            code="DE",
            administrative_roles=["COUNTRY"],
            name_i18n={"de": "Deutschland", "en": "Germany"},
        ),
    )
    session.flush()
    sn_id = _find_or_create_jurisdiction(
        session,
        Jurisdiction(
            id=ID_SN,
            kind=JurisdictionKind.REGION,
            geographic_parent_id=de_id,
            code="14",
            administrative_roles=["REGION"],
            name_i18n={"de": "Sachsen", "en": "Saxony"},
        ),
    )
    session.flush()
    dd_id = _find_or_create_jurisdiction(
        session,
        Jurisdiction(
            id=ID_DD,
            kind=JurisdictionKind.MUNICIPALITY,
            geographic_parent_id=sn_id,
            code="14612000",
            administrative_roles=["DISTRICT", "MUNICIPALITY"],
            name_i18n={"de": "Dresden", "en": "Dresden"},
        ),
    )
    session.flush()
    return dd_id


def _upsert_documents(session: Session, jurisdiction_id: uuid.UUID) -> None:
    melde = Document(
        id=ID_DOC_MELDE,
        jurisdiction_id=jurisdiction_id,
        slug="meldebescheinigung",
        title_i18n={
            "de": "Meldebescheinigung",
            "en": "Registration certificate",
        },
        description_i18n={
            "de": "Nachweis über die Meldeadresse (Beispiel-MVP).",
            "en": "Proof of registered address (MVP sample).",
        },
        official_url=None,
    )
    ausweis = Document(
        id=ID_DOC_AUSWEIS,
        jurisdiction_id=jurisdiction_id,
        slug="personalausweis",
        title_i18n={
            "de": "Personalausweis",
            "en": "National ID card",
        },
        description_i18n={
            "de": "Gültiger Personalausweis oder Reisepass.",
            "en": "Valid national ID card or passport.",
        },
        official_url=None,
    )
    geburt = Document(
        id=ID_DOC_GEBURT,
        jurisdiction_id=jurisdiction_id,
        slug="geburtsurkunde",
        title_i18n={
            "de": "Geburtsurkunde",
            "en": "Birth certificate",
        },
        description_i18n={
            "de": "Urkunde zur Geburt (Beispiel-MVP).",
            "en": "Civil birth record (MVP sample).",
        },
        official_url=None,
    )
    wohn = Document(
        id=ID_DOC_WOHN,
        jurisdiction_id=jurisdiction_id,
        slug="wohnungsgeberbescheinigung",
        title_i18n={
            "de": "Wohnungsgeberbescheinigung",
            "en": "Landlord confirmation",
        },
        description_i18n={
            "de": "Bestätigung des Wohnungsgebers über Einzug (Beispiel-MVP).",
            "en": "Landlord confirmation of move-in (MVP sample).",
        },
        official_url=None,
    )
    for row in (melde, ausweis, geburt, wohn):
        session.merge(row)


def _upsert_requirements(session: Session, jurisdiction_id: uuid.UUID) -> None:
    reqs = [
        DocumentRequirement(
            id=ID_REQ_1,
            parent_document_id=ID_DOC_MELDE,
            required_document_id=ID_DOC_AUSWEIS,
            jurisdiction_id=jurisdiction_id,
            source="canonical",
            notes_i18n={
                "de": "Identitätsnachweis für die Meldung.",
                "en": "Identity proof for registration.",
            },
            valid_from=None,
            valid_to=None,
        ),
        DocumentRequirement(
            id=ID_REQ_2,
            parent_document_id=ID_DOC_MELDE,
            required_document_id=ID_DOC_GEBURT,
            jurisdiction_id=jurisdiction_id,
            source="canonical",
            notes_i18n={
                "de": "Nachweis der Personenstandsangaben (Beispiel).",
                "en": "Civil status evidence (sample).",
            },
            valid_from=None,
            valid_to=None,
        ),
        DocumentRequirement(
            id=ID_REQ_3,
            parent_document_id=ID_DOC_MELDE,
            required_document_id=ID_DOC_WOHN,
            jurisdiction_id=jurisdiction_id,
            source="canonical",
            notes_i18n={
                "de": "Nachweis über die Wohnung (Beispiel).",
                "en": "Proof of housing (sample).",
            },
            valid_from=None,
            valid_to=None,
        ),
    ]
    for row in reqs:
        session.merge(row)


def seed_mvp_graph(session: Session) -> None:
    dresden_id = _upsert_jurisdictions(session)
    _upsert_documents(session, dresden_id)
    _upsert_requirements(session, dresden_id)


def main() -> None:
    with SessionLocal() as session:
        seed_mvp_graph(session)
        session.commit()
    print("seed_documents: MVP graph upserted (jurisdictions + documents + requirements).")


if __name__ == "__main__":
    main()
