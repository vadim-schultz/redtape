from __future__ import annotations
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from app.features.locations.repository import LocationsRepository
from app.features.locations.service import LocationsService
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locality import Locality


def test_hierarchy_lists(db_session) -> None:
    session = db_session
    now = datetime.now(UTC)

    ns = uuid.uuid5(uuid.NAMESPACE_URL, "redtape.test.unit.locations")
    country_id = uuid.uuid5(ns, "country:DE")
    state_id = uuid.uuid5(ns, "state:SN")
    district_id = uuid.uuid5(ns, "district:SN-146")
    municipality_id = uuid.uuid5(ns, "muni:14612")

    # Clear fixtures.
    session.execute(sa.delete(Locality).where(Locality.municipality_id == municipality_id))
    for jid in [country_id, state_id, district_id, municipality_id]:
        session.execute(sa.delete(Jurisdiction).where(Jurisdiction.id == jid))

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
        name_i18n={"de": "Kreis Beispiel", "en": "Example District"},
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
    session.flush()

    locality = Locality(
        id=uuid.uuid5(ns, "locality:14612:01001:1"),
        municipality_id=municipality_id,
        postal_code="01001",
        name="Lokation",
        name_i18n={"de": "Lokation", "en": "Locality"},
        last_updated=now,
    )
    session.add(locality)
    session.commit()

    service = LocationsService(LocationsRepository(session))
    enabled = {"de", "en"}

    states = service.list_states(country_code="DE", locale="de", enabled_locales=enabled).items
    assert len(states) == 1
    assert states[0].code == "14"

    districts = service.list_districts(state_code="14", locale="de", enabled_locales=enabled).items
    assert len(districts) == 1
    assert districts[0].code == "146"

    cities = service.list_cities(district_code="146", locale="de", enabled_locales=enabled).items
    assert len(cities) == 1
    assert cities[0].code == "14612"

    localities = service.list_localities(municipality_code="14612", locale="de", enabled_locales=enabled).items
    assert len(localities) == 1
    assert localities[0].code == "01001"
