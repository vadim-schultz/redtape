"""Lazy, cached loader for the category contract artifact; the only code that opens it."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.shared.taxonomy.category_types import (
    CategoryDefinition,
    ContractPayload,
    LegacyMapping,
    PvogLeafMapping,
    TaxonomyContractError,
)
from app.shared.taxonomy.category_validation import validate_category_inventory, validate_pvog_leaf_mappings

ARTIFACT_PATH = Path(__file__).resolve().parent / "category_contract_v1.json"


@dataclass(frozen=True, slots=True)
class CategoryContract:
    """The validated category contract: artifact versions and the frozen and leaf sections."""

    artifact_version: str
    pvog_source_version: str
    categories: tuple[CategoryDefinition, ...]
    legacy_crosswalk: tuple[LegacyMapping, ...]
    pvog_leaf_mappings: tuple[PvogLeafMapping, ...]


@cache
def load_contract() -> CategoryContract:
    """Return the contract read from ``ARTIFACT_PATH``, loaded and validated on first use.

    A failed load raises ``TaxonomyContractError`` and is not cached, so the next call retries.
    """
    return _parse_contract(_read_artifact(ARTIFACT_PATH))


def _read_artifact(path: Path) -> bytes:
    """Return the raw artifact bytes or raise ``TaxonomyContractError``."""
    try:
        return path.read_bytes()
    except OSError as exc:
        raise TaxonomyContractError(f"category contract artifact unreadable: {path}") from exc


def _parse_contract(raw: bytes) -> CategoryContract:
    """Parse, map, and validate artifact bytes into a :class:`CategoryContract`."""
    contract = _to_contract(_parse_payload(raw))
    validate_category_inventory(contract.categories)
    validate_pvog_leaf_mappings(contract.pvog_leaf_mappings, contract.categories)
    return contract


def _parse_payload(raw: bytes) -> ContractPayload:
    """Check the artifact's shape, or raise ``TaxonomyContractError``."""
    try:
        return TypeAdapter(ContractPayload).validate_json(raw)
    except ValidationError as exc:
        raise TaxonomyContractError(f"category contract artifact is malformed: {exc.error_count()} errors") from exc


def _to_contract(payload: ContractPayload) -> CategoryContract:
    """Map the validated payload onto the frozen dataclasses."""
    return CategoryContract(
        artifact_version=payload.artifact_version,
        pvog_source_version=payload.pvog_source_version,
        categories=_categories(payload),
        legacy_crosswalk=_legacy_crosswalk(payload),
        pvog_leaf_mappings=_pvog_leaf_mappings(payload),
    )


def _categories(payload: ContractPayload) -> tuple[CategoryDefinition, ...]:
    """Map each payload category onto a :class:`CategoryDefinition`."""
    return tuple(
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


def _legacy_crosswalk(payload: ContractPayload) -> tuple[LegacyMapping, ...]:
    """Map each payload legacy disposition onto a :class:`LegacyMapping`."""
    return tuple(
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


def _pvog_leaf_mappings(payload: ContractPayload) -> tuple[PvogLeafMapping, ...]:
    """Map each payload PVOG leaf mapping onto a :class:`PvogLeafMapping`."""
    return tuple(
        PvogLeafMapping(
            leaf_code=mapping.leaf_code,
            category_codes=mapping.category_codes,
            confidence=mapping.confidence,
            state=mapping.state,
            reason=mapping.reason,
        )
        for mapping in payload.pvog_leaf_mappings
    )
