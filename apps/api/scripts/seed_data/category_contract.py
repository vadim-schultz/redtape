"""Load and validate the versioned category taxonomy contract."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from pydantic import TypeAdapter
from scripts.seed_data.category_types import (
    CategoryDefinition,
    LegacyAxis,
    LegacyMapping,
    TaxonomyContractError,
    _ContractPayload,
)

CODE_PATTERN = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"
_CODE_RE = re.compile(CODE_PATTERN)
_ARTIFACT_PATH = (
    Path(__file__).resolve().parents[4] / ".plans" / "category-taxonomy-migration" / "category-contract-v1.json"
)


def _load_contract() -> tuple[str, str, tuple[CategoryDefinition, ...], tuple[LegacyMapping, ...]]:
    """Load the checked-in contract artifact."""
    payload = TypeAdapter(_ContractPayload).validate_json(_ARTIFACT_PATH.read_bytes())
    categories = tuple(
        CategoryDefinition(
            code=category.code,
            parent_code=category.parent_code,
            name_i18n=dict(category.name_i18n),
            description_i18n=dict(category.description_i18n),
            icon=category.icon,
            sort_order=category.sort_order,
            is_active=category.is_active,
            source_parent_codes=category.source_parent_codes,
        )
        for category in payload.categories
    )
    mappings = tuple(
        LegacyMapping(
            axis=mapping.axis,
            source_code=mapping.source_code,
            state=mapping.state,
            target_codes=mapping.target_codes,
            reason=mapping.reason,
            score_combination=mapping.score_combination,
        )
        for mapping in payload.legacy_crosswalk
    )
    return payload.artifact_version, payload.pvog_source_version, categories, mappings


(
    CATEGORY_CONTRACT_VERSION,
    PVOG_SOURCE_VERSION,
    CATEGORY_INVENTORY,
    LEGACY_CROSSWALK,
) = _load_contract()


def validate_category_inventory(categories: Sequence[CategoryDefinition]) -> None:
    """Reject duplicate, orphaned, cyclic, inactive-parent, or incomplete categories."""
    if not categories:
        raise TaxonomyContractError("category inventory is empty")
    by_code = {category.code: category for category in categories}
    if len(by_code) != len(categories):
        raise TaxonomyContractError("duplicate category code")

    for category in categories:
        if not _CODE_RE.fullmatch(category.code):
            raise TaxonomyContractError(f"invalid category code: {category.code}")
        if not all(category.name_i18n.get(locale, "").strip() for locale in ("de", "en")):
            raise TaxonomyContractError(f"category {category.code} has incomplete localized name")
        if not all(category.description_i18n.get(locale, "").strip() for locale in ("de", "en")):
            raise TaxonomyContractError(f"category {category.code} has incomplete localized description")
        if category.parent_code is not None:
            parent = by_code.get(category.parent_code)
            if parent is None:
                raise TaxonomyContractError(f"category {category.code} has unknown parent")
            if not parent.is_active and category.is_active:
                raise TaxonomyContractError(f"active category {category.code} has inactive parent")

    order_keys = [(category.parent_code, category.sort_order) for category in categories]
    if len(set(order_keys)) != len(order_keys):
        raise TaxonomyContractError("duplicate category ordering")

    state: dict[str, int] = {}

    def visit(code: str) -> None:
        """Visit one parent chain and reject a cycle."""
        if state.get(code) == 1:
            raise TaxonomyContractError("category cycle detected")
        if state.get(code) == 2:
            return
        state[code] = 1
        parent_code = by_code[code].parent_code
        if parent_code is not None:
            visit(parent_code)
        state[code] = 2

    for code in by_code:
        visit(code)
    for category in categories:
        if category.parent_code is not None and by_code[category.parent_code].parent_code is not None:
            raise TaxonomyContractError(f"category {category.code} has a non-root parent")


def validate_legacy_crosswalk(
    mappings: Sequence[LegacyMapping],
    categories: Sequence[CategoryDefinition],
    expected_sources: set[tuple[LegacyAxis, str]] | None = None,
) -> None:
    """Reject unknown targets, duplicate sources, and missing legacy dispositions."""
    active_codes = {category.code for category in categories if category.is_active}
    seen: set[tuple[LegacyAxis, str]] = set()
    for mapping in mappings:
        key = (mapping.axis, mapping.source_code)
        if mapping.state == "mapped" and any(target not in active_codes for target in mapping.target_codes):
            raise TaxonomyContractError(f"unknown target in mapping for {mapping.source_code}")
        if key in seen:
            raise TaxonomyContractError(f"conflicting duplicate mapping for {mapping.axis}:{mapping.source_code}")
        seen.add(key)
        if mapping.state == "mapped" and not mapping.target_codes:
            raise TaxonomyContractError(f"mapped mapping has no target for {mapping.source_code}")
        if mapping.state != "mapped" and mapping.target_codes:
            raise TaxonomyContractError(f"non-mapped disposition has targets for {mapping.source_code}")
        if not mapping.reason.strip():
            raise TaxonomyContractError(f"mapping has no reason for {mapping.source_code}")

    if expected_sources is not None and seen != expected_sources:
        missing = expected_sources - seen
        extra = seen - expected_sources
        raise TaxonomyContractError(f"crosswalk coverage mismatch: missing={missing}, extra={extra}")


validate_category_inventory(CATEGORY_INVENTORY)
