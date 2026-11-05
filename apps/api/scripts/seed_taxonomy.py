"""Idempotent seed of the canonical category taxonomy and its PVOG source mappings.

Run from `apps/api`:
  python -m scripts.seed_taxonomy
"""

from __future__ import annotations

from collections.abc import Iterable

from app.db import SessionLocal
from app.models.taxonomy import Category, CategoryExternalMapping
from sqlalchemy.orm import Session

from scripts.seed_data.taxonomy import (
    CATEGORY_INVENTORY,
    PVOG_LEAF_MAPPINGS,
    PVOG_SOURCE_VERSION,
    category_mapping_id,
    term_id,
)


def _upsert_canonical_categories(session: Session) -> None:
    """Upsert the frozen category rows before their source mappings."""
    ids = {category.code: term_id(category.code) for category in CATEGORY_INVENTORY}
    for category in CATEGORY_INVENTORY:
        session.merge(
            Category(
                id=ids[category.code],
                parent_id=None if category.parent_code is None else ids[category.parent_code],
                code=category.code,
                name_i18n=category.name_i18n,
                description_i18n=category.description_i18n,
                icon=category.icon,
                sort_order=category.sort_order,
                is_active=category.is_active,
            )
        )
    session.flush()


def _mapping_row(
    *,
    category_code: str,
    external_level: str,
    external_code: str,
    source_version: str,
    confidence: float,
    state: str,
    reason: str | None,
) -> CategoryExternalMapping:
    return CategoryExternalMapping(
        id=category_mapping_id(category_code, external_level, external_code, source_version),
        category_id=term_id(category_code),
        source="pvog",
        external_level=external_level,
        external_code=external_code,
        source_version=source_version,
        mapping_confidence=confidence,
        mapping_state=state,
        reason=reason,
    )


def _parent_mapping_rows() -> Iterable[CategoryExternalMapping]:
    return (
        _mapping_row(
            category_code=category.code,
            external_level="parent",
            external_code=source_code,
            source_version=PVOG_SOURCE_VERSION,
            confidence=1.0,
            state="mapped",
            reason=None,
        )
        for category in CATEGORY_INVENTORY
        for source_code in category.source_parent_codes
    )


def _leaf_mapping_rows() -> Iterable[CategoryExternalMapping]:
    return (
        _mapping_row(
            category_code=category_code,
            external_level="leaf",
            external_code=mapping.leaf_code,
            source_version=PVOG_SOURCE_VERSION,
            confidence=mapping.confidence,
            state=mapping.state,
            reason=mapping.reason,
        )
        for mapping in PVOG_LEAF_MAPPINGS
        for category_code in mapping.category_codes
    )


def _canonical_source_mappings() -> list[CategoryExternalMapping]:
    """Build deterministic source mappings from the frozen category contract."""
    return [*_parent_mapping_rows(), *_leaf_mapping_rows()]


def seed_canonical_taxonomy(session: Session) -> None:
    """Upsert canonical categories and their versioned PVOG source mappings."""
    _upsert_canonical_categories(session)
    for mapping in _canonical_source_mappings():
        session.merge(mapping)
    session.flush()


def main() -> None:
    """Seed the canonical taxonomy in one transaction and print the row counts."""
    with SessionLocal() as session:
        seed_canonical_taxonomy(session)
        session.commit()
    print(f"seed_taxonomy: {len(CATEGORY_INVENTORY)} categories upserted.")


if __name__ == "__main__":
    main()
