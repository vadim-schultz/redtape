"""Validation rules for the category contract: inventory, legacy crosswalk, and PVOG leaf mappings."""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.shared.taxonomy.category_types import (
    CategoryDefinition,
    LegacyAxis,
    LegacyMapping,
    PvogLeafMapping,
    TaxonomyContractError,
)

CODE_PATTERN = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"
_CODE_RE = re.compile(CODE_PATTERN)


def validate_category_inventory(categories: Sequence[CategoryDefinition]) -> None:
    """Reject duplicate, orphaned, cyclic, inactive-parent, or incomplete categories."""
    if not categories:
        raise TaxonomyContractError("category inventory is empty")
    by_code = {category.code: category for category in categories}
    if len(by_code) != len(categories):
        raise TaxonomyContractError("duplicate category code")
    for category in categories:
        _check_category(category, by_code)
    _check_ordering(categories)
    _check_acyclic(by_code)
    _check_depth(categories, by_code)


def _check_category(category: CategoryDefinition, by_code: dict[str, CategoryDefinition]) -> None:
    """Reject an invalid code, incomplete text, or a parent that is unknown or inactive."""
    if not _CODE_RE.fullmatch(category.code):
        raise TaxonomyContractError(f"invalid category code: {category.code}")
    _check_localized_text(category)
    _check_parent(category, by_code)


def _check_localized_text(category: CategoryDefinition) -> None:
    """Reject a category without a non-blank German and English name and description."""
    if not all(category.name_i18n.get(locale, "").strip() for locale in ("de", "en")):
        raise TaxonomyContractError(f"category {category.code} has incomplete localized name")
    if not all(category.description_i18n.get(locale, "").strip() for locale in ("de", "en")):
        raise TaxonomyContractError(f"category {category.code} has incomplete localized description")


def _check_parent(category: CategoryDefinition, by_code: dict[str, CategoryDefinition]) -> None:
    """Reject a parent that is unknown, or an inactive parent of an active category."""
    if category.parent_code is None:
        return
    parent = by_code.get(category.parent_code)
    if parent is None:
        raise TaxonomyContractError(f"category {category.code} has unknown parent")
    if not parent.is_active and category.is_active:
        raise TaxonomyContractError(f"active category {category.code} has inactive parent")


def _check_ordering(categories: Sequence[CategoryDefinition]) -> None:
    """Reject two categories that share a parent and a sort order."""
    order_keys = [(category.parent_code, category.sort_order) for category in categories]
    if len(set(order_keys)) != len(order_keys):
        raise TaxonomyContractError("duplicate category ordering")


def _check_acyclic(by_code: dict[str, CategoryDefinition]) -> None:
    """Reject a parent chain that loops back on itself."""
    state: dict[str, int] = {}
    for code in by_code:
        _visit(code, by_code, state)


def _visit(code: str, by_code: dict[str, CategoryDefinition], state: dict[str, int]) -> None:
    """Walk one parent chain; state 1 marks a chain in progress and 2 a chain already checked."""
    if state.get(code) == 1:
        raise TaxonomyContractError("category cycle detected")
    if state.get(code) == 2:
        return
    state[code] = 1
    parent_code = by_code[code].parent_code
    if parent_code is not None:
        _visit(parent_code, by_code, state)
    state[code] = 2


def _check_depth(categories: Sequence[CategoryDefinition], by_code: dict[str, CategoryDefinition]) -> None:
    """Reject a category whose parent is itself a child, so the tree has exactly two levels."""
    for category in categories:
        if category.parent_code is not None and by_code[category.parent_code].parent_code is not None:
            raise TaxonomyContractError(f"category {category.code} has a non-root parent")


