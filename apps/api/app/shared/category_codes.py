"""Active canonical category codes: the closed vocabulary stored mentions are read against."""

from __future__ import annotations

from collections.abc import Iterable

from app.shared.taxonomy.contract_loader import load_contract


def active_category_codes() -> frozenset[str]:
    """Return the active canonical category codes, read from the contract on first use."""
    return frozenset(category.code for category in load_contract().categories if category.is_active)


def __getattr__(name: str) -> frozenset[str]:
    """Serve ``ACTIVE_CATEGORY_CODES`` on first access, so importing this module reads no artifact."""
    if name != "ACTIVE_CATEGORY_CODES":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return active_category_codes()


def split_active_codes(codes: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split ``codes`` into the active canonical ones and the unknown ones, each de-duplicated in input order."""
    active_codes = active_category_codes()
    unique = tuple(dict.fromkeys(codes))
    active = tuple(code for code in unique if code in active_codes)
    unknown = tuple(code for code in unique if code not in active_codes)
    return active, unknown
