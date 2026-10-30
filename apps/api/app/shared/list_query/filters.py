"""Reusable typed filter parsers; each raises ``ValueError`` with a client-facing message."""

from __future__ import annotations

import enum
from typing import TypeVar
from uuid import UUID

from app.shared.list_query.model import FilterParser, FilterValue

_Enum = TypeVar("_Enum", bound=enum.StrEnum)


def enum_filter(kind: type[_Enum]) -> FilterParser:
    """Return a parser accepting only the values of ``kind``."""

    def parse(raw: str) -> FilterValue:
        try:
            return kind(raw)
        except ValueError:
            allowed = ", ".join(member.value for member in kind)
            raise ValueError(f"Expected one of: {allowed}") from None

    return parse


def min_int_filter(minimum: int) -> FilterParser:
    """Return a parser accepting integers of at least ``minimum``."""

    def parse(raw: str) -> FilterValue:
        if not raw.lstrip("-").isdigit() or int(raw) < minimum:
            raise ValueError(f"Expected an integer of at least {minimum}")
        return int(raw)

    return parse


def uuid_filter(raw: str) -> FilterValue:
    """Accept a UUID and return it in canonical text form."""
    try:
        return str(UUID(raw))
    except ValueError:
        raise ValueError("Expected a UUID") from None


def text_filter(max_length: int) -> FilterParser:
    """Return a parser accepting text of 1 to ``max_length`` characters."""

    def parse(raw: str) -> FilterValue:
        if not 1 <= len(raw) <= max_length:
            raise ValueError(f"Expected 1 to {max_length} characters")
        return raw

    return parse