def validate_legacy_crosswalk(
    mappings: Sequence[LegacyMapping],
    categories: Sequence[CategoryDefinition],
    expected_sources: set[tuple[LegacyAxis, str]] | None = None,
) -> None:
    """Reject unknown targets, duplicate sources, and missing legacy dispositions."""
    active_codes = _active_codes(categories)
    seen: set[tuple[LegacyAxis, str]] = set()
    for mapping in mappings:
        _check_targets(mapping, active_codes)
        _check_unique_source(mapping, seen)
        seen.add((mapping.axis, mapping.source_code))
        _check_disposition(mapping)
    if expected_sources is not None:
        _check_coverage(seen, expected_sources)


def _check_targets(mapping: LegacyMapping, active_codes: set[str]) -> None:
    """Reject a mapped disposition that points at an unknown or inactive category."""
    if mapping.state == "mapped" and any(target not in active_codes for target in mapping.target_codes):
        raise TaxonomyContractError(f"unknown target in mapping for {mapping.source_code}")


def _check_unique_source(mapping: LegacyMapping, seen: set[tuple[LegacyAxis, str]]) -> None:
    """Reject a second disposition for the same legacy axis and source code."""
    if (mapping.axis, mapping.source_code) in seen:
        raise TaxonomyContractError(f"conflicting duplicate mapping for {mapping.axis}:{mapping.source_code}")


def _check_disposition(mapping: LegacyMapping) -> None:
    """Reject targets that contradict the state, and a disposition with no reason."""
    if mapping.state == "mapped" and not mapping.target_codes:
        raise TaxonomyContractError(f"mapped mapping has no target for {mapping.source_code}")
    if mapping.state != "mapped" and mapping.target_codes:
        raise TaxonomyContractError(f"non-mapped disposition has targets for {mapping.source_code}")
    if not mapping.reason.strip():
        raise TaxonomyContractError(f"mapping has no reason for {mapping.source_code}")


def _check_coverage(
    seen: set[tuple[LegacyAxis, str]],
    expected_sources: set[tuple[LegacyAxis, str]],
) -> None:
    """Reject a crosswalk that does not cover exactly the expected legacy sources."""
    if seen == expected_sources:
        return
    missing = expected_sources - seen
    extra = seen - expected_sources
    raise TaxonomyContractError(f"crosswalk coverage mismatch: missing={missing}, extra={extra}")


def validate_pvog_leaf_mappings(
    mappings: Sequence[PvogLeafMapping],
    categories: Sequence[CategoryDefinition],
) -> None:
    """Reject duplicate leaf mappings, unknown targets, invalid scores, or missing reasons or acceptance dates."""
    active_codes = _active_codes(categories)
    seen: set[str] = set()
    for mapping in mappings:
        if mapping.leaf_code in seen:
            raise TaxonomyContractError(f"duplicate PVOG leaf mapping: {mapping.leaf_code}")
        seen.add(mapping.leaf_code)
        _check_leaf(mapping, active_codes)


def _check_leaf(mapping: PvogLeafMapping, active_codes: set[str]) -> None:
    """Reject a leaf mapping with no target, an unknown target, a bad confidence, or no acceptance record."""
    if not mapping.category_codes:
        raise TaxonomyContractError(f"PVOG leaf mapping has no target: {mapping.leaf_code}")
    if any(target not in active_codes for target in mapping.category_codes):
        raise TaxonomyContractError(f"unknown target in PVOG leaf mapping: {mapping.leaf_code}")
    if not 0 <= mapping.confidence <= 1:
        raise TaxonomyContractError(f"invalid PVOG leaf confidence: {mapping.leaf_code}")
    _check_acceptance(mapping)


def _check_acceptance(mapping: PvogLeafMapping) -> None:
    """Reject a leaf without a reason or an acceptance date, whatever its state (invariant 10, D-R9)."""
    if not mapping.reason.strip():
        raise TaxonomyContractError(f"PVOG leaf mapping has no reason: {mapping.leaf_code}")
    if mapping.accepted_on is None:
        raise TaxonomyContractError(f"PVOG leaf mapping has no acceptance date: {mapping.leaf_code}")


def _active_codes(categories: Sequence[CategoryDefinition]) -> set[str]:
    """Return the codes of the active categories."""
    return {category.code for category in categories if category.is_active}
