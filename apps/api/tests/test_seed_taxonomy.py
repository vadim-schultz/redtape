from __future__ import annotations

import re
from dataclasses import replace

import pytest
import sqlalchemy as sa
from app.models import Category
from scripts.seed_data.category_contract import (
    CATEGORY_INVENTORY,
    LEGACY_CROSSWALK,
    TaxonomyContractError,
    validate_category_inventory,
    validate_legacy_crosswalk,
)
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy.orm import Session

CODE_PATTERN = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"


def _count(session: Session, table: sa.Table | type) -> int:
    return session.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()


def test_every_category_has_non_empty_de_and_en_text() -> None:
    for category in CATEGORY_INVENTORY:
        for texts in (category.name_i18n, category.description_i18n):
            assert all(texts.get(locale, "").strip() for locale in ("de", "en"))


def test_category_codes_are_stable_ascii_kebab_case() -> None:
    codes = [category.code for category in CATEGORY_INVENTORY]

    assert all(re.fullmatch(CODE_PATTERN, code) for code in codes)
    assert len(set(codes)) == len(codes)


def test_seed_creates_categories_and_is_idempotent(db_session: Session) -> None:
    seed_canonical_taxonomy(db_session)
    db_session.flush()
    first_count = _count(db_session, Category)

    seed_canonical_taxonomy(db_session)
    db_session.flush()

    assert first_count == len(CATEGORY_INVENTORY)
    assert _count(db_session, Category) == first_count


def test_seed_leaves_an_existing_document_untagged(db_session: Session) -> None:
    from app.models.document import Document
    from app.models.jurisdiction import Jurisdiction, JurisdictionKind
    from app.models.taxonomy import document_category

    country = Jurisdiction(kind=JurisdictionKind.COUNTRY, geographic_parent_id=None, code="DE")
    db_session.add(country)
    db_session.flush()
    db_session.add(Document(slug="some-real-document", title_i18n={"en": "Real"}, jurisdiction_id=country.id))
    db_session.flush()

    seed_canonical_taxonomy(db_session)

    assert _count(db_session, document_category) == 0


def test_taxonomy_every_active_subcategory_has_one_active_root() -> None:
    validate_category_inventory(CATEGORY_INVENTORY)

    active = {category.code: category for category in CATEGORY_INVENTORY if category.is_active}
    for category in active.values():
        if category.parent_code is None:
            continue
        assert active[category.parent_code].parent_code is None


def test_taxonomy_duplicate_or_cyclic_category_inventory_is_rejected() -> None:
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


def test_frozen_crosswalk_has_a_disposition_for_each_legacy_source() -> None:
    """Keep the retired mapping artifact valid even though runtime taxonomy is category-only."""
    validate_legacy_crosswalk(LEGACY_CROSSWALK, CATEGORY_INVENTORY)
