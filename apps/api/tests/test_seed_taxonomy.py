from __future__ import annotations

import re
from dataclasses import replace

import pytest
import sqlalchemy as sa
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import (
    CODE_PATTERN,
    Domain,
    LifeSituation,
    LifeSituationGroup,
    document_domain,
    document_life_situation,
)
from scripts.seed_data.taxonomy import (
    CATEGORY_INVENTORY,
    DOMAINS,
    LEGACY_CROSSWALK,
    SITUATION_GROUP_CODES,
    SITUATION_GROUPS,
    SITUATIONS,
    TaxonomyContractError,
    Term,
    term_id,
    validate_category_inventory,
    validate_legacy_crosswalk,
)
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy.orm import Session

ALL_TERMS = DOMAINS + SITUATIONS
GERMAN_SLUGS = {"umzug", "wohnen", "geburt", "heirat", "fahrzeuge", "arbeit", "familie", "bildung"}


def _count(session: Session, table: sa.Table | type) -> int:
    return session.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()


def _seeded(session: Session) -> Session:
    seed_canonical_taxonomy(session)
    session.flush()
    return session


def test_data_has_13_domains_and_18_situations() -> None:
    assert (len(DOMAINS), len(SITUATIONS)) == (13, 18)


def test_data_has_8_situation_groups() -> None:
    assert len(SITUATION_GROUPS) == 8


def test_situation_group_codes_is_a_pure_partition_of_the_18_situations() -> None:
    """Architecture §4: every situation code maps to exactly one group, and every group is used."""

    situation_codes = {t.code for t in SITUATIONS}
    group_codes = {t.code for t in SITUATION_GROUPS}

    assert SITUATION_GROUP_CODES.keys() == situation_codes
    assert set(SITUATION_GROUP_CODES.values()) == group_codes


def test_situation_group_codes_matches_the_architecture_table() -> None:
    assert SITUATION_GROUP_CODES == {
        "marriage": "family-relationships",
        "separation-divorce": "family-relationships",
        "birth-of-child": "family-relationships",
        "death-of-relative": "family-relationships",
        "moving-house": "home-housing",
        "renting-home": "home-housing",
        "buying-property": "home-housing",
        "new-job": "work-career",
        "job-loss": "work-career",
        "going-self-employed": "work-career",
        "studying": "education",
        "starting-school": "education",
        "buying-vehicle": "vehicles-travel",
        "getting-licence": "vehicles-travel",
        "immigration": "residence-migration",
        "naturalisation": "residence-migration",
        "illness-care": "health-care",
        "retirement": "retirement",
    }


@pytest.mark.parametrize("term", ALL_TERMS, ids=lambda t: t.code)
def test_every_term_has_non_empty_de_and_en(term: Term) -> None:
    for texts in (term.name_i18n, term.description_i18n):
        assert all(texts.get(locale, "").strip() for locale in ("de", "en"))


def test_codes_are_ascii_kebab_case_english() -> None:
    codes = [t.code for t in ALL_TERMS]

    assert all(re.fullmatch(CODE_PATTERN, c) for c in codes)
    assert not GERMAN_SLUGS & set(codes)
    assert len(set(codes)) == len(codes)


def test_term_ids_are_stable_across_imports() -> None:
    assert all(t.id == term_id(t.code) for t in ALL_TERMS)
    assert len({t.id for t in ALL_TERMS}) == len(ALL_TERMS)


@pytest.mark.parametrize("group", SITUATION_GROUPS, ids=lambda t: t.code)
def test_every_situation_group_has_non_empty_de_and_en(group: Term) -> None:
    for texts in (group.name_i18n, group.description_i18n):
        assert all(texts.get(locale, "").strip() for locale in ("de", "en"))


def test_situation_group_codes_are_ascii_kebab_case_english() -> None:
    codes = [t.code for t in SITUATION_GROUPS]

    assert all(re.fullmatch(CODE_PATTERN, c) for c in codes)
    assert len(set(codes)) == len(codes)


def test_situation_group_term_ids_are_stable_across_imports() -> None:
    # Groups are a separate table from situations, so their codes may legitimately coincide
    # (e.g. the singleton "retirement" group over the "retirement" situation, per architecture
    # §4) without the two ever being confused: each lives in its own table with its own PK.
    assert all(t.id == term_id(t.code) for t in SITUATION_GROUPS)
    assert len({t.id for t in SITUATION_GROUPS}) == len(SITUATION_GROUPS)


def test_seed_creates_13_domains_and_18_situations(db_session: Session) -> None:
    _seeded(db_session)

    assert (_count(db_session, Domain), _count(db_session, LifeSituation)) == (13, 18)


