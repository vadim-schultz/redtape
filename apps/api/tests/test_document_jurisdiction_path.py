from __future__ import annotations

from datetime import datetime, timezone
import uuid
import unittest

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.features.documents.repository import DocumentRepository
from app.features.documents.service import DocumentService
from app.models import Base
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind


class TestDocumentJurisdictionPath(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.engine = create_engine(settings.database_url)
            # Ensure schema exists for our new tables/columns.
            Base.metadata.create_all(self.engine)
        except Exception as e:  # pragma: no cover
            self.skipTest(f"Database unavailable for tests: {e}")

        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        self.session: Session = self.SessionLocal()

        # Use deterministic UUIDs so inserts are repeatable.
        ns = uuid.uuid5(uuid.NAMESPACE_URL, "redtape.test.unit.jurisdiction_path")
        self.country_id = uuid.uuid5(ns, "country:DE")
        self.state_id = uuid.uuid5(ns, "state:14")
        self.district_id = uuid.uuid5(ns, "district:146")
        self.municipality_id = uuid.uuid5(ns, "municipality:14612")

        self.target_doc_id = uuid.uuid5(ns, "doc:target")
        self.req1_id = uuid.uuid5(ns, "doc:req1")
        self.req2_id = uuid.uuid5(ns, "doc:req2")

    def tearDown(self) -> None:
        try:
            self.session.close()
        except Exception:
            pass

    def test_jurisdiction_path_is_root_to_leaf(self) -> None:
        now = datetime.now(timezone.utc)

        self.session.execute(
            sa.delete(DocumentRequirement).where(
                DocumentRequirement.parent_document_id == self.target_doc_id
            )
        )

        self.session.execute(sa.delete(Document).where(Document.id == self.target_doc_id))
        self.session.execute(sa.delete(Document).where(Document.id == self.req1_id))
        self.session.execute(sa.delete(Document).where(Document.id == self.req2_id))

        for jid in [self.country_id, self.state_id, self.district_id, self.municipality_id]:
            self.session.execute(sa.delete(Jurisdiction).where(Jurisdiction.id == jid))

        # Insert jurisdiction chain: country -> region(state) -> region(district) -> municipality(city)
        country = Jurisdiction(
            id=self.country_id,
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
            id=self.state_id,
            kind=JurisdictionKind.REGION,
            geographic_parent_id=self.country_id,
            code="14",
            administrative_roles=["REGION"],
            name_i18n={"de": "Sachsen", "en": "Saxony"},
            openplz_type="Land",
            postal_code=None,
            multiple_postal_codes=False,
            last_updated=now,
        )
        district = Jurisdiction(
            id=self.district_id,
            kind=JurisdictionKind.REGION,
            geographic_parent_id=self.state_id,
            code="146",
            administrative_roles=["DISTRICT"],
            name_i18n={"de": "Kreis Example", "en": "District Example"},
            openplz_type="Kreis",
            postal_code=None,
            multiple_postal_codes=False,
            last_updated=now,
        )
        municipality = Jurisdiction(
            id=self.municipality_id,
            kind=JurisdictionKind.MUNICIPALITY,
            geographic_parent_id=self.district_id,
            code="14612",
            administrative_roles=["MUNICIPALITY", "DISTRICT"],
            name_i18n={"de": "Musterstadt", "en": "Example City"},
            openplz_type="Stadt",
            postal_code="01001",
            multiple_postal_codes=False,
            last_updated=now,
        )

        self.session.add_all([country, state, district, municipality])

        # Insert document target + requirements.
        target = Document(
            id=self.target_doc_id,
            jurisdiction_id=self.municipality_id,
            slug="target-doc",
            title_i18n={"de": "Ziel-Dokument", "en": "Target Document"},
            description_i18n={"de": "Beschreibung", "en": "Description"},
            official_url=None,
        )
        req1 = Document(
            id=self.req1_id,
            jurisdiction_id=self.municipality_id,
            slug="req-1",
            title_i18n={"de": "Anforderung 1", "en": "Requirement 1"},
            description_i18n={"de": "Req 1", "en": "Req 1"},
            official_url=None,
        )
        req2 = Document(
            id=self.req2_id,
            jurisdiction_id=self.municipality_id,
            slug="req-2",
            title_i18n={"de": "Anforderung 2", "en": "Requirement 2"},
            description_i18n={"de": "Req 2", "en": "Req 2"},
            official_url=None,
        )
        self.session.add_all([target, req1, req2])
        self.session.flush()

        edges = [
            DocumentRequirement(
                id=uuid.uuid5(ns, "edge:req1"),
                parent_document_id=self.target_doc_id,
                required_document_id=self.req1_id,
                jurisdiction_id=self.municipality_id,
                source="canonical",
                notes_i18n={"de": "Notiz 1", "en": "Note 1"},
            ),
            DocumentRequirement(
                id=uuid.uuid5(ns, "edge:req2"),
                parent_document_id=self.target_doc_id,
                required_document_id=self.req2_id,
                jurisdiction_id=self.municipality_id,
                source="canonical",
                notes_i18n=None,
            ),
        ]
        self.session.add_all(edges)

        # Flush but don't commit to keep transaction isolated.
        self.session.commit()

        service = DocumentService(DocumentRepository(self.session))
        detail = service.get_document_detail(
            document_id=self.target_doc_id, locale="de", enabled_locales={"de", "en"}
        )
        assert detail is not None

        # Expect full breadcrumb: country -> state -> district -> municipality
        self.assertEqual(len(detail.jurisdiction_path), 4)
        self.assertEqual(detail.jurisdiction_path[0].kind, "COUNTRY")
        self.assertEqual(detail.jurisdiction_path[-1].kind, "MUNICIPALITY")


if __name__ == "__main__":
    unittest.main()

