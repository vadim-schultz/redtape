"""Tag consensus vocabulary: the shared types the merged SQL engine computes support against."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import NamedTuple

from sqlalchemy.orm import InstrumentedAttribute

from app.config import Settings
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


@dataclass(frozen=True)
class TagThresholds:
    """The two thresholds a code needs: distinct procedures, and their share of the tagged procedures."""

    min_procedures: int
    min_share: float


def axis_thresholds(settings: Settings, axis: TagAxis) -> TagThresholds:
    """Return the thresholds ``axis`` reads from ``settings`` — the one place either path gets them from.

    Situation relaxes to one procedure (default): structurally, a life situation recurs within one
    procedure's mentions, not across unrelated procedures the way a domain does (decision D2).
    """
    if axis is TagAxis.SITUATION:
        return TagThresholds(
            settings.discovery_tag_min_procedures_situation, settings.discovery_tag_min_share_situation
        )
    return TagThresholds(settings.discovery_tag_min_procedures, settings.discovery_tag_min_share)
