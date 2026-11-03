from __future__ import annotations

import uuid

from scripts.openplz_ids import (
    UUID_NAMESPACE,
    country_id,
    locality_id,
    municipality_id,
    region_id,
    stable_uuid,
)

# Golden values, computed from the formulas on `main` before this chapter
# touched them. If these ever need to change, every persisted jurisdiction and
# locality id changes with them.
EXPECTED_NAMESPACE = uuid.UUID("1221acf1-efe2-5dbc-8e6f-729112b021e5")
EXPECTED_COUNTRY_DE = uuid.UUID("e0273f59-194b-56b6-9a18-e2a7e1632413")
EXPECTED_REGION_14 = uuid.UUID("ddac3643-9ecf-5a51-b273-d881bff977dd")
EXPECTED_MUNICIPALITY_14612000 = uuid.UUID("4620006e-4e41-5403-aa9d-268e59dd916d")
EXPECTED_LOCALITY_DRESDEN = uuid.UUID("d9982633-c853-5a00-8f93-ecc5ed7309d2")


def test_namespace_is_pinned() -> None:
    assert UUID_NAMESPACE == EXPECTED_NAMESPACE


def test_country_id_golden_value() -> None:
    assert country_id("DE") == EXPECTED_COUNTRY_DE


def test_region_id_golden_value() -> None:
    assert region_id("14") == EXPECTED_REGION_14


def test_municipality_id_golden_value() -> None:
    assert municipality_id("14612000") == EXPECTED_MUNICIPALITY_14612000


def test_locality_id_golden_value() -> None:
    assert locality_id("14612000", "01067", "Dresden") == EXPECTED_LOCALITY_DRESDEN


def test_ids_are_deterministic_across_calls() -> None:
    assert municipality_id("14612000") == municipality_id("14612000")
    assert locality_id("14612000", "01067", "Dresden") == locality_id("14612000", "01067", "Dresden")


def test_state_and_district_share_the_region_namespace() -> None:
    # States and districts are both stored as kind=REGION, keyed by their
    # OpenPLZ code -- region_id() is the single function for both.
    assert region_id("14") == stable_uuid("jurisdiction:REGION:14")
    assert region_id("14612") == stable_uuid("jurisdiction:REGION:14612")


def test_different_keys_give_different_ids() -> None:
    assert country_id("DE") != region_id("DE")
    assert region_id("14") != municipality_id("14")
    assert locality_id("14612000", "01067", "Dresden") != locality_id("14612000", "01067", "Loschwitz")
