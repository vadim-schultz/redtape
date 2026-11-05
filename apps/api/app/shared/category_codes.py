"""Active canonical category codes of the static contract: the closed vocabulary stored mentions are read against."""

from __future__ import annotations

from collections.abc import Iterable

from scripts.seed_data.category_contract import CATEGORY_INVENTORY

ACTIVE_CATEGORY_CODES: frozenset[str] = frozenset(
    category.code for category in CATEGORY_INVENTORY if category.is_active
)


def split_active_codes(codes: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split ``codes`` into the active canonical ones and the unknown ones, each de-duplicated in input order."""
    unique = tuple(dict.fromkeys(codes))
    active = tuple(code for code in unique if code in ACTIVE_CATEGORY_CODES)
    unknown = tuple(code for code in unique if code not in ACTIVE_CATEGORY_CODES)
    return active, unknown
