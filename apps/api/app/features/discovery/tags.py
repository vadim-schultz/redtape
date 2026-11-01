"""Tag consensus vocabulary: the shared types the merged SQL engine computes support against."""

from __future__ import annotations

import enum
from typing import NamedTuple

from sqlalchemy.orm import InstrumentedAttribute

from app.models.discovery import DiscoveryCandidateMention as Mention

DEFAULT_MIN_PROCEDURES = 2
DEFAULT_MIN_SHARE = 0.5
MANUAL_EXTRACTOR = "manual"
"""The ``extractor`` of a mention written by a curator; its codes are authoritative for their axis."""


class TagSupport(NamedTuple):
    """How many procedures carry one code, their share of the tagged procedures, and whether that suffices."""

    code: str
    procedures: int
    share: float
    accepted: bool


class TagAxis(enum.Enum):
    """A tag axis of a mention: the array column that carries its codes."""

    DOMAIN = "domain"
    SITUATION = "situation"

    @property
    def column(self) -> InstrumentedAttribute[list[str] | None]:
        """Return the mention column holding this axis' codes."""
        return Mention.domain_codes if self is TagAxis.DOMAIN else Mention.situation_codes
