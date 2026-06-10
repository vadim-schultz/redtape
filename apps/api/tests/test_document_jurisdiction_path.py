from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from app.features.documents.repository import DocumentRepository
from app.features.documents.service import DocumentService
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind


def test_jurisdiction_path_is_root_to_leaf(db_session) -> None:
    session = db_session
    now = datetime.now(UTC)

    # Use deterministic UUIDs so inserts are repeatable.
    ns = uuid.uuid5(uuid.NAMESPACE_URL, "redtape.test.unit.jurisdiction_path")
    country_id = uuid.uuid5(ns, "country:DE")
    state_id = uuid.uuid5(ns, "state:14")
    district_id = uuid.uuid5(ns, "district:146")
    municipality_id = uuid.uuid5(ns, "municipality:14612")
    target_doc_id = uuid.uuid5(ns, "doc:target")
    req1_id = uuid.uuid5(ns, "doc:req1")
    req2_id = uuid.uuid5(ns, "doc:req2")

    session.execute(sa.delete(DocumentRequirement).where(DocumentRequirement.parent_document_id == target_doc_id))

    session.execute(sa.delete(Document).where(Document.id == target_doc_id))
    session.execute(sa.delete(Document).where(Document.id == req1_id))
    session.execute(sa.delete(Document).where(Document.id == req2_id))

    for jid in [country_id, state_id, district_id, municipality_id]:
        session.execute(sa.delete(Jurisdiction).where(Jurisdiction.id == jid))

    # Insert jurisdiction chain: country -> region(state) -> region(district) -> municipality(city)
    country = Jurisdiction(
        id=country_id,
        kind=JurisdictionKind.COUNTRY,
        geographic_parent_id=None,
        code="DE",
        administrative_roles=["COUNTRY"],
        name_i18n={"de": "Deutschland", "en": "Germany"},
        openplz_type="Country",
        postal_code=None,
        multiple_postal_codes=False,
        last_updated=now,
    )
    state = Jurisdiction(
        id=state_id,
        kind=JurisdictionKind.REGION,
        geographic_parent_id=country_id,
        code="14",
        administrative_roles=["REGION"],
        name_i18n={"de": "Sachsen", "en": "Saxony"},
        openplz_type="Land",
        postal_code=None,
        multiple_postal_codes=False,
        last_updated=now,
    )
    district = Jurisdiction(
        id=district_id,
        kind=JurisdictionKind.REGION,
        geographic_parent_id=state_id,
        code="146",
        administrative_roles=["DISTRICT"],
        name_i18n={"de": "Kreis Example", "en": "District Example"},
        openplz_type="Kreis",
        postal_code=None,
        multiple_postal_codes=False,
        last_updated=now,
    )
    municipality = Jurisdiction(
        id=municipality_id,
        kind=JurisdictionKind.MUNICIPALITY,
        geographic_parent_id=district_id,
        code="14612",
        administrative_roles=["MUNICIPALITY", "DISTRICT"],
        name_i18n={"de": "Musterstadt", "en": "Example City"},
        openplz_type="Stadt",
        postal_code="01001",
        multiple_postal_codes=False,
        last_updated=now,
    )

    session.add_all([country, state, district, municipality])

    # Insert document target + requirements.
    target = Document(
        id=target_doc_id,
        jurisdiction_id=municipality_id,
        slug="target-doc",
        title_i18n={"de": "Ziel-Dokument", "en": "Target Document"},
        description_i18n={"de": "Beschreibung", "en": "Description"},
        official_url=None,
    )
    req1 = Document(
        id=req1_id,
        jurisdiction_id=municipality_id,
        slug="req-1",
        title_i18n={"de": "Anforderung 1", "en": "Requirement 1"},
        description_i18n={"de": "Req 1", "en": "Req 1"},
        official_url=None,
    )
    req2 = Document(
        id=req2_id,
        jurisdiction_id=municipality_id,
        slug="req-2",
        title_i18n={"de": "Anforderung 2", "en": "Requirement 2"},
        description_i18n={"de": "Req 2", "en": "Req 2"},
        official_url=None,
    )
    session.add_all([target, req1, req2])
    session.flush()

    # NOTE: the original unittest version referenced `self.ns` (undefined). We use the local `ns`.
    edges = [
        DocumentRequirement(
            id=uuid.uuid5(ns, "edge:req1"),
            parent_document_id=target_doc_id,
            required_document_id=req1_id,
            jurisdiction_id=municipality_id,
            source="canonical",
            notes_i18n={"de": "Notiz 1", "en": "Note 1"},
        ),
        DocumentRequirement(
            id=uuid.uuid5(ns, "edge:req2"),
            parent_document_id=target_doc_id,
            required_document_id=req2_id,
            jurisdiction_id=municipality_id,
            source="canonical",
            notes_i18n=None,
        ),
    ]
    session.add_all(edges)
    session.commit()

    service = DocumentService(DocumentRepository(session))
    detail = service.get_document_detail(document_id=target_doc_id, locale="de", enabled_locales={"de", "en"})
    assert detail is not None

    # Expect full breadcrumb: country -> state -> district -> municipality
    assert len(detail.jurisdiction_path) == 4
    assert detail.jurisdiction_path[0].kind == "COUNTRY"
    assert detail.jurisdiction_path[-1].kind == "MUNICIPALITY"
