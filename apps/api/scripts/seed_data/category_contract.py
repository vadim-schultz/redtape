"""Category contract names for the seed and backfill scripts, resolved on first access from the app loader."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from app.shared.taxonomy.category_types import (
    CategoryDefinition,
    LegacyMapping,
    PvogLeafMapping,
    TaxonomyContractError,
)
from app.shared.taxonomy.category_validation import (
    CODE_PATTERN,
    validate_category_inventory,
    validate_legacy_crosswalk,
    validate_pvog_leaf_mappings,
)
from app.shared.taxonomy.contract_loader import CategoryContract, load_contract

if TYPE_CHECKING:
    CATEGORY_CONTRACT_VERSION: str
    PVOG_SOURCE_VERSION: str
    CATEGORY_INVENTORY: tuple[CategoryDefinition, ...]
    LEGACY_CROSSWALK: tuple[LegacyMapping, ...]
    PVOG_LEAF_MAPPINGS: tuple[PvogLeafMapping, ...]

__all__ = [
    "CATEGORY_CONTRACT_VERSION",
    "CATEGORY_INVENTORY",
    "CODE_PATTERN",
    "LEGACY_CROSSWALK",
    "PVOG_LEAF_MAPPINGS",
    "PVOG_SOURCE_VERSION",
    "CategoryDefinition",
    "LegacyMapping",
    "PvogLeafMapping",
    "TaxonomyContractError",
    "validate_category_inventory",
    "validate_legacy_crosswalk",
    "validate_pvog_leaf_mappings",
]

ContractValue = str | tuple[CategoryDefinition, ...] | tuple[LegacyMapping, ...] | tuple[PvogLeafMapping, ...]

_CONTRACT_NAMES: dict[str, Callable[[CategoryContract], ContractValue]] = {
    "CATEGORY_CONTRACT_VERSION": lambda contract: contract.artifact_version,
    "PVOG_SOURCE_VERSION": lambda contract: contract.pvog_source_version,
    "CATEGORY_INVENTORY": lambda contract: contract.categories,
    "LEGACY_CROSSWALK": lambda contract: contract.legacy_crosswalk,
    "PVOG_LEAF_MAPPINGS": lambda contract: contract.pvog_leaf_mappings,
}


def __getattr__(name: str) -> ContractValue:
    """Resolve a contract name on first access, so importing this module reads no artifact."""
    resolve = _CONTRACT_NAMES.get(name)
    if resolve is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return resolve(load_contract())
