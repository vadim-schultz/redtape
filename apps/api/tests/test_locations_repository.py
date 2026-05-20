from __future__ import annotations

from datetime import datetime, timezone
import unittest
import uuid

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.features.locations.repository import LocationsRepository
from app.features.locations.service import LocationsService
from app.models import Base
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locality import Locality


class TestLocationsRepository(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.engine = create_engine(settings.database_url)
            Base.metadata.create_all(self.engine)
        except Exception as e:  # pragma: no cover
            self.skipTest(f"Database unavailable for tests: {e}")

        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        self.session: Session = self.SessionLocal()

        ns = uuid.uuid5(uuid.NAMESPACE_URL, "redtape.test.unit.locations")
        self.country_id = uuid.uuid5(ns, "country:DE")
        self.state_id = uuid.uuid5(ns, "state:SN")
        self.district_id = uuid.uuid5(ns, "district:SN-146")
        self.municipality_id = uuid.uuid5(ns, "muni:14612")
        self.ns = ns

    def tearDown(self) -> None:
        try:
            self.session.close()
        except Exception:
            pass

    def test_hierarchy_lists(self) -> None:
        now = datetime.now(timezone.utc)

        # Clear fixtures.
        self.session.execute(sa.delete(Locality).where(Locality.municipality_id == self.municipality_id))
        for jid in [self.country_id, self.state_id, self.district_id, self.municipality_id]:
            self.session.execute(sa.delete(Jurisdiction).where(Jurisdiction.id == jid))

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
            name_i18n={"de": "Kreis Beispiel", "en": "Example District"},
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
        self.session.flush()

        locality = Locality(
            id=uuid.uuid5(self.ns, "locality:14612:01001:1"),
            municipality_id=self.municipality_id,
            postal_code="01001",
            name="Lokation",
            name_i18n={"de": "Lokation", "en": "Locality"},
            last_updated=now,
        )
        self.session.add(locality)
        self.session.commit()

        service = LocationsService(LocationsRepository(self.session))
        enabled = {"de", "en"}

        states = service.list_states(country_code="DE", locale="de", enabled_locales=enabled).items
        self.assertEqual(len(states), 1)
        self.assertEqual(states[0].code, "14")

        districts = service.list_districts(state_code="14", locale="de", enabled_locales=enabled).items
        self.assertEqual(len(districts), 1)
        self.assertEqual(districts[0].code, "146")

        cities = service.list_cities(district_code="146", locale="de", enabled_locales=enabled).items
        self.assertEqual(len(cities), 1)
        self.assertEqual(cities[0].code, "14612")

        localities = service.list_localities(municipality_code="14612", locale="de", enabled_locales=enabled).items
        self.assertEqual(len(localities), 1)
        self.assertEqual(localities[0].code, "01001")


if __name__ == "__main__":
    unittest.main()