def test_seed_creates_8_situation_groups(db_session: Session) -> None:
    _seeded(db_session)

    assert _count(db_session, LifeSituationGroup) == 8


def test_seed_assigns_every_situation_exactly_the_group_the_architecture_table_specifies(
    db_session: Session,
) -> None:
    """Seed-integrity test (chapter 2): the persisted partition matches ``SITUATION_GROUP_CODES``
    exactly, every situation has a group, and every group has at least one situation.
    """
    _seeded(db_session)

    rows = db_session.execute(
        sa.select(LifeSituation.code, LifeSituationGroup.code).join(
            LifeSituationGroup, LifeSituation.group_id == LifeSituationGroup.id
        )
    ).all()
    persisted = dict(rows)

    assert len(rows) == len(SITUATIONS)
    assert persisted == SITUATION_GROUP_CODES
    assert {group_code for _, group_code in rows} == {t.code for t in SITUATION_GROUPS}


def test_second_run_creates_no_duplicates(db_session: Session) -> None:
    _seeded(db_session)
    before = [_count(db_session, t) for t in (Domain, LifeSituation, LifeSituationGroup)]

    seed_canonical_taxonomy(db_session)
    db_session.flush()

    assert [_count(db_session, t) for t in (Domain, LifeSituation, LifeSituationGroup)] == before


def test_seed_creates_and_tags_no_document(db_session: Session) -> None:
    _seeded(db_session)

    counts = [_count(db_session, t) for t in (Document, document_domain, document_life_situation)]

    assert counts == [0, 0, 0]


def test_seed_leaves_an_existing_document_untagged(db_session: Session) -> None:
    country = Jurisdiction(kind=JurisdictionKind.COUNTRY, geographic_parent_id=None, code="DE")
    db_session.add(country)
    db_session.flush()
    db_session.add(Document(slug="some-real-document", title_i18n={"en": "Real"}, jurisdiction_id=country.id))
    db_session.flush()

    _seeded(db_session)

    assert _count(db_session, document_domain) == _count(db_session, document_life_situation) == 0


def test_taxonomy_every_active_subcategory_has_one_active_root() -> None:
    """Taxonomy · every active subcategory has one active root."""
    validate_category_inventory(CATEGORY_INVENTORY)

    active = {category.code: category for category in CATEGORY_INVENTORY if category.is_active}
    for category in active.values():
        if category.parent_code is None:
            continue
        parent = active[category.parent_code]
        assert parent.parent_code is None


def test_taxonomy_duplicate_or_cyclic_category_inventory_is_rejected() -> None:
    """Taxonomy · duplicate or cyclic category inventory is rejected."""
    root = next(category for category in CATEGORY_INVENTORY if category.parent_code is None)
    child = next(category for category in CATEGORY_INVENTORY if category.parent_code == root.code)
    duplicate = (*CATEGORY_INVENTORY, root)
    cyclic = (
        replace(root, parent_code=child.code),
        replace(child, parent_code=root.code),
        *(category for category in CATEGORY_INVENTORY if category.code not in {root.code, child.code}),
    )

    with pytest.raises(TaxonomyContractError, match="duplicate"):
        validate_category_inventory(duplicate)
    with pytest.raises(TaxonomyContractError, match="cycle"):
        validate_category_inventory(cyclic)


def test_crosswalk_every_legacy_domain_and_situation_code_has_a_disposition() -> None:
    """Crosswalk · every legacy domain and situation code has a disposition."""
    validate_legacy_crosswalk(LEGACY_CROSSWALK, CATEGORY_INVENTORY)

    expected = {("domain", term.code) for term in DOMAINS} | {("life_situation", term.code) for term in SITUATIONS}
    assert {(mapping.axis, mapping.source_code) for mapping in LEGACY_CROSSWALK} == expected


def test_crosswalk_unknown_target_or_duplicate_conflicting_mapping_is_rejected() -> None:
    """Crosswalk · unknown target or duplicate conflicting mapping is rejected."""
    mapped = next(mapping for mapping in LEGACY_CROSSWALK if mapping.state == "mapped")
    unknown_target = replace(mapped, target_codes=("not-a-category",))
    conflicting = (*LEGACY_CROSSWALK, replace(mapped, target_codes=()))

    with pytest.raises(TaxonomyContractError, match="unknown target"):
        validate_legacy_crosswalk((*LEGACY_CROSSWALK, unknown_target), CATEGORY_INVENTORY)
    with pytest.raises(TaxonomyContractError, match="conflicting duplicate"):
        validate_legacy_crosswalk(conflicting, CATEGORY_INVENTORY)
